import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_token
from app.core.rag_engine import delete_document_chunks, get_collection_count
from app.models.database import Document, get_db
from app.models.schemas import DocumentOut, KnowledgeStats
from app.services.embedding import process_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=DocumentOut, dependencies=[Depends(verify_token)])
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    doc = Document(filename=file.filename, file_type=ext, file_size=len(content))
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    try:
        chunk_count = await process_document(doc.id, file.filename, content, file.content_type)
        doc.chunk_count = chunk_count
        doc.status = "ready"
    except Exception as e:
        logger.exception("Failed to process document %s", file.filename)
        doc.status = "error"
        doc.error_message = str(e)

    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/documents", response_model=list[DocumentOut], dependencies=[Depends(verify_token)])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return list(result.scalars().all())


@router.delete("/documents/{doc_id}", dependencies=[Depends(verify_token)])
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await delete_document_chunks(doc_id)
    await db.delete(doc)
    await db.commit()
    return {"ok": True}


@router.get("/stats", response_model=KnowledgeStats, dependencies=[Depends(verify_token)])
async def knowledge_stats(db: AsyncSession = Depends(get_db)):
    total_q = await db.execute(select(func.count(Document.id)))
    ready_q = await db.execute(select(func.count(Document.id)).where(Document.status == "ready"))
    return KnowledgeStats(
        total_documents=total_q.scalar() or 0,
        total_chunks=get_collection_count(),
        ready_documents=ready_q.scalar() or 0,
    )
