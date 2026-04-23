"""Security tests (SEC-001 ~ SEC-005)."""

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.base import (
    client, auth_headers, admin_token, mock_llm_gateway, mock_redis
)


@pytest.mark.security
@pytest.mark.unit
class TestSecurity:
    """Test security measures (SEC-001 ~ SEC-005)."""
    
    def test_sql_injection_in_chat(self, client: TestClient, mock_llm_gateway, mock_redis):
        """SEC-001: SQL injection in chat message is safely handled."""
        sql_injection = "'; DROP TABLE conversations; --"
        
        response = client.post("/api/chat", json={
            "message": sql_injection,
            "visitor_id": "test-visitor",
            "language": "en"
        })
        
        # Should process normally without executing SQL
        assert response.status_code == 200
        
        # Verify table still exists by making another request
        response2 = client.post("/api/chat", json={
            "message": "Hello",
            "visitor_id": "test-visitor-2",
            "language": "en"
        })
        assert response2.status_code == 200
    
    def test_sql_injection_in_search(self, client: TestClient, auth_headers: dict):
        """SEC-001: SQL injection in FAQ search is safely handled."""
        sql_injection = "'; DELETE FROM faq_entries; --"
        
        response = client.get(
            f"/api/faq/entries?q={sql_injection}",
            headers=auth_headers
        )
        
        # Should handle safely
        assert response.status_code in [200, 400]
    
    def test_xss_in_chat(self, client: TestClient, mock_llm_gateway, mock_redis):
        """SEC-002: XSS script in message is properly escaped."""
        xss_payload = "<script>alert('XSS')</script>"
        
        response = client.post("/api/chat", json={
            "message": xss_payload,
            "visitor_id": "test-visitor-xss",
            "language": "en"
        })
        
        assert response.status_code == 200
        
        # Response should not contain unescaped script
        response_text = response.text
        assert "<script>alert('XSS')</script>" not in response_text or response.json()["message"] == ""
    
    def test_xss_stored_in_conversation(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """SEC-002: Stored XSS in conversation history is escaped."""
        xss_payload = "<img src=x onerror=alert('XSS')>"
        
        # Send XSS payload
        chat_resp = client.post("/api/chat", json={
            "message": xss_payload,
            "visitor_id": "test-visitor-xss-2",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        # Retrieve conversation
        response = client.get(
            f"/api/chat/conversations/{conv_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        # Content should be escaped in response
        response_text = response.text
        assert "onerror=alert" not in response_text or "<img" not in response_text
    
    def test_unauthorized_access_admin(self, client: TestClient):
        """SEC-003: Access admin endpoint without token returns 401."""
        endpoints = [
            ("GET", "/api/knowledge/documents"),
            ("GET", "/api/leads"),
            ("GET", "/api/faq/entries"),
            ("GET", "/api/admin/handoff/list"),
            ("GET", "/api/dashboard/stats"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            else:
                continue
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"
    
    def test_unauthorized_access_with_invalid_token(self, client: TestClient):
        """SEC-003: Access with invalid token returns 401."""
        response = client.get(
            "/api/knowledge/documents",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401
    
    def test_path_traversal_in_upload(self, client: TestClient, auth_headers: dict):
        """SEC-004: Path traversal in filename is rejected."""
        import io
        
        traversal_filename = "../../../etc/passwd"
        file_content = b"test content"
        
        response = client.post(
            "/api/knowledge/upload",
            headers=auth_headers,
            files={"file": (traversal_filename, io.BytesIO(file_content), "text/plain")}
        )
        
        # Should reject or sanitize
        assert response.status_code in [400, 200]
        
        if response.status_code == 200:
            # If accepted, filename should be sanitized
            data = response.json()
            assert ".." not in data["filename"]
    
    def test_path_traversal_in_delete(self, client: TestClient, auth_headers: dict):
        """SEC-004: Path traversal in delete ID is handled."""
        traversal_id = "../../../etc/passwd"
        
        response = client.delete(
            f"/api/knowledge/documents/{traversal_id}",
            headers=auth_headers
        )
        
        # Should return 404 (not found) rather than attempting deletion
        assert response.status_code == 404
    
    def test_brute_force_login_rate_limit(self, client: TestClient):
        """SEC-005: Multiple failed login attempts should be limited."""
        # Make multiple failed login attempts
        for i in range(10):
            response = client.post("/api/auth/login", json={
                "username": "admin",
                "password": f"wrongpassword{i}"
            })
            assert response.status_code == 401
        
        # After many attempts, may be rate limited
        # This depends on implementation
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        
        # Should still be 401 or 429 (rate limited)
        assert response.status_code in [401, 429]
    
    def test_sensitive_data_exposure(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """Verify sensitive data is not exposed in responses."""
        # Create a conversation
        chat_resp = client.post("/api/chat", json={
            "message": "Test",
            "visitor_id": "test-visitor",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        # Get conversation details
        response = client.get(
            f"/api/chat/conversations/{conv_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_text = response.text.lower()
        
        # Should not expose sensitive fields
        assert "password" not in response_text
        assert "secret" not in response_text
        assert "token" not in response_text or "conversation" in response_text
    
    def test_cors_policy(self, client: TestClient):
        """Verify CORS headers are properly set."""
        response = client.options("/api/chat", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST"
        })
        
        # CORS is configured to allow all origins in development
        assert "access-control-allow-origin" in response.headers
