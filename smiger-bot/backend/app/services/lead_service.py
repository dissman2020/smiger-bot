import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Conversation, Lead
from app.models.schemas import LeadCreate

logger = logging.getLogger(__name__)


async def _notify_channels(lead: Lead) -> None:
    from app.core import telegram_client, gchat_client
    lead_kwargs = dict(
        lead_name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        country=lead.country,
        requirement=lead.requirement,
    )
    if telegram_client.is_enabled():
        try:
            await telegram_client.notify_new_lead(**lead_kwargs)
        except Exception:
            logger.exception("Failed to send Telegram lead notification")
    if gchat_client.is_enabled():
        try:
            await gchat_client.notify_new_lead(**lead_kwargs)
        except Exception:
            logger.exception("Failed to send Google Chat lead notification")


async def create_lead(db: AsyncSession, data: LeadCreate) -> Lead:
    lead = Lead(
        conversation_id=data.conversation_id,
        name=data.name,
        company=data.company,
        email=data.email,
        phone=data.phone,
        country=data.country,
        requirement=data.requirement,
    )
    db.add(lead)

    if data.conversation_id:
        result = await db.execute(select(Conversation).where(Conversation.id == data.conversation_id))
        conv = result.scalar_one_or_none()
        if conv:
            conv.lead_captured = True

    await db.commit()
    await db.refresh(lead)

    asyncio.create_task(_notify_channels(lead))

    return lead


async def get_leads(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Lead]:
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_lead_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Lead.id)))
    return result.scalar() or 0
