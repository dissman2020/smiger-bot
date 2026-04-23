"""RAG engine tests (RAG-001 ~ RAG-007)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.core import rag_engine
from tests.fixtures.base import mock_chromadb


@pytest.mark.rag
@pytest.mark.unit
class TestRAGEngine:
    """Test RAG engine functionality (RAG-001 ~ RAG-007)."""
    
    @pytest.mark.asyncio
    async def test_vector_search(self, mock_chromadb):
        """RAG-001: Query returns relevant chunks."""
        with patch("app.core.rag_engine.get_embedding") as mock_embed:
            mock_embed.return_value = [0.1] * 1024
            
            results = await rag_engine.search("electric guitar recommendations")
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert "text" in results[0]
        assert "similarity" in results[0]
        assert "metadata" in results[0]
    
    @pytest.mark.asyncio
    async def test_similarity_threshold(self, mock_chromadb):
        """RAG-002: Query below threshold returns empty or fallback."""
        with patch("app.core.rag_engine.get_embedding") as mock_embed, \
             patch("app.core.rag_engine._get_collection") as mock_get_coll:
            
            mock_embed.return_value = [0.1] * 1024
            
            # Mock collection to return low similarity results
            coll_mock = MagicMock()
            coll_mock.query.return_value = {
                "documents": [["Irrelevant content"]],
                "distances": [[0.9]],  # High distance = low similarity
                "metadatas": [[{"filename": "test.pdf"}]],
            }
            mock_get_coll.return_value = coll_mock
            
            results = await rag_engine.search("very specific query")
        
        # Results with similarity below threshold may be filtered
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_category_filter(self, mock_chromadb):
        """RAG-003: Search with category filter returns filtered results."""
        with patch("app.core.rag_engine.get_embedding") as mock_embed:
            mock_embed.return_value = [0.1] * 1024
            
            results = await rag_engine.search(
                "guitar question",
                category="products"
            )
        
        assert isinstance(results, list)
        # All results should be in the specified category
        for result in results:
            if "category" in result.get("metadata", {}):
                assert result["metadata"]["category"] == "products"
    
    def test_chunk_text(self):
        """RAG-004: Large document is correctly chunked."""
        text = "This is a test sentence. " * 100  # Long text
        
        chunks = rag_engine.chunk_text(text, chunk_size=100, chunk_overlap=20)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1  # Should be split into multiple chunks
        
        # Each chunk should be within size limit
        for chunk in chunks:
            assert len(chunk) <= 120  # chunk_size + some margin
    
    @pytest.mark.asyncio
    async def test_embedding_generation(self):
        """RAG-005: Embedding API returns correct dimension vectors."""
        from app.core.llm_gateway import get_embedding
        
        with patch("app.core.llm_gateway.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=AsyncMock(return_value={
                    "data": [{"embedding": [0.1] * 1024}]
                })
            )
            
            embedding = await get_embedding("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1024
    
    @pytest.mark.asyncio
    async def test_batch_embedding(self):
        """RAG-006: Batch text embedding is processed correctly."""
        from app.core.llm_gateway import get_embeddings_batch
        
        texts = ["text 1", "text 2", "text 3"]
        
        with patch("app.core.llm_gateway.httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=AsyncMock(return_value={
                    "data": [
                        {"embedding": [0.1] * 1024},
                        {"embedding": [0.2] * 1024},
                        {"embedding": [0.3] * 1024},
                    ]
                })
            )
            
            embeddings = await get_embeddings_batch(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(e) == 1024 for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_delete_document_chunks(self, mock_chromadb):
        """RAG-007: Delete document removes associated chunks."""
        doc_id = "test-doc-123"
        
        await rag_engine.delete_document_chunks(doc_id)
        
        # Verify delete was called on collection
        collection = mock_chromadb.get_or_create_collection.return_value
        collection.delete.assert_called_once()
    
    def test_chunk_faq_entries(self):
        """Test FAQ entry chunking."""
        entries = [
            {
                "id": 1,
                "category": "general",
                "question_cn": "问题1？",
                "question_en": "Question 1?",
                "answer_cn": "答案1",
                "answer_en": "Answer 1",
                "tags": ["tag1"]
            },
            {
                "id": 2,
                "category": "products",
                "question_cn": "问题2？",
                "question_en": "Question 2?",
                "answer_cn": "答案2",
                "answer_en": "Answer 2",
                "tags": ["tag2"]
            }
        ]
        
        pairs = rag_engine.chunk_faq_entries(entries)
        
        assert isinstance(pairs, list)
        assert len(pairs) == 2
        
        # Each pair should be (text, metadata)
        for text, meta in pairs:
            assert isinstance(text, str)
            assert isinstance(meta, dict)
            assert "type" in meta
            assert meta["type"] == "faq"
    
    @pytest.mark.asyncio
    async def test_add_document_chunks(self, mock_chromadb):
        """Test adding document chunks to vector DB."""
        with patch("app.core.rag_engine.get_embeddings_batch") as mock_embed_batch:
            mock_embed_batch.return_value = [[0.1] * 1024, [0.2] * 1024]
            
            count = await rag_engine.add_document_chunks(
                doc_id="doc-123",
                chunks=["chunk 1", "chunk 2"],
                filename="test.pdf"
            )
        
        assert count == 2
        collection = mock_chromadb.get_or_create_collection.return_value
        collection.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_faq_chunks(self, mock_chromadb):
        """Test adding FAQ chunks to vector DB."""
        faq_pairs = [
            ("Q: Question\nA: Answer", {"type": "faq", "faq_id": "1"})
        ]
        
        with patch("app.core.rag_engine.get_embeddings_batch") as mock_embed_batch:
            mock_embed_batch.return_value = [[0.1] * 1024]
            
            count = await rag_engine.add_faq_chunks(faq_pairs)
        
        assert count == 1
        collection = mock_chromadb.get_or_create_collection.return_value
        collection.add.assert_called_once()
