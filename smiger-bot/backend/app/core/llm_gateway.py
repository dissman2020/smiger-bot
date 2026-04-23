from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_llm_client: Any = None
_http_client: Any = None

MAX_TOOL_ROUNDS = 3


def get_llm_client() -> AsyncOpenAI:
    """Client for chat completions (sophnet / DeepSeek)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    return _llm_client


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client


# ── Chat (plain, no tools) ────────────────────────────

async def chat_completion(messages: list[dict], temperature: float = 0.7) -> str:
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


async def chat_completion_stream(messages: list[dict], temperature: float = 0.7) -> AsyncGenerator[str, None]:
    client = get_llm_client()
    stream = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ── Chat with tool-calling ────────────────────────────

async def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_executor: Any,
    temperature: float = 0.7,
) -> str:
    """Non-streaming chat that handles multi-round tool calls.

    Loops up to MAX_TOOL_ROUNDS times: if the LLM returns tool_calls,
    execute them, append results, and call again until a text response
    is produced.

    Falls back to plain chat_completion if tool-calling triggers an error.
    """
    from app.core.mcp_tools import execute_tool  # avoid circular

    client = get_llm_client()
    working_messages = list(messages)

    for _round in range(MAX_TOOL_ROUNDS):
        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=working_messages,
                temperature=temperature,
                max_tokens=1024,
                tools=tools,
            )
        except Exception as e:
            logger.warning("Tool-calling request failed (%s), falling back to plain chat", e)
            return await chat_completion(messages, temperature)

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or (choice.message.tool_calls and len(choice.message.tool_calls) > 0):
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": choice.message.content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]
            working_messages.append(assistant_msg)

            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info("Tool call: %s(%s)", fn_name, fn_args)
                result_str = execute_tool(fn_name, fn_args)
                logger.info("Tool result: %s", result_str[:300])

                working_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })
            continue

        return choice.message.content or ""

    logger.warning("Exceeded max tool rounds (%d), returning last content", MAX_TOOL_ROUNDS)
    return working_messages[-1].get("content", "") if working_messages else ""


async def chat_with_tools_stream(
    messages: list[dict],
    tools: list[dict],
    tool_executor: Any,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Streaming chat with tools.

    Tool-calling rounds are executed non-streaming. Only the final text
    response is streamed back token-by-token.
    """
    from app.core.mcp_tools import execute_tool

    client = get_llm_client()
    working_messages = list(messages)

    for _round in range(MAX_TOOL_ROUNDS):
        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=working_messages,
                temperature=temperature,
                max_tokens=1024,
                tools=tools,
            )
        except Exception as e:
            logger.warning("Tool-calling failed (%s), streaming without tools", e)
            async for token in chat_completion_stream(messages, temperature):
                yield token
            return

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or (choice.message.tool_calls and len(choice.message.tool_calls) > 0):
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": choice.message.content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]
            working_messages.append(assistant_msg)

            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}
                logger.info("Tool call (stream): %s(%s)", fn_name, fn_args)
                result_str = execute_tool(fn_name, fn_args)
                working_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })
            continue

        # Final round: stream the text response
        break

    stream = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=working_messages,
        temperature=temperature,
        max_tokens=1024,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ── Embedding (sophnet custom API) ────────────────────

async def _call_sophnet_embedding(texts: list[str]) -> list[list[float]]:
    """Call the sophnet easyllm embedding API."""
    client = _get_http_client()
    payload = {
        "easyllm_id": settings.EMBEDDING_EASYLLM_ID,
        "input_texts": texts,
        "dimensions": settings.EMBEDDING_DIMENSIONS,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
    }
    resp = await client.post(settings.EMBEDDING_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        logger.error("Embedding API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
    data = resp.json()

    # Handle possible response formats:
    # {"embeddings": [[...], [...]]}  or  {"data": [{"embedding": [...]}, ...]}
    if "embeddings" in data:
        return data["embeddings"]
    if "data" in data:
        return [item["embedding"] for item in data["data"]]

    raise ValueError(f"Unexpected embedding API response format: {list(data.keys())}")


async def get_embedding(text: str) -> list[float]:
    results = await _call_sophnet_embedding([text])
    return results[0]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    batch_size = 10
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = await _call_sophnet_embedding(batch)
        all_embeddings.extend(embeddings)
    return all_embeddings
