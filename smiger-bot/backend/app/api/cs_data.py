"""Customer-service data import / query / stats endpoints."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.models.database import CsRecord, get_db
from app.models.schemas import CsRecordCreate, CsRecordOut, CsStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/cs", tags=["customer-service"])


@router.get("/records", response_model=list[CsRecordOut])
async def list_records(
    status: str | None = None,
    channel: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    q = select(CsRecord).order_by(CsRecord.created_at.desc())
    if status:
        q = q.where(CsRecord.status == status)
    if channel:
        q = q.where(CsRecord.channel == channel)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/records", response_model=CsRecordOut)
async def create_record(
    body: CsRecordCreate,
    _: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    rec = CsRecord(**body.model_dump())
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.post("/records/import", response_model=dict)
async def import_records(
    file: UploadFile = File(...),
    _: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import CS records from a JSON file. Expects a JSON array of records."""
    content = await file.read()
    try:
        items: list[dict[str, Any]] = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array")

    count = 0
    for item in items:
        try:
            data = CsRecordCreate(**item)
            db.add(CsRecord(**data.model_dump()))
            count += 1
        except Exception:
            continue

    await db.commit()
    logger.info("Imported %d CS records", count)
    return {"imported": count, "skipped": len(items) - count}


@router.get("/records/{record_id}", response_model=CsRecordOut)
async def get_record(
    record_id: str,
    _: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CsRecord).where(CsRecord.id == record_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    return rec


@router.patch("/records/{record_id}", response_model=CsRecordOut)
async def update_record(
    record_id: str,
    body: dict,
    _: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CsRecord).where(CsRecord.id == record_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    allowed = {"status", "agent_name", "tags", "subject"}
    for k, v in body.items():
        if k in allowed:
            setattr(rec, k, v)
    if body.get("status") == "resolved" and not rec.resolved_at:
        rec.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(rec)
    return rec


@router.get("/stats", response_model=CsStats)
async def get_stats(
    _: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count(CsRecord.id)))).scalar() or 0
    open_count = (await db.execute(select(func.count(CsRecord.id)).where(CsRecord.status == "open"))).scalar() or 0
    resolved = (await db.execute(select(func.count(CsRecord.id)).where(CsRecord.status == "resolved"))).scalar() or 0

    ch_result = await db.execute(
        select(CsRecord.channel, func.count(CsRecord.id)).group_by(CsRecord.channel)
    )
    channels = {row[0]: row[1] for row in ch_result.all()}

    return CsStats(total=total, open=open_count, resolved=resolved, channels=channels)
