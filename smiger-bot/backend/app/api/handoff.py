"""Admin endpoints for human handoff management."""
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.core import gchat_client, telegram_client, whatsapp_client
from app.core.telegram_accounts import list_enabled_telegram_accounts
from app.core.ws_registry import get_user_ws
from app.models.database import Conversation, Message, get_db
from app.models.schemas import (
    HandoffAcceptRequest,
    HandoffConversationItem,
    HandoffCount,
    HandoffReply,
    MessageOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/handoff", tags=["handoff"])


class HandoffChannelUpdate(BaseModel):
    telegram_account_name: str | None = None


def _is_valid_telegram_account(name: str | None) -> bool:
    if not name:
        return False
    return any(a["name"] == name for a in list_enabled_telegram_accounts(require_ready=True))


@router.get("/count", response_model=HandoffCount)
async def handoff_count(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    result = await db.execute(
        select(Conversation.handoff_status, func.count(Conversation.id))
        .where(Conversation.handoff_status.in_(["pending", "active"]))
        .group_by(Conversation.handoff_status)
    )
    counts = {row[0]: row[1] for row in result.all()}
    return HandoffCount(
        pending=counts.get("pending", 0),
        active=counts.get("active", 0),
    )


@router.get("/list", response_model=list[HandoffConversationItem])
async def handoff_list(
    status: str | None = None,
    all: bool = False,
    region: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """List conversations for handoff management."""
    q = select(Conversation).order_by(Conversation.updated_at.desc())

    if not all:
        q = q.where(Conversation.handoff_status != "none")
    if status:
        q = q.where(Conversation.handoff_status == status)
    if region:
        q = q.where(Conversation.customer_region == region)

    q = q.limit(200)
    result = await db.execute(q)
    convs = list(result.scalars().all())

    items = []
    for c in convs:
        await db.refresh(c, ["messages"])
        preview = c.messages[-1].content[:100] if c.messages else None
        items.append(HandoffConversationItem(
            id=c.id,
            visitor_id=c.visitor_id,
            customer_region=c.customer_region,
            customer_country_code=c.customer_country_code,
            customer_phone=c.customer_phone,
            language=c.language,
            turn_count=c.turn_count,
            lead_captured=c.lead_captured,
            handoff_status=c.handoff_status,
            handoff_at=c.handoff_at,
            whatsapp_tag=c.whatsapp_tag,
            telegram_account_name=c.telegram_account_name,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_preview=preview,
        ))
    return items


@router.get("/{conv_id}/messages", response_model=list[MessageOut])
async def handoff_messages(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


@router.post("/{conv_id}/channel")
async def update_handoff_channel(
    conv_id: str,
    body: HandoffChannelUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    account_name = (body.telegram_account_name or "").strip() or None
    if account_name and not _is_valid_telegram_account(account_name):
        raise HTTPException(status_code=400, detail=f"Invalid telegram_account_name: {account_name}")

    conv.telegram_account_name = account_name
    await db.commit()
    logger.info("Handoff channel updated for %s: telegram=%s", conv_id, account_name or "-")
    return {"status": "ok", "conversation_id": conv_id, "telegram_account_name": conv.telegram_account_name}


@router.post("/{conv_id}/accept")
async def accept_handoff(
    conv_id: str,
    body: HandoffAcceptRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Accept a handoff and set status to active."""
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if body and body.telegram_account_name:
        selected = body.telegram_account_name.strip()
        if selected and not _is_valid_telegram_account(selected):
            raise HTTPException(status_code=400, detail=f"Invalid telegram_account_name: {selected}")
        conv.telegram_account_name = selected or None

    conv.handoff_status = "active"
    conv.handoff_notice_sent = True
    if not conv.whatsapp_tag:
        conv.whatsapp_tag = uuid.uuid4().hex[:6]
    if not conv.handoff_at:
        conv.handoff_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Handoff accepted for conversation %s", conv_id)

    await db.refresh(conv, ["messages"])
    preview = conv.messages[-1].content[:200] if conv.messages else "(no message yet)"

    if whatsapp_client.is_enabled():
        await whatsapp_client.notify_handoff(conv.whatsapp_tag, conv.visitor_id, preview)
    if telegram_client.is_enabled():
        await telegram_client.notify_handoff(
            conv.whatsapp_tag,
            conv.visitor_id,
            preview,
            account_name=conv.telegram_account_name,
            customer_phone=conv.customer_phone,
            customer_region=conv.customer_region,
        )
    if gchat_client.is_enabled():
        await gchat_client.notify_handoff(conv.whatsapp_tag, conv.visitor_id, preview)

    user_ws = get_user_ws(conv_id)
    if user_ws:
        try:
            await user_ws.send_text(json.dumps({
                "type": "system",
                "content": "sales_connected",
            }))
        except Exception:
            pass

    return {
        "status": "active",
        "conversation_id": conv_id,
        "telegram_account_name": conv.telegram_account_name,
    }


@router.post("/{conv_id}/reply")
async def reply_to_user(
    conv_id: str,
    body: HandoffReply,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.handoff_status != "active":
        conv.handoff_status = "active"
        conv.handoff_notice_sent = True
        if not conv.handoff_at:
            conv.handoff_at = datetime.now(timezone.utc)

    msg = Message(
        conversation_id=conv_id,
        role="assistant",
        content=body.message,
        confidence=1.0,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    logger.info("Admin reply sent to conversation %s", conv_id)

    user_ws = get_user_ws(conv_id)
    if user_ws:
        try:
            await user_ws.send_text(json.dumps({
                "type": "agent_message",
                "content": body.message,
            }))
        except Exception:
            logger.warning("Failed to push agent message via WS for %s", conv_id)

    return {"status": "sent", "message_id": msg.id}


@router.post("/{conv_id}/resolve")
async def resolve_handoff(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.handoff_status = "resolved"
    conv.handoff_notice_sent = False
    await db.commit()
    logger.info("Handoff resolved for conversation %s", conv_id)

    user_ws = get_user_ws(conv_id)
    if user_ws:
        try:
            await user_ws.send_text(json.dumps({
                "type": "system",
                "content": "handoff_resolved",
            }))
        except Exception:
            pass

    return {"status": "resolved", "conversation_id": conv_id}
