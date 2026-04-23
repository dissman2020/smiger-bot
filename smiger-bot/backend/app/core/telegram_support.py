"""Direct Telegram customer support with AI auto-replies."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import telegram_client
from app.core.conversation import ConversationManager
from app.core.telegram_accounts import get_active_telegram_account, get_account_by_name
from app.models.database import (
    Conversation,
    TelegramSupportChat,
    TelegramSupportMessage,
    TelegramSupportSetting,
    async_session,
)

logger = logging.getLogger(__name__)
conv_manager = ConversationManager()

DEFAULT_SYSTEM_PROMPT = (
    "You are a professional, polite, concise Telegram support assistant. "
    "Reply in Chinese by default unless the user clearly uses another language. "
    "If you are unsure, say so instead of making things up."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _telegram_conversation_id(chat_id: str) -> str:
    return f"telegram_support_{chat_id}"


def _detect_language(text: str) -> str:
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"


def _build_customer_context(chat: TelegramSupportChat) -> str:
    return "\n".join([
        "Channel: Telegram direct customer support",
        f"Telegram chat id: {chat.chat_id}",
        f"Display name: {chat.display_name or 'not provided'}",
        f"Telegram username: {chat.username or 'not provided'}",
        f"Account: {chat.account_name or 'default'}",
    ])


def normalize_incoming_message(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None

    text = _text(message.get("text"))
    if not text:
        return None

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    return {
        "update_id": update.get("update_id"),
        "message_id": message.get("message_id"),
        "chat_id": _text(chat.get("id")),
        "chat_type": _text(chat.get("type")),
        "text": text,
        "from_user_id": _text(sender.get("id")),
        "from_is_bot": bool(sender.get("is_bot")),
        "first_name": _text(sender.get("first_name")),
        "last_name": _text(sender.get("last_name")),
        "username": _text(sender.get("username")),
    }


async def get_or_create_settings(db: AsyncSession) -> TelegramSupportSetting:
    result = await db.execute(select(TelegramSupportSetting).where(TelegramSupportSetting.id == 1))
    support_settings = result.scalar_one_or_none()
    if support_settings:
        return support_settings

    support_settings = TelegramSupportSetting(
        id=1,
        ai_enabled=True,
        max_history=12,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    )
    db.add(support_settings)
    await db.flush()
    return support_settings


def build_display_name(message: dict[str, Any]) -> str | None:
    value = " ".join(
        part for part in [message.get("first_name"), message.get("last_name")] if part
    ).strip()
    return value or None


async def upsert_chat(
    db: AsyncSession,
    message: dict[str, Any],
    account_name: str | None,
) -> TelegramSupportChat:
    chat_id = _text(message.get("chat_id"))
    result = await db.execute(select(TelegramSupportChat).where(TelegramSupportChat.chat_id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        chat = TelegramSupportChat(chat_id=chat_id, account_name=account_name)
        db.add(chat)

    chat.account_name = account_name or chat.account_name
    chat.first_name = message.get("first_name") or None
    chat.last_name = message.get("last_name") or None
    chat.username = message.get("username") or None
    chat.display_name = build_display_name(message)
    chat.updated_at = _utcnow()
    return chat


def is_ai_enabled(chat: TelegramSupportChat, support_settings: TelegramSupportSetting) -> bool:
    if chat.ai_enabled_override is not None:
        return bool(chat.ai_enabled_override)
    return bool(support_settings.ai_enabled)


async def list_chats(db: AsyncSession) -> list[TelegramSupportChat]:
    result = await db.execute(
        select(TelegramSupportChat).order_by(TelegramSupportChat.updated_at.desc()).limit(200)
    )
    return list(result.scalars().all())


async def get_chat(db: AsyncSession, chat_id: str) -> TelegramSupportChat | None:
    result = await db.execute(select(TelegramSupportChat).where(TelegramSupportChat.chat_id == str(chat_id)))
    return result.scalar_one_or_none()


async def get_messages(
    db: AsyncSession,
    chat_id: str,
    limit: int | None = None,
) -> list[TelegramSupportMessage]:
    q = (
        select(TelegramSupportMessage)
        .where(TelegramSupportMessage.chat_id == str(chat_id))
        .order_by(TelegramSupportMessage.created_at)
    )
    if limit:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def record_message(
    db: AsyncSession,
    chat_id: str,
    role: str,
    content: str,
    source: str,
    telegram_message_id: Any = None,
) -> TelegramSupportMessage:
    item = TelegramSupportMessage(
        chat_id=str(chat_id),
        role=role,
        content=content,
        source=source,
        telegram_message_id=_text(telegram_message_id) or None,
    )
    db.add(item)
    return item


async def build_llm_reply(
    db: AsyncSession,
    chat: TelegramSupportChat,
    support_settings: TelegramSupportSetting,
    user_message: str,
) -> str:
    """Generate Telegram replies through the same RAG/tool pipeline as web chat."""
    conversation_id = _telegram_conversation_id(chat.chat_id)
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(
            id=conversation_id,
            visitor_id=f"telegram_{chat.chat_id}",
            language=_detect_language(user_message),
            telegram_account_name=chat.account_name,
        )
        db.add(conv)
        await db.flush()
    else:
        conv.telegram_account_name = chat.account_name or conv.telegram_account_name
        if user_message:
            conv.language = _detect_language(user_message)

    reply, _confidence, _lead_prompt = await conv_manager.handle_message(
        db=db,
        conversation=conv,
        user_message=user_message,
        channel_instructions=support_settings.system_prompt or DEFAULT_SYSTEM_PROMPT,
        customer_context=_build_customer_context(chat),
        history_limit_messages=max(1, min(int(support_settings.max_history or 12), 50)),
    )
    return reply.strip()


async def handle_admin_command(
    message: dict[str, Any],
    account_name: str | None = None,
) -> bool:
    text = _text(message.get("text")).lower()
    if text not in {"/ai_on", "/ai_off", "/status"}:
        return False

    chat_id = _text(message.get("chat", {}).get("id"))
    async with async_session() as db:
        support_settings = await get_or_create_settings(db)
        if text == "/ai_on":
            support_settings.ai_enabled = True
            await db.commit()
            await telegram_client.send_message(
                chat_id,
                "Telegram support AI auto-reply is now ON.",
                parse_mode="",
                account_name=account_name,
            )
            return True

        if text == "/ai_off":
            support_settings.ai_enabled = False
            await db.commit()
            await telegram_client.send_message(
                chat_id,
                "Telegram support AI auto-reply is now OFF.",
                parse_mode="",
                account_name=account_name,
            )
            return True

        chat_count = len(await list_chats(db))
        await db.commit()
        await telegram_client.send_message(
            chat_id,
            "\n".join([
                f"Telegram support AI auto-reply: {'ON' if support_settings.ai_enabled else 'OFF'}",
                f"Tracked chats: {chat_count}",
                f"Updated at: {support_settings.updated_at.isoformat() if support_settings.updated_at else 'unknown'}",
            ]),
            parse_mode="",
            account_name=account_name,
        )
        return True


async def process_customer_update(
    update: dict[str, Any],
    account_name: str | None = None,
) -> bool:
    message = normalize_incoming_message(update)
    if not message or message["from_is_bot"] or message["chat_type"] != "private":
        return False

    account = get_account_by_name(account_name, require_ready=True) if account_name else get_active_telegram_account()
    if not settings.TELEGRAM_ENABLED or not account:
        return False

    admin_chat_id = _text(account.get("admin_chat_id"))
    if message["chat_id"] == admin_chat_id:
        return False

    async with async_session() as db:
        support_settings = await get_or_create_settings(db)
        chat = await upsert_chat(db, message, account.get("name"))
        chat.unread_count = int(chat.unread_count or 0) + 1
        await record_message(
            db,
            chat.chat_id,
            role="user",
            content=message["text"],
            source="telegram",
            telegram_message_id=message.get("message_id"),
        )
        await db.commit()

        if not is_ai_enabled(chat, support_settings):
            return True

        try:
            reply = await build_llm_reply(db, chat, support_settings, message["text"])
        except Exception:
            logger.exception("Telegram support AI reply failed for chat %s", chat.chat_id)
            return True

        if not reply:
            return True

        try:
            sent = await telegram_client.send_message(
                chat.chat_id,
                reply,
                parse_mode="",
                account_name=account.get("name"),
            )
            await record_message(
                db,
                chat.chat_id,
                role="assistant",
                content=reply,
                source="ai",
                telegram_message_id=(sent or {}).get("message_id"),
            )
            chat.updated_at = _utcnow()
            await db.commit()
        except Exception:
            logger.exception("Telegram support failed to send AI reply for chat %s", chat.chat_id)

    return True


async def send_manual_reply(
    db: AsyncSession,
    chat: TelegramSupportChat,
    text: str,
) -> TelegramSupportMessage:
    account_name = chat.account_name or None
    result = await telegram_client.send_message(
        chat.chat_id,
        text,
        parse_mode="",
        account_name=account_name,
    )
    item = await record_message(
        db,
        chat.chat_id,
        role="assistant",
        content=text,
        source="manual",
        telegram_message_id=(result or {}).get("message_id"),
    )
    chat.unread_count = 0
    chat.updated_at = _utcnow()
    await db.commit()
    await db.refresh(item)
    return item
