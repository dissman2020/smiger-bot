"""Google Chat App endpoint — receives admin replies from Google Chat and routes them to web users."""
from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Request, Response

from app.config import settings
from app.core.ws_registry import get_user_ws
from app.models.database import Conversation, Message, async_session

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhook", tags=["webhook"])

_TAG_RE = re.compile(r"#([a-f0-9]{4,8})\b", re.IGNORECASE)


@router.post("/gchat")
async def receive_gchat_event(request: Request):
    """Handle incoming Google Chat App events (messages from admin in a space)."""
    if settings.GCHAT_VERIFY_TOKEN:
        token = request.headers.get("X-GChat-Verify-Token", "")
        if token != settings.GCHAT_VERIFY_TOKEN:
            logger.warning("Google Chat webhook verify token mismatch")
            return Response(content="Forbidden", status_code=403)

    body = await request.json()

    event_type = body.get("type", "")

    if event_type == "ADDED_TO_SPACE":
        return {"text": "Smiger Bot 已连接！客户消息将推送到此空间。回复时请带上会话标记 #xxxxxx。"}

    if event_type != "MESSAGE":
        return {}

    try:
        message = body.get("message", {})
        text = (message.get("text") or "").strip()

        if not text:
            return {}

        text = re.sub(r"@\S+\s*", "", text).strip()

        tag_match = _TAG_RE.search(text)
        if not tag_match:
            return {"text": "请在回复中包含会话标记（如 #a1b2c3），以便将消息路由到正确的客户。"}

        conv_tag = tag_match.group(1).lower()
        reply_text = _TAG_RE.sub("", text).strip()

        if not reply_text:
            return {"text": "消息内容为空，请输入回复内容。"}

        async with async_session() as db:
            await _route_reply(db, conv_tag, reply_text)

        return {"text": f"✅ 已发送至客户 [#{conv_tag}]"}

    except Exception:
        logger.exception("Error processing Google Chat event")
        return {"text": "⚠️ 处理消息时出错，请稍后重试。"}


async def _route_reply(db: AsyncSession, conv_tag: str, reply_text: str):
    """Find the conversation by tag and deliver the admin reply."""
    result = await db.execute(
        select(Conversation).where(Conversation.whatsapp_tag == conv_tag)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        logger.warning("No conversation found for tag #%s", conv_tag)
        return

    if conv.handoff_status != "active":
        conv.handoff_status = "active"

    msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=reply_text,
        confidence=1.0,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    logger.info("Google Chat admin reply saved for conv %s [#%s]", conv.id, conv_tag)

    user_ws = get_user_ws(conv.id)
    if user_ws:
        try:
            await user_ws.send_text(json.dumps({
                "type": "agent_message",
                "content": reply_text,
            }))
            logger.info("Google Chat reply pushed to user WS for conv %s", conv.id)
        except Exception:
            logger.warning("Failed to push Google Chat reply via WS for conv %s", conv.id)
