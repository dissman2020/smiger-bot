"""Telegram long-polling background task (no public domain required)."""
from __future__ import annotations

import asyncio
import json
import logging
import re

from app.core import telegram_client, telegram_support
from app.core.telegram_accounts import get_active_telegram_account
from app.core.ws_registry import get_user_ws
from app.models.database import Conversation, Message, async_session

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"#([a-f0-9]{4,8})\b", re.IGNORECASE)
_running = False


async def start_polling():
    """Entry point. Call once at app startup. Runs forever in background."""
    global _running
    if _running:
        return
    _running = True

    if not telegram_client.is_enabled():
        logger.info("Telegram polling skipped: not enabled")
        return

    await telegram_client.delete_webhook()
    logger.info("Telegram polling started (long-poll mode)")

    offset: int | None = None
    while _running:
        try:
            updates = await telegram_client.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update["update_id"] + 1
                await _handle_update(update)
        except asyncio.CancelledError:
            logger.info("Telegram polling cancelled")
            break
        except Exception:
            logger.exception("Telegram polling error, retrying in 5s")
            await asyncio.sleep(5)


def stop_polling():
    global _running
    _running = False


async def _handle_update(update: dict):
    """Process a single Telegram update (same routing logic as webhook)."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    account = get_active_telegram_account(require_ready=True)
    if not account:
        return

    chat_id = str(message.get("chat", {}).get("id", ""))
    admin_chat_id = account["admin_chat_id"]
    if chat_id != admin_chat_id:
        await telegram_support.process_customer_update(update, account_name=account["name"])
        return

    if await telegram_support.handle_admin_command(message, account_name=account["name"]):
        return

    tag_match = _TAG_RE.search(text)
    if not tag_match:
        await telegram_client.send_message(
            admin_chat_id,
            "Please include a conversation tag like #a1b2c3 in your reply.",
            account_name=account["name"],
        )
        return

    conv_tag = tag_match.group(1).lower()
    reply_text = _TAG_RE.sub("", text).strip()
    if not reply_text:
        return

    async with async_session() as db:
        await _route_reply(db, conv_tag, reply_text)

    await telegram_client.send_message(
        admin_chat_id,
        f"Sent to customer [#{conv_tag}]",
        account_name=account["name"],
    )


async def _route_reply(db: AsyncSession, conv_tag: str, reply_text: str):
    result = await db.execute(
        select(Conversation).where(Conversation.whatsapp_tag == conv_tag)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        logger.warning("No conversation found for tag #%s", conv_tag)
        account = get_active_telegram_account(require_ready=True)
        if account:
            await telegram_client.send_message(
                account["admin_chat_id"],
                f"No conversation found for #{conv_tag}",
                account_name=account["name"],
            )
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
    logger.info("Telegram admin reply saved for conv %s [#%s]", conv.id, conv_tag)

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
