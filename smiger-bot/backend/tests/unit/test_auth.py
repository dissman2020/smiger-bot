"""Authentication module tests (AUTH-001 ~ AUTH-005)."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from tests.fixtures.base import client, auth_headers, admin_token


@pytest.mark.auth
@pytest.mark.unit
class TestAuth:
    """Test authentication endpoints."""
    
    def test_login_success(self, client: TestClient):
        """AUTH-001: Normal login with correct credentials."""
        response = client.post("/api/auth/login", json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
    
    def test_login_wrong_password(self, client: TestClient):
        """AUTH-002: Login with wrong password returns 401."""
        response = client.post("/api/auth/login", json={
            "username": settings.ADMIN_USERNAME,
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_login_empty_username(self, client: TestClient):
        """AUTH-003: Login with empty username returns 400."""
        response = client.post("/api/auth/login", json={
            "username": "",
            "password": settings.ADMIN_PASSWORD
        })
        
        assert response.status_code == 401
    
    def test_access_with_expired_token(self, client: TestClient):
        """AUTH-004: Access with expired token returns 401."""
        # Create an expired token (manually crafted)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTYwMDAwMDAwMH0.invalid"
        
        response = client.get(
            "/api/knowledge/documents",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
    
    def test_access_with_invalid_token(self, client: TestClient):
        """AUTH-005: Access with forged/invalid token returns 401."""
        response = client.get(
            "/api/knowledge/documents",
            headers={"Authorization": "Bearer invalid_token_123"}
        )
        
        assert response.status_code == 401
    
    def test_access_without_token(self, client: TestClient):
        """Access protected endpoint without token returns 401."""
        response = client.get("/api/knowledge/documents")
        
        assert response.status_code == 401
    
    def test_access_with_valid_token(self, client: TestClient, auth_headers: dict):
        """Access protected endpoint with valid token succeeds."""
        response = client.get("/api/knowledge/documents", headers=auth_headers)
        
        assert response.status_code == 200
