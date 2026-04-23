import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.models.database import get_db
from app.models.schemas import LeadCreate, LeadOut
from app.services.lead_service import create_lead, get_lead_count, get_leads

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadOut)
async def submit_lead(body: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = await create_lead(db, body)
    return lead


@router.get("", response_model=list[LeadOut], dependencies=[Depends(verify_token)])
async def list_leads(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await get_leads(db, skip=skip, limit=limit)


@router.get("/count", dependencies=[Depends(verify_token)])
async def lead_count(db: AsyncSession = Depends(get_db)):
    return {"count": await get_lead_count(db)}


@router.get("/export", dependencies=[Depends(verify_token)])
async def export_leads_csv(db: AsyncSession = Depends(get_db)):
    leads = await get_leads(db, skip=0, limit=10000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Name", "Company", "Email", "Phone", "Country", "Requirement", "Source", "Created At"])
    for lead in leads:
        writer.writerow([
            lead.name, lead.company, lead.email, lead.phone,
            lead.country, lead.requirement, lead.source,
            lead.created_at.isoformat() if lead.created_at else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
