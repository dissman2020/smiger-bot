import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.config import settings
from app.core import gchat_client, telegram_client, whatsapp_client
from app.core.conversation import ConversationManager
from app.core.intent_detector import detect_purchase_intent
from app.core.product_recommender import extract_product_cards
from app.core.ws_registry import register_user, unregister_user
from app.models.database import Conversation, Lead, Message, async_session, get_db
from app.models.schemas import ChatRequest, ChatResponse, ConversationListItem, ConversationOut

# Redis 客户端（用于分布式锁）
import redis.asyncio as aioredis

_redis: aioredis.Redis | None = None

async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


@asynccontextmanager
async def conversation_lock(conversation_id: str, timeout: int = 30):
    """
    分布式锁：确保同一会话的消息串行处理
    防止 turn_count 竞态和消息乱序
    """
    r = await _get_redis()
    lock_key = f"lock:conv:{conversation_id}"
    lock_value = uuid.uuid4().hex

    # 尝试获取锁
    acquired = await r.set(lock_key, lock_value, nx=True, ex=timeout)
    if not acquired:
        raise HTTPException(status_code=429, detail="Message processing, please try again")

    try:
        yield lock_value
    finally:
        # 释放锁（使用 Lua 脚本确保原子性）
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await r.eval(lua_script, 1, lock_key, lock_value)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

conv_manager = ConversationManager()


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _apply_customer_profile(
    conv: Conversation,
    *,
    customer_region: str | None,
    customer_country_code: str | None,
    customer_phone: str | None,
) -> bool:
    changed = False

    region = _clean(customer_region)
    code = _clean(customer_country_code)
    phone = _clean(customer_phone)

    if region and conv.customer_region != region:
        conv.customer_region = region
        changed = True
    if code and conv.customer_country_code != code:
        conv.customer_country_code = code
        changed = True
    if phone and conv.customer_phone != phone:
        conv.customer_phone = phone
        changed = True

    return changed


