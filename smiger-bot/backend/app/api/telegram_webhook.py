"""Telegram webhook: receives admin replies and routes them to web users."""
from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Request, Response

from app.core import telegram_support
from app.core.telegram_accounts import get_account_by_admin_chat_id, get_account_by_webhook_secret, get_active_telegram_account
from app.core.ws_registry import get_user_ws
from app.models.database import Conversation, Message, async_session

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhook", tags=["webhook"])

_TAG_RE = re.compile(r"#([a-f0-9]{4,8})\b", re.IGNORECASE)


@router.post("/telegram")
async def receive_telegram_update(request: Request):
    """Handle incoming Telegram updates (messages from admin)."""
    body = await request.json()
    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"status": "ok"}

    chat_id = str(message.get("chat", {}).get("id", ""))
    account = get_account_by_admin_chat_id(chat_id, require_ready=True, enabled_only=True)
    if not account:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        account = get_account_by_webhook_secret(token, require_ready=True, enabled_only=True)
        if not account:
            account = get_active_telegram_account(require_ready=True)
        if account and account.get("webhook_secret") and token != account["webhook_secret"]:
            logger.warning("Telegram customer webhook secret mismatch (%s)", account["name"])
            return Response(content="Forbidden", status_code=403)
        handled = await telegram_support.process_customer_update(
            body,
            account_name=(account["name"] if account else None),
        )
        if handled:
            return {"status": "ok"}
        logger.info("Ignoring Telegram message from unknown admin chat: %s", chat_id)
        return {"status": "ok"}

    if account.get("webhook_secret"):
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != account["webhook_secret"]:
            logger.warning("Telegram webhook secret mismatch (%s)", account["name"])
            return Response(content="Forbidden", status_code=403)

    try:
        text = (message.get("text") or "").strip()
        if not text:
            return {"status": "ok"}

        if await telegram_support.handle_admin_command(message, account_name=account["name"]):
            return {"status": "ok"}

        tag_match = _TAG_RE.search(text)
        if not tag_match:
            logger.info("Telegram message missing conversation tag (%s): %s", account["name"], text[:100])
            return {"status": "no_tag"}

        conv_tag = tag_match.group(1).lower()
        reply_text = _TAG_RE.sub("", text).strip()
        if not reply_text:
            return {"status": "empty_reply"}

        async with async_session() as db:
            await _route_reply(db, conv_tag, reply_text, account["name"])
    except Exception:
        logger.exception("Error processing Telegram webhook")

    return {"status": "ok"}


async def _route_reply(
    db: AsyncSession,
    conv_tag: str,
    reply_text: str,
    account_name: str,
):
    """Find the conversation by tag and deliver the admin reply."""
    result = await db.execute(
        select(Conversation).where(Conversation.whatsapp_tag == conv_tag)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        logger.warning("No conversation found for tag #%s", conv_tag)
        return

    if conv.telegram_account_name and conv.telegram_account_name != account_name:
        logger.warning(
            "Conversation #%s is bound to %s but reply came from %s",
            conv_tag,
            conv.telegram_account_name,
            account_name,
        )
        return

    conv.telegram_account_name = account_name
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
    logger.info("Telegram admin reply saved for conv %s [#%s] via %s", conv.id, conv_tag, account_name)

    user_ws = get_user_ws(conv.id)
    if user_ws:
        try:
            await user_ws.send_text(json.dumps({
                "type": "agent_message",
                "content": reply_text,
            }))
            logger.info("Telegram reply pushed to user WS for conv %s", conv.id)
        except Exception:
            logger.warning("Failed to push Telegram reply via WS for conv %s", conv.id)
