from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.models.database import Conversation, Document, Lead, Message, get_db
from app.models.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(verify_token)])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_conv = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    total_msg = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    total_leads = (await db.execute(select(func.count(Lead.id)))).scalar() or 0
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    conv_today = (await db.execute(
        select(func.count(Conversation.id)).where(Conversation.created_at >= today_start)
    )).scalar() or 0
    leads_today = (await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= today_start)
    )).scalar() or 0

    return DashboardStats(
        total_conversations=total_conv,
        total_messages=total_msg,
        total_leads=total_leads,
        total_documents=total_docs,
        conversations_today=conv_today,
        leads_today=leads_today,
    )
