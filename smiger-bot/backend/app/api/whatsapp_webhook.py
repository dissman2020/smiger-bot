"""WhatsApp Cloud API webhook — receives admin replies and routes them to web users."""
from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ws_registry import get_user_ws
from app.models.database import Conversation, Message, async_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhook", tags=["webhook"])

_TAG_RE = re.compile(r"#([a-f0-9]{4,8})\b", re.IGNORECASE)


@router.get("/whatsapp")
async def verify_webhook(request: Request):
    """Meta webhook verification handshake."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified")
        return Response(content=challenge, media_type="text/plain")
    logger.warning("WhatsApp webhook verification failed (token mismatch)")
    return Response(content="Forbidden", status_code=403)


@router.post("/whatsapp")
async def receive_webhook(request: Request):
    """Handle incoming WhatsApp messages from admin."""
    body = await request.json()

    try:
        entry = body.get("entry", [])
        if not entry:
            return {"status": "ok"}

        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "ok"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return {"status": "ok"}

        msg = messages[0]
        sender = msg.get("from", "")
        text = (msg.get("text") or {}).get("body", "").strip()

        if not text:
            return {"status": "ok"}

        admin_phone = settings.WHATSAPP_ADMIN_PHONE.lstrip("+").replace(" ", "")
        if sender != admin_phone:
            logger.info("Ignoring WhatsApp message from non-admin: %s", sender)
            return {"status": "ok"}

        tag_match = _TAG_RE.search(text)
        if not tag_match:
            logger.warning("WhatsApp admin message missing conversation tag: %s", text[:100])
            return {"status": "no_tag"}

        conv_tag = tag_match.group(1).lower()
        reply_text = _TAG_RE.sub("", text).strip()

        if not reply_text:
            return {"status": "empty_reply"}

        async with async_session() as db:
            await _route_reply(db, conv_tag, reply_text)

    except Exception:
        logger.exception("Error processing WhatsApp webhook")

    return {"status": "ok"}


async def _route_reply(db: AsyncSession, conv_tag: str, reply_text: str):
    """Find the conversation by tag and deliver the admin reply."""
    result = await db.execute(
        select(Conversation).where(Conversation.whatsapp_tag == conv_tag)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        logger.warning("No conversation found for WhatsApp tag #%s", conv_tag)
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
    logger.info("WhatsApp admin reply saved for conv %s [#%s]", conv.id, conv_tag)

    user_ws = get_user_ws(conv.id)
    if user_ws:
        try:
            await user_ws.send_text(json.dumps({
                "type": "agent_message",
                "content": reply_text,
            }))
            logger.info("WhatsApp reply pushed to user WS for conv %s", conv.id)
        except Exception:
            logger.warning("Failed to push WhatsApp reply via WS for conv %s", conv.id)
