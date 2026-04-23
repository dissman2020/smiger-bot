from __future__ import annotations

import asyncio
import logging
from typing import Any

import chromadb

from app.config import settings
from app.core.llm_gateway import get_embedding, get_embeddings_batch

logger = logging.getLogger(__name__)

_chroma_client: Any = None
COLLECTION_NAME = "smiger_knowledge"


def _get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _chroma_client


def _get_collection() -> chromadb.Collection:
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_text(text: str, chunk_size: int | None = None, chunk_overlap: int | None = None) -> list[str]:
    """Split text into overlapping chunks."""
    size = chunk_size or settings.CHUNK_SIZE
    overlap = chunk_overlap or settings.CHUNK_OVERLAP
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += size - overlap
    return chunks


def chunk_faq_entries(entries: list[dict]) -> list[tuple[str, dict]]:
    """Convert structured FAQ entries into (text, metadata) pairs.

    Each Q&A pair becomes one chunk keeping bilingual content together.
    Returns list of (chunk_text, metadata_dict).
    """
    results: list[tuple[str, dict]] = []
    for entry in entries:
        text_parts = []
        if entry.get("question_cn"):
            text_parts.append(f"问：{entry['question_cn']}")
        if entry.get("question_en"):
            text_parts.append(f"Q: {entry['question_en']}")
        if entry.get("answer_cn"):
            text_parts.append(f"答：{entry['answer_cn']}")
        if entry.get("answer_en"):
            text_parts.append(f"A: {entry['answer_en']}")

        chunk_text_content = "\n".join(text_parts)
        meta = {
            "type": "faq",
            "category": entry.get("category", "general"),
            "faq_id": str(entry.get("id", "")),
        }
        tags = entry.get("tags")
        if tags:
            meta["tags"] = ",".join(tags) if isinstance(tags, list) else str(tags)
        results.append((chunk_text_content, meta))
    return results


async def add_document_chunks(
    doc_id: str,
    chunks: list[str],
    filename: str,
    extra_meta: dict | None = None,
) -> int:
    """Embed and store document chunks in ChromaDB. Returns chunk count."""
    if not chunks:
        return 0

    batch_size = 50
    total_added = 0
    base_meta = {"doc_id": doc_id, "filename": filename, "type": "document"}
    if extra_meta:
        base_meta.update(extra_meta)

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = await get_embeddings_batch(batch)

        ids = [f"{doc_id}_{i + j}" for j in range(len(batch))]
        metadatas = [{**base_meta, "chunk_index": i + j} for j in range(len(batch))]

        loop = asyncio.get_event_loop()
        collection = _get_collection()
        await loop.run_in_executor(
            None,
            lambda _ids=ids, _emb=embeddings, _docs=batch, _meta=metadatas: collection.add(
                ids=_ids, embeddings=_emb, documents=_docs, metadatas=_meta
            ),
        )
        total_added += len(batch)

    logger.info("Added %d chunks for document %s", total_added, doc_id)
    return total_added


async def add_faq_chunks(faq_pairs: list[tuple[str, dict]]) -> int:
    """Embed and store FAQ Q&A pairs with rich metadata. Returns chunk count."""
    if not faq_pairs:
        return 0

    texts = [t for t, _ in faq_pairs]
    metas = [m for _, m in faq_pairs]
    embeddings = await get_embeddings_batch(texts)

    ids = [f"faq_{m.get('faq_id', i)}" for i, m in enumerate(metas)]

    loop = asyncio.get_event_loop()
    collection = _get_collection()
    await loop.run_in_executor(
        None,
        lambda: collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas),
    )
    logger.info("Added %d FAQ chunks", len(faq_pairs))
    return len(faq_pairs)


async def delete_faq_chunks() -> None:
    """Remove all FAQ-type chunks from ChromaDB."""
    loop = asyncio.get_event_loop()
    collection = _get_collection()
    try:
        await loop.run_in_executor(
            None,
            lambda: collection.delete(where={"type": "faq"}),
        )
        logger.info("Deleted all FAQ chunks")
    except Exception:
        logger.warning("No FAQ chunks to delete or delete failed, continuing")


async def search(
    query: str,
    top_k: int | None = None,
    category: str | None = None,
) -> list[dict]:
    """Search the knowledge base and return relevant chunks with scores.

    Optionally filter by category (for FAQ entries).
    """
    k = top_k or settings.RETRIEVAL_TOP_K
    query_embedding = await get_embedding(query)

    where_filter = None
    if category:
        where_filter = {"category": category}

    loop = asyncio.get_event_loop()
    collection = _get_collection()

    def _query():
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": k,
            "include": ["documents", "distances", "metadatas"],
        }
        if where_filter:
            kwargs["where"] = where_filter
        return collection.query(**kwargs)

    results = await loop.run_in_executor(None, _query)

    if not results["documents"] or not results["documents"][0]:
        return []

    items: list[dict] = []
    for doc, dist, meta in zip(results["documents"][0], results["distances"][0], results["metadatas"][0]):
        similarity = 1 - dist
        items.append({"text": doc, "similarity": similarity, "metadata": meta})
    return items


async def delete_document_chunks(doc_id: str) -> None:
    """Remove all chunks for a given document."""
    loop = asyncio.get_event_loop()
    collection = _get_collection()
    await loop.run_in_executor(
        None,
        lambda _did=doc_id: collection.delete(where={"doc_id": _did}),
    )
    logger.info("Deleted chunks for document %s", doc_id)


def get_collection_count() -> int:
    return _get_collection().count()
