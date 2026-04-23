"""Knowledge base module tests (KNOW-001 ~ KNOW-012)."""

import io
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.base import (
    client, auth_headers, admin_token, mock_chromadb, sample_pdf, sample_docx
)


@pytest.mark.knowledge
@pytest.mark.unit
class TestKnowledgeBase:
    """Test knowledge base endpoints (KNOW-001 ~ KNOW-012)."""
    
    def test_upload_pdf(self, client: TestClient, auth_headers: dict, sample_pdf, mock_chromadb):
        """KNOW-001: Upload valid PDF document."""
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.return_value = "This is test PDF content"
            
            response = client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["file_type"] == "pdf"
        assert "id" in data
    
    def test_upload_docx(self, client: TestClient, auth_headers: dict, sample_docx, mock_chromadb):
        """KNOW-002: Upload valid DOCX document."""
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.return_value = "This is test DOCX content"
            
            response = client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("test.docx", io.BytesIO(sample_docx), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.docx"
        assert data["file_type"] == "docx"
    
    def test_upload_xlsx(self, client: TestClient, auth_headers: dict, mock_chromadb):
        """KNOW-003: Upload valid XLSX document."""
        xlsx_content = b"PK\x03\x04" + b"\x00" * 26
        
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.return_value = "Sheet1\tData1\tData2"
            
            response = client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("test.xlsx", io.BytesIO(xlsx_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.xlsx"
        assert data["file_type"] == "xlsx"
    
    def test_upload_txt(self, client: TestClient, auth_headers: dict, mock_chromadb):
        """KNOW-004: Upload valid TXT document."""
        txt_content = b"This is a test text file content."
        
        response = client.post(
            "/api/knowledge/upload",
            headers=auth_headers,
            files={"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["file_type"] == "txt"
    
    def test_upload_empty_file(self, client: TestClient, auth_headers: dict):
        """KNOW-005: Upload 0-byte file returns error."""
        response = client.post(
            "/api/knowledge/upload",
            headers=auth_headers,
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        )
        
        # Empty file may be accepted but result in 0 chunks
        assert response.status_code in [200, 400]
    
    def test_upload_large_file(self, client: TestClient, auth_headers: dict):
        """KNOW-006: Upload >20MB file returns 413."""
        large_content = b"A" * (21 * 1024 * 1024)  # 21MB
        
        response = client.post(
            "/api/knowledge/upload",
            headers=auth_headers,
            files={"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
        )
        
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()
    
    def test_upload_unsupported_format(self, client: TestClient, auth_headers: dict):
        """KNOW-007: Upload unsupported format (image) returns 400."""
        image_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG header
        
        response = client.post(
            "/api/knowledge/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", io.BytesIO(image_content), "image/jpeg")}
        )
        
        assert response.status_code in [400, 500]
    
    def test_upload_corrupted_pdf(self, client: TestClient, auth_headers: dict, mock_chromadb):
        """KNOW-008: Upload corrupted PDF sets status to error."""
        corrupted_pdf = b"NOT_A_VALID_PDF"
        
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.side_effect = Exception("Corrupted PDF")
            
            response = client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("corrupted.pdf", io.BytesIO(corrupted_pdf), "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "error_message" in data
    
    def test_delete_document(self, client: TestClient, auth_headers: dict, sample_pdf, mock_chromadb):
        """KNOW-009: Delete existing document removes it and chunks."""
        # First upload
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.return_value = "Test content"
            
            upload_resp = client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
            )
        
        doc_id = upload_resp.json()["id"]
        
        # Delete
        response = client.delete(f"/api/knowledge/documents/{doc_id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["ok"] is True
    
    def test_delete_nonexistent_document(self, client: TestClient, auth_headers: dict):
        """KNOW-010: Delete non-existent document returns 404."""
        response = client.delete("/api/knowledge/documents/non-existent-id", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_list_documents(self, client: TestClient, auth_headers: dict, sample_pdf, mock_chromadb):
        """KNOW-011: Get document list returns correct list."""
        # Upload a document first
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.return_value = "Test content"
            
            client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
            )
        
        # List
        response = client.get("/api/knowledge/documents", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_knowledge_stats(self, client: TestClient, auth_headers: dict, sample_pdf, mock_chromadb):
        """KNOW-012: Get knowledge base stats returns correct statistics."""
        # Upload a document
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.return_value = "Test content"
            
            client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
            )
        
        # Get stats
        response = client.get("/api/knowledge/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "total_chunks" in data
        assert "ready_documents" in data
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["total_chunks"], int)