async def _handle_human_active_message(
    db: AsyncSession,
    conv: Conversation,
    user_message: str,
) -> tuple[bool, bool]:
    """Store user message and route to human channels while handoff is active.

    Returns:
        (first_notice_sent_now, handoff_active)
    """
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    conv.turn_count += 1

    first_notice = not conv.handoff_notice_sent
    if first_notice:
        conv.handoff_notice_sent = True

    await db.commit()

    if conv.whatsapp_tag:
        if whatsapp_client.is_enabled():
            await whatsapp_client.forward_user_message(conv.whatsapp_tag, user_message)
        if telegram_client.is_enabled():
            await telegram_client.forward_user_message(
                conv.whatsapp_tag,
                user_message,
                account_name=conv.telegram_account_name,
            )
        if gchat_client.is_enabled():
            await gchat_client.forward_user_message(conv.whatsapp_tag, user_message)

    return first_notice, True


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Non-streaming chat endpoint for simple integrations."""
    visitor_id = body.visitor_id or str(uuid.uuid4())

    if body.conversation_id:
        result = await db.execute(select(Conversation).where(Conversation.id == body.conversation_id))
        conv = result.scalar_one_or_none()
    else:
        conv = None

    if conv is None:
        kwargs = {
            "visitor_id": visitor_id,
            "language": body.language,
            "customer_region": _clean(body.customer_region) or None,
            "customer_country_code": _clean(body.customer_country_code) or None,
            "customer_phone": _clean(body.customer_phone) or None,
        }
        if body.conversation_id:
            kwargs["id"] = body.conversation_id
        conv = Conversation(**kwargs)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    else:
        profile_changed = _apply_customer_profile(
            conv,
            customer_region=body.customer_region,
            customer_country_code=body.customer_country_code,
            customer_phone=body.customer_phone,
        )
        if profile_changed:
            await db.commit()

    if conv.handoff_status == "active":
        # 转人工状态也需要锁保护，防止消息乱序
        async with conversation_lock(conv.id, timeout=30):
            first_notice, _ = await _handle_human_active_message(db, conv, body.message)
        return ChatResponse(
            conversation_id=conv.id,
            message="您的消息已转给人工客服处理。" if first_notice else "",
            confidence=1.0,
            lead_prompt=False,
        )

    # 使用分布式锁确保同一会话的消息串行处理
    async with conversation_lock(conv.id, timeout=30):
        reply, confidence, lead_prompt = await conv_manager.handle_message(
            db=db,
            conversation=conv,
            user_message=body.message,
        )

    return ChatResponse(
        conversation_id=conv.id,
        message=reply,
        confidence=confidence,
        lead_prompt=lead_prompt,
        products=extract_product_cards(reply),
    )


@router.websocket("/ws/{conversation_id}")
async def chat_ws(websocket: WebSocket, conversation_id: str):
    """Streaming chat via WebSocket."""
    await websocket.accept()
    register_user(conversation_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_message = payload.get("message", "")
            visitor_id = payload.get("visitor_id", str(uuid.uuid4()))
            language = payload.get("language", "en")
            customer_region = payload.get("customer_region")
            customer_country_code = payload.get("customer_country_code")
            customer_phone = payload.get("customer_phone")

            async with async_session() as db:
                result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
                conv = result.scalar_one_or_none()

                if conv is None:
                    conv = Conversation(
                        id=conversation_id,
                        visitor_id=visitor_id,
                        language=language,
                        customer_region=_clean(customer_region) or None,
                        customer_country_code=_clean(customer_country_code) or None,
                        customer_phone=_clean(customer_phone) or None,
                    )
                    db.add(conv)
                    await db.commit()
                    await db.refresh(conv)
                else:
                    profile_changed = _apply_customer_profile(
                        conv,
                        customer_region=customer_region,
                        customer_country_code=customer_country_code,
                        customer_phone=customer_phone,
                    )
                    if profile_changed:
                        await db.commit()

                # 使用分布式锁确保消息处理串行化
                lock_acquired = False
                try:
                    async with conversation_lock(conv.id, timeout=30):
                        lock_acquired = True

                        # Human handoff active: store message and route to channels.
                        if conv.handoff_status == "active":
                            first_notice, _ = await _handle_human_active_message(db, conv, user_message)
                            await db.commit()

                            if first_notice:
                                await websocket.send_text(json.dumps({
                                    "type": "token",
                                    "content": "人工客服已接入，您的消息会直接转给客服处理。",
                                }))

                            await websocket.send_text(json.dumps({
                                "type": "done",
                                "conversation_id": conv.id,
                                "confidence": 1.0,
                                "lead_prompt": False,
                                "handoff_active": True,
                            }))
                            continue

                        # Normal AI processing.
                        full_reply = ""
                        confidence = 0.0
                        lead_prompt = False

                        async for token, meta in conv_manager.handle_message_stream(
                            db=db,
                            conversation=conv,
                            user_message=user_message,
                        ):
                            if meta:
                                confidence = meta.get("confidence", 0.0)
                                lead_prompt = meta.get("lead_prompt", False)
                            else:
                                full_reply += token
                                await websocket.send_text(json.dumps({"type": "token", "content": token}))

                        product_cards = extract_product_cards(full_reply)
                        if product_cards:
                            await websocket.send_text(json.dumps({
                                "type": "products",
                                "items": product_cards,
                            }))

                        handoff_triggered = False
                        if conv.handoff_status in ("none", "resolved"):
                            if detect_purchase_intent(user_message, full_reply):
                                conv.handoff_status = "pending"
                                conv.handoff_at = datetime.now(timezone.utc)
                                conv.handoff_notice_sent = False
                                if not conv.whatsapp_tag:
                                    conv.whatsapp_tag = uuid.uuid4().hex[:6]
                                await db.commit()
                                handoff_triggered = True
                                logger.info("Purchase intent detected for conversation %s", conv.id)

                except HTTPException as e:
                    if e.status_code == 429:
                        # 锁获取失败，提示用户稍后重试
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": "消息处理中，请稍后再试",
                        }))
                        await websocket.send_text(json.dumps({
                            "type": "done",
                            "conversation_id": conv.id,
                            "confidence": 0.0,
                            "lead_prompt": False,
                        }))
                        continue
                    raise

                        preview = user_message[:200] if user_message else full_reply[:200]
                        if whatsapp_client.is_enabled():
                            await whatsapp_client.notify_handoff(
                                conv.whatsapp_tag,
                                conv.visitor_id,
                                preview,
                            )
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
                            await gchat_client.notify_handoff(
                                conv.whatsapp_tag,
                                conv.visitor_id,
                                preview,
                            )

                        if handoff_triggered:
                            await websocket.send_text(json.dumps({
                                "type": "handoff",
                                "reason": "purchase_intent",
                            }))

                        await websocket.send_text(json.dumps({
                            "type": "done",
                            "conversation_id": conv.id,
                            "confidence": confidence,
                            "lead_prompt": lead_prompt or handoff_triggered,
                            "handoff_active": conv.handoff_status in ("pending", "active"),
                        }))

                except HTTPException as e:
                    if e.status_code == 429:
                        # 锁获取失败，提示用户稍后重试
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": "消息处理中，请稍后再试",
                        }))
                        await websocket.send_text(json.dumps({
                            "type": "done",
                            "conversation_id": conv.id,
                            "confidence": 0.0,
                            "lead_prompt": False,
                        }))
                        continue
                    raise

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", conversation_id)
    except Exception:
        logger.exception("WebSocket error for %s", conversation_id)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "An error occurred. Please try again.",
            }))
            await websocket.send_text(json.dumps({
                "type": "done",
                "conversation_id": conversation_id,
                "confidence": 0.0,
                "lead_prompt": False,
            }))
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        unregister_user(conversation_id)


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
    )
    convs = list(result.scalars().all())
    items = []
    for c in convs:
        await db.refresh(c, ["messages"])
        preview = c.messages[-1].content[:100] if c.messages else None
        items.append(ConversationListItem(
            id=c.id,
            visitor_id=c.visitor_id,
            customer_region=c.customer_region,
            customer_country_code=c.customer_country_code,
            customer_phone=c.customer_phone,
            language=c.language,
            turn_count=c.turn_count,
            lead_captured=c.lead_captured,
            handoff_status=c.handoff_status or "none",
            created_at=c.created_at,
            message_preview=preview,
        ))
    return items


@router.get("/conversations/{conv_id}", response_model=ConversationOut)
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.refresh(conv, ["messages"])
    return conv


@router.delete("/conversations")
async def clear_conversations_history(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Clear all chat history for admin maintenance."""
    try:
        lead_unlink = await db.execute(
            update(Lead)
            .where(Lead.conversation_id.is_not(None))
            .values(conversation_id=None)
        )
        msg_deleted = await db.execute(delete(Message))
        conv_deleted = await db.execute(delete(Conversation))
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to clear conversation history")
        raise HTTPException(status_code=500, detail="Failed to clear history")

    return {
        "status": "ok",
        "leads_unlinked": lead_unlink.rowcount or 0,
        "messages_deleted": msg_deleted.rowcount or 0,
        "conversations_deleted": conv_deleted.rowcount or 0,
    }
