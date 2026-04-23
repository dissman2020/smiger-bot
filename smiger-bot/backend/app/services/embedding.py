import logging

from app.core.rag_engine import add_document_chunks, chunk_text
from app.services.document import parse_file

logger = logging.getLogger(__name__)


async def process_document(doc_id: str, filename: str, content: bytes, content_type: str | None = None) -> int:
    """Parse a file, chunk it, embed it, and store in the vector DB. Returns chunk count."""
    text = parse_file(content, filename, content_type)
    if not text.strip():
        raise ValueError(f"No text could be extracted from {filename}")

    chunks = chunk_text(text)
    logger.info("Parsed %s: %d chars -> %d chunks", filename, len(text), len(chunks))

    count = await add_document_chunks(doc_id, chunks, filename)
    return count
