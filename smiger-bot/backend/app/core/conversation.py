from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis

from app.config import settings
from app.core.llm_gateway import (
    chat_completion,
    chat_completion_stream,
    chat_with_tools,
    chat_with_tools_stream,
)
from app.core.mcp_tools import TOOL_DEFINITIONS, execute_tool
from app.core.prompts import LEAD_PROMPT_INJECTION, SYSTEM_PROMPT, get_fallback_response
from app.core.rag_engine import search
from app.models.database import Conversation, Message

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_redis: Any = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


class ConversationManager:
    """Manages multi-turn conversations with RAG-augmented responses and lead capture."""

    async def _get_history(self, conversation_id: str) -> list[dict]:
        """使用 Redis List 原子操作获取历史记录，避免竞态条件"""
        r = await _get_redis()
        # 使用 LRANGE 获取列表中的所有元素（原子操作）
        key = f"conv:{conversation_id}:history"
        raw_list = await r.lrange(key, 0, -1)
        if raw_list:
            history = [json.loads(item) for item in raw_list]
            # 只保留最近的 MAX_HISTORY_TURNS * 2 条消息
            max_items = settings.MAX_HISTORY_TURNS * 2
            if len(history) > max_items:
                # 异步修剪列表（不阻塞主流程）
                asyncio.create_task(r.ltrim(key, -max_items, -1))
            return history
        return []

    async def _save_history(self, conversation_id: str, history: list[dict]) -> None:
        """将新消息追加到 Redis List（原子操作）"""
        r = await _get_redis()
        key = f"conv:{conversation_id}:history"
        # 使用 RPUSH 原子追加新消息
        for msg in history:
            await r.rpush(key, json.dumps(msg))
        # 设置过期时间并限制长度
        max_items = settings.MAX_HISTORY_TURNS * 2
        await r.ltrim(key, -max_items, -1)
        await r.expire(key, 86400)

    async def _append_messages(self, conversation_id: str, messages: list[dict]) -> None:
        """原子追加消息到历史记录（线程安全）"""
        r = await _get_redis()
        key = f"conv:{conversation_id}:history"
        pipe = r.pipeline()
        for msg in messages:
            pipe.rpush(key, json.dumps(msg))
        # 限制长度并设置过期时间
        max_items = settings.MAX_HISTORY_TURNS * 2
        pipe.ltrim(key, -max_items, -1)
        pipe.expire(key, 86400)
        await pipe.execute()

    def _build_context(self, rag_results: list[dict]) -> str:
        if not rag_results:
            return "No relevant information found in the knowledge base."
        parts = []
        for i, r in enumerate(rag_results, 1):
            source = r["metadata"].get("filename", "unknown")
            parts.append(f"[{i}] (source: {source}, relevance: {r['similarity']:.2f})\n{r['text']}")
        return "\n\n".join(parts)

    def _build_history_text(self, history: list[dict]) -> str:
        if not history:
            return "(This is the start of the conversation)"
        lines = []
        for msg in history:
            role = "Customer" if msg["role"] == "user" else "Smiger Expert"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _build_messages(
        self,
        user_message: str,
        context: str,
        history: list[dict],
        turn_count: int,
        lead_captured: bool,
        channel_instructions: str | None = None,
        customer_context: str | None = None,
    ) -> list[dict]:
        system_content = SYSTEM_PROMPT.format(
            context=context,
            history=self._build_history_text(history),
        )

        if channel_instructions:
            system_content += f"\n\n## Channel Instructions\n{channel_instructions.strip()}"

        if customer_context:
            system_content += f"\n\n## Customer Context\n{customer_context.strip()}"

        if turn_count >= settings.LEAD_TRIGGER_TURN and not lead_captured:
            system_content += LEAD_PROMPT_INJECTION.format(turn_count=turn_count)

        messages = [{"role": "system", "content": system_content}]

        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})
        return messages

    async def handle_message(
        self,
        db: AsyncSession,
        conversation: Conversation,
        user_message: str,
        channel_instructions: str | None = None,
        customer_context: str | None = None,
        history_limit_messages: int | None = None,
    ) -> tuple[str, float, bool]:
        """Process a message and return (reply, confidence, should_prompt_lead)."""
        history = await self._get_history(conversation.id)
        if history_limit_messages:
            history = history[-max(1, history_limit_messages):]

        rag_results = await search(user_message)
        context = self._build_context(rag_results)

        max_sim = max((r["similarity"] for r in rag_results), default=0.0)
        confidence = max_sim

        fallback = get_fallback_response(conversation.language)

        if confidence < settings.SIMILARITY_THRESHOLD and conversation.turn_count > 0:
            reply = fallback
        else:
            messages = self._build_messages(
                user_message, context, history,
                conversation.turn_count, conversation.lead_captured,
                channel_instructions=channel_instructions,
                customer_context=customer_context,
            )
            try:
                reply = await chat_with_tools(
                    messages, TOOL_DEFINITIONS, execute_tool,
                )
            except Exception:
                logger.warning("chat_with_tools failed, falling back to plain chat")
                reply = await chat_completion(messages)

        user_msg = Message(conversation_id=conversation.id, role="user", content=user_message)
        assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=reply, confidence=confidence)
        db.add(user_msg)
        db.add(assistant_msg)
        # 使用原子操作增加 turn_count
        conversation.version += 1
        conversation.turn_count += 1
        await db.commit()

        # 原子追加新消息到 Redis（避免竞态）
        await self._append_messages(conversation.id, [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply}
        ])

        lead_prompt = conversation.turn_count >= settings.LEAD_TRIGGER_TURN and not conversation.lead_captured
        return reply, confidence, lead_prompt

    async def handle_message_stream(
        self,
        db: AsyncSession,
        conversation: Conversation,
        user_message: str,
        channel_instructions: str | None = None,
        customer_context: str | None = None,
        history_limit_messages: int | None = None,
    ) -> AsyncGenerator[tuple[str, dict | None], None]:
        """Stream tokens, then yield a final meta dict."""
        history = await self._get_history(conversation.id)
        if history_limit_messages:
            history = history[-max(1, history_limit_messages):]

        rag_results = await search(user_message)
        context = self._build_context(rag_results)
        max_sim = max((r["similarity"] for r in rag_results), default=0.0)
        confidence = max_sim

        fallback = get_fallback_response(conversation.language)

        if confidence < settings.SIMILARITY_THRESHOLD and conversation.turn_count > 0:
            yield fallback, None
            reply = fallback
        else:
            messages = self._build_messages(
                user_message, context, history,
                conversation.turn_count, conversation.lead_captured,
                channel_instructions=channel_instructions,
                customer_context=customer_context,
            )
            reply = ""
            try:
                async for token in chat_with_tools_stream(
                    messages, TOOL_DEFINITIONS, execute_tool,
                ):
                    reply += token
                    yield token, None
            except Exception:
                logger.warning("chat_with_tools_stream failed, falling back")
                async for token in chat_completion_stream(messages):
                    reply += token
                    yield token, None

        user_msg = Message(conversation_id=conversation.id, role="user", content=user_message)
        assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=reply, confidence=confidence)
        db.add(user_msg)
        db.add(assistant_msg)
        # 使用原子操作增加 turn_count
        conversation.version += 1
        conversation.turn_count += 1
        await db.commit()

        # 原子追加新消息到 Redis（避免竞态）
        await self._append_messages(conversation.id, [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply}
        ])

        lead_prompt = conversation.turn_count >= settings.LEAD_TRIGGER_TURN and not conversation.lead_captured
        yield "", {"confidence": confidence, "lead_prompt": lead_prompt}
