"""Base test fixtures and utilities."""

import os
import io
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# MUST set environment variables BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["LLM_API_KEY"] = "test-api-key"
os.environ["LLM_BASE_URL"] = "https://test.api.com"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test123"
os.environ["CHROMA_PERSIST_DIR"] = "/tmp/test_chroma"
os.environ["TELEGRAM_ENABLED"] = "false"
os.environ["WHATSAPP_ENABLED"] = "false"
os.environ["GCHAT_ENABLED"] = "false"

# Now import app
from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Provide a synchronous test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_llm_gateway():
    """Mock LLM gateway responses."""
    with patch("app.core.llm_gateway.chat_completion") as mock_chat, \
         patch("app.core.llm_gateway.chat_completion_stream") as mock_stream, \
         patch("app.core.llm_gateway.get_embedding") as mock_embed, \
         patch("app.core.llm_gateway.get_embeddings_batch") as mock_embed_batch:
        
        mock_chat.return_value = ("This is a test response", 0.95)
        mock_stream.return_value = AsyncMock()
        mock_embed.return_value = [0.1] * 1024
        mock_embed_batch.return_value = [[0.1] * 1024]
        
        yield {
            "chat": mock_chat,
            "stream": mock_stream,
            "embed": mock_embed,
            "embed_batch": mock_embed_batch,
        }


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("app.core.conversation._get_redis") as mock:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.delete.return_value = True
        mock.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    with patch("app.core.rag_engine._get_chroma_client") as mock:
        chroma_mock = MagicMock()
        collection_mock = MagicMock()
        collection_mock.query.return_value = {
            "documents": [["Test document"]],
            "distances": [[0.1]],
            "metadatas": [[{"filename": "test.pdf"}]],
        }
        collection_mock.count.return_value = 10
        collection_mock.add.return_value = None
        collection_mock.delete.return_value = None
        chroma_mock.get_or_create_collection.return_value = collection_mock
        mock.return_value = chroma_mock
        yield chroma_mock


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    content = b"%PDF-1.4 test content"
    return content


@pytest.fixture
def sample_docx():
    """Create a sample DOCX file for testing."""
    content = b"PK\x03\x04" + b"\x00" * 26
    return content


@pytest.fixture
def admin_token(client) -> str:
    """Get admin JWT token."""
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "test123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    return ""


@pytest.fixture
def auth_headers(admin_token) -> dict:
    """Get authentication headers."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_conversation_data(**kwargs):
        """Create conversation test data."""
        return {
            "visitor_id": kwargs.get("visitor_id", "test-visitor-123"),
            "language": kwargs.get("language", "en"),
            "customer_region": kwargs.get("customer_region"),
            "customer_country_code": kwargs.get("customer_country_code"),
            "customer_phone": kwargs.get("customer_phone"),
        }
    
    @staticmethod
    def create_lead_data(**kwargs):
        """Create lead test data."""
        return {
            "email": kwargs.get("email", "test@example.com"),
            "name": kwargs.get("name", "Test User"),
            "company": kwargs.get("company", "Test Company"),
            "phone": kwargs.get("phone", "+1234567890"),
            "country": kwargs.get("country", "US"),
            "requirement": kwargs.get("requirement", "Looking for guitars"),
        }
    
    @staticmethod
    def create_faq_data(**kwargs):
        """Create FAQ test data."""
        return {
            "category": kwargs.get("category", "general"),
            "question_cn": kwargs.get("question_cn", "测试问题？"),
            "question_en": kwargs.get("question_en", "Test question?"),
            "answer_cn": kwargs.get("answer_cn", "测试答案。"),
            "answer_en": kwargs.get("answer_en", "Test answer."),
            "tags": kwargs.get("tags", ["test", "sample"]),
            "sort_order": kwargs.get("sort_order", 0),
            "is_active": kwargs.get("is_active", True),
        }


@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory()
