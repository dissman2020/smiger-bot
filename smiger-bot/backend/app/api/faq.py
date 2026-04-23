"""FAQ management API — CRUD + bulk import + sync to vector DB."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.models.database import FaqEntry, get_db
from app.models.schemas import FaqEntryCreate, FaqEntryOut, FaqEntryUpdate, FaqSyncResult
from app.core.rag_engine import add_faq_chunks, chunk_faq_entries, delete_faq_chunks
from app.services.faq_parser import parse_faq_text
from app.services.document import parse_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/faq", tags=["faq"])


@router.get("/entries", response_model=list[FaqEntryOut])
async def list_entries(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    q: Optional[str] = Query(None, description="Search in questions/answers"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    stmt = select(FaqEntry).order_by(FaqEntry.sort_order, FaqEntry.id)
    if category:
        stmt = stmt.where(FaqEntry.category == category)
    if is_active is not None:
        stmt = stmt.where(FaqEntry.is_active == is_active)

    result = await db.execute(stmt)
    entries = list(result.scalars().all())

    if q:
        q_lower = q.lower()
        entries = [
            e for e in entries
            if q_lower in (e.question_cn or "").lower()
            or q_lower in (e.question_en or "").lower()
            or q_lower in (e.answer_cn or "").lower()
            or q_lower in (e.answer_en or "").lower()
        ]
    return entries


@router.post("/entries", response_model=FaqEntryOut)
async def create_entry(
    body: FaqEntryCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    entry = FaqEntry(
        category=body.category,
        question_cn=body.question_cn,
        question_en=body.question_en,
        answer_cn=body.answer_cn,
        answer_en=body.answer_en,
        tags=body.tags,
        extra_metadata=body.extra_metadata,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/entries/{entry_id}", response_model=FaqEntryOut)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    entry = await db.get(FaqEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
    return entry


@router.put("/entries/{entry_id}", response_model=FaqEntryOut)
async def update_entry(
    entry_id: int,
    body: FaqEntryUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    entry = await db.get(FaqEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="FAQ entry not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    entry = await db.get(FaqEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
    await db.delete(entry)
    await db.commit()
    return {"ok": True, "deleted_id": entry_id}


@router.post("/import", response_model=dict)
async def import_faq(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Bulk import FAQ entries from a file.

    Supports:
    - .json: array of {question_cn, question_en, answer_cn, answer_en, category, tags}
    - .doc/.docx/.txt: auto-parsed via FAQ parser (bilingual Q&A detection)
    """
    content = await file.read()
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    entries_data: list[dict] = []

    if ext == "json":
        try:
            raw = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        if isinstance(raw, list):
            entries_data = raw
        else:
            raise HTTPException(status_code=400, detail="JSON must be an array of FAQ objects")
    else:
        text = parse_file(content, filename, file.content_type)
        parsed = parse_faq_text(text)
        for item in parsed:
            entries_data.append({
                "category": item.category,
                "question_cn": item.question_cn,
                "question_en": item.question_en,
                "answer_cn": item.answer_cn,
                "answer_en": item.answer_en,
                "tags": item.tags,
                "extra_metadata": item.extra_metadata,
            })

    created = 0
    for data in entries_data:
        if not data.get("question_cn") and not data.get("question_en"):
            continue
        entry = FaqEntry(
            category=data.get("category", "general"),
            question_cn=data.get("question_cn", ""),
            question_en=data.get("question_en", ""),
            answer_cn=data.get("answer_cn", ""),
            answer_en=data.get("answer_en", ""),
            tags=data.get("tags"),
            extra_metadata=data.get("extra_metadata"),
            sort_order=data.get("sort_order", 0),
        )
        db.add(entry)
        created += 1

    await db.commit()
    logger.info("Imported %d FAQ entries from %s", created, filename)
    return {"imported": created, "filename": filename}


@router.post("/sync", response_model=FaqSyncResult)
async def sync_to_knowledge_base(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Re-embed all active FAQ entries into the vector knowledge base."""
    result = await db.execute(
        select(FaqEntry).where(FaqEntry.is_active == True).order_by(FaqEntry.sort_order, FaqEntry.id)
    )
    entries = list(result.scalars().all())

    await delete_faq_chunks()

    faq_dicts = []
    for e in entries:
        faq_dicts.append({
            "id": e.id,
            "category": e.category,
            "question_cn": e.question_cn,
            "question_en": e.question_en,
            "answer_cn": e.answer_cn,
            "answer_en": e.answer_en,
            "tags": e.tags or [],
        })

    pairs = chunk_faq_entries(faq_dicts)
    count = await add_faq_chunks(pairs)

    logger.info("Synced %d FAQ entries (%d chunks) to knowledge base", len(entries), count)
    return FaqSyncResult(total_entries=len(entries), total_chunks=count)


@router.get("/categories", response_model=list[dict])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """List all FAQ categories with counts."""
    result = await db.execute(
        select(FaqEntry.category, func.count(FaqEntry.id))
        .group_by(FaqEntry.category)
        .order_by(FaqEntry.category)
    )
    return [{"category": row[0], "count": row[1]} for row in result.all()]
