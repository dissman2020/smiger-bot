"""Admin API for the direct Telegram support module."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.config import settings
from app.core import telegram_support
from app.core.telegram_accounts import get_active_account_name, get_active_telegram_account
from app.models.database import (
    TelegramSupportChat,
    TelegramSupportMessage,
    get_db,
)

router = APIRouter(prefix="/api/admin/telegram-support", tags=["telegram-support"])


class TelegramSupportSettingsOut(BaseModel):
    ai_enabled: bool
    max_history: int
    system_prompt: str
    telegram_enabled: bool
    active_account: str


class TelegramSupportSettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    max_history: int | None = None
    system_prompt: str | None = None


class TelegramSupportChatOut(BaseModel):
    chat_id: str
    account_name: str | None
    display_name: str | None
    username: str | None
    first_name: str | None
    last_name: str | None
    ai_enabled: bool
    ai_enabled_override: bool | None
    unread_count: int
    message_count: int = 0
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TelegramSupportMessageOut(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    source: str
    telegram_message_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TelegramSupportChatDetailOut(BaseModel):
    chat: TelegramSupportChatOut
    messages: list[TelegramSupportMessageOut]


class TelegramSupportReplyIn(BaseModel):
    text: str


class TelegramSupportAiUpdate(BaseModel):
    ai_enabled: bool | None = None
    clear_override: bool = False


def _message_preview(content: str | None, max_len: int = 100) -> str | None:
    if not content:
        return None
    return content if len(content) <= max_len else f"{content[: max_len - 1]}..."


def _chat_out(
    chat: TelegramSupportChat,
    ai_enabled: bool,
    messages: list[TelegramSupportMessage] | None = None,
) -> TelegramSupportChatOut:
    last = messages[-1] if messages else None
    return TelegramSupportChatOut(
        chat_id=chat.chat_id,
        account_name=chat.account_name,
        display_name=chat.display_name,
        username=chat.username,
        first_name=chat.first_name,
        last_name=chat.last_name,
        ai_enabled=ai_enabled,
        ai_enabled_override=chat.ai_enabled_override,
        unread_count=chat.unread_count or 0,
        message_count=len(messages or []),
        last_message_preview=_message_preview(last.content if last else None),
        last_message_at=last.created_at if last else chat.updated_at,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.get("/settings", response_model=TelegramSupportSettingsOut)
async def get_support_settings(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    support_settings = await telegram_support.get_or_create_settings(db)
    active = get_active_telegram_account(require_ready=False)
    return TelegramSupportSettingsOut(
        ai_enabled=support_settings.ai_enabled,
        max_history=support_settings.max_history,
        system_prompt=support_settings.system_prompt,
        telegram_enabled=settings.TELEGRAM_ENABLED,
        active_account=(active["name"] if active else get_active_account_name()),
    )


@router.put("/settings", response_model=TelegramSupportSettingsOut)
async def update_support_settings(
    body: TelegramSupportSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    support_settings = await telegram_support.get_or_create_settings(db)
    if body.ai_enabled is not None:
        support_settings.ai_enabled = body.ai_enabled
    if body.max_history is not None:
        support_settings.max_history = max(1, min(body.max_history, 50))
    if body.system_prompt is not None:
        support_settings.system_prompt = body.system_prompt.strip() or telegram_support.DEFAULT_SYSTEM_PROMPT
    await db.commit()
    await db.refresh(support_settings)
    active = get_active_telegram_account(require_ready=False)
    return TelegramSupportSettingsOut(
        ai_enabled=support_settings.ai_enabled,
        max_history=support_settings.max_history,
        system_prompt=support_settings.system_prompt,
        telegram_enabled=settings.TELEGRAM_ENABLED,
        active_account=(active["name"] if active else get_active_account_name()),
    )


@router.get("/chats", response_model=list[TelegramSupportChatOut])
async def list_support_chats(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    support_settings = await telegram_support.get_or_create_settings(db)
    chats = await telegram_support.list_chats(db)
    items: list[TelegramSupportChatOut] = []
    for chat in chats:
        messages = await telegram_support.get_messages(db, chat.chat_id)
        items.append(_chat_out(chat, telegram_support.is_ai_enabled(chat, support_settings), messages))
    return items


@router.get("/chats/{chat_id}", response_model=TelegramSupportChatDetailOut)
async def get_support_chat(
    chat_id: str,
    mark_read: bool = True,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    support_settings = await telegram_support.get_or_create_settings(db)
    chat = await telegram_support.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Telegram support chat not found")
    if mark_read:
        chat.unread_count = 0
        await db.commit()
        await db.refresh(chat)
    messages = await telegram_support.get_messages(db, chat.chat_id)
    return TelegramSupportChatDetailOut(
        chat=_chat_out(chat, telegram_support.is_ai_enabled(chat, support_settings), messages),
        messages=messages,
    )


@router.post("/chats/{chat_id}/read")
async def mark_support_chat_read(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    chat = await telegram_support.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Telegram support chat not found")
    chat.unread_count = 0
    await db.commit()
    return {"status": "ok", "chat_id": chat_id}


@router.post("/chats/{chat_id}/ai", response_model=TelegramSupportChatOut)
async def update_support_chat_ai(
    chat_id: str,
    body: TelegramSupportAiUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    support_settings = await telegram_support.get_or_create_settings(db)
    chat = await telegram_support.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Telegram support chat not found")
    if body.clear_override:
        chat.ai_enabled_override = None
    elif body.ai_enabled is not None:
        chat.ai_enabled_override = body.ai_enabled
    else:
        raise HTTPException(status_code=400, detail="Set ai_enabled or clear_override=true")
    await db.commit()
    await db.refresh(chat)
    messages = await telegram_support.get_messages(db, chat.chat_id)
    return _chat_out(chat, telegram_support.is_ai_enabled(chat, support_settings), messages)


@router.post("/chats/{chat_id}/messages", response_model=TelegramSupportMessageOut)
async def reply_support_chat(
    chat_id: str,
    body: TelegramSupportReplyIn,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Reply text cannot be empty")
    chat = await telegram_support.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Telegram support chat not found")
    return await telegram_support.send_manual_reply(db, chat, text)
