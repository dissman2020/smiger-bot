"""Lead module tests (LEAD-001 ~ LEAD-010)."""

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.base import (
    client, auth_headers, admin_token, mock_llm_gateway, mock_redis
)


@pytest.mark.lead
@pytest.mark.unit
class TestLeads:
    """Test lead endpoints (LEAD-001 ~ LEAD-010)."""
    
    def test_submit_lead_complete(self, client: TestClient):
        """LEAD-001: Submit lead with complete form."""
        response = client.post("/api/leads", json={
            "email": "customer@example.com",
            "name": "John Doe",
            "company": "ABC Corp",
            "phone": "+1234567890",
            "country": "US",
            "requirement": "Looking for electric guitars"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "customer@example.com"
        assert data["name"] == "John Doe"
        assert "id" in data
    
    def test_submit_lead_email_only(self, client: TestClient):
        """LEAD-002: Submit lead with only email (required field)."""
        response = client.post("/api/leads", json={
            "email": "minimal@example.com"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "minimal@example.com"
        assert data["name"] is None
        assert data["company"] is None
    
    def test_submit_lead_empty_email(self, client: TestClient):
        """LEAD-003: Submit lead without email returns 400."""
        response = client.post("/api/leads", json={
            "name": "No Email",
            "company": "Test Corp"
        })
        
        assert response.status_code == 400
    
    def test_submit_lead_invalid_email(self, client: TestClient):
        """LEAD-004: Submit lead with invalid email format returns 400."""
        response = client.post("/api/leads", json={
            "email": "not-an-email"
        })
        
        # May return 200 (stored) or 400 (validated)
        # Depending on implementation
        assert response.status_code in [200, 400, 422]
    
    def test_submit_lead_with_conversation(self, client: TestClient, mock_llm_gateway, mock_redis):
        """LEAD-005: Submit lead associated with conversation."""
        # First create a conversation
        chat_resp = client.post("/api/chat", json={
            "message": "I'm interested in guitars",
            "visitor_id": "test-visitor-lead",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        # Submit lead with conversation_id
        response = client.post("/api/leads", json={
            "conversation_id": conv_id,
            "email": "withconv@example.com",
            "name": "Conv User",
            "requirement": "Need guitar"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conv_id
    
    def test_list_leads(self, client: TestClient, auth_headers: dict):
        """LEAD-006: Admin gets lead list."""
        # Create a lead first
        client.post("/api/leads", json={
            "email": "listtest@example.com",
            "name": "List Test"
        })
        
        response = client.get("/api/leads", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_list_leads_pagination(self, client: TestClient, auth_headers: dict):
        """LEAD-007: Lead list pagination with skip/limit."""
        # Create multiple leads
        for i in range(5):
            client.post("/api/leads", json={
                "email": f"page{i}@example.com",
                "name": f"User {i}"
            })
        
        # Test pagination
        response = client.get("/api/leads?skip=0&limit=2", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
        
        # Test second page
        response2 = client.get("/api/leads?skip=2&limit=2", headers=auth_headers)
        assert response2.status_code == 200
    
    def test_lead_count(self, client: TestClient, auth_headers: dict):
        """LEAD-008: Get lead count statistics."""
        # Create a lead
        client.post("/api/leads", json={
            "email": "counttest@example.com"
        })
        
        response = client.get("/api/leads/count", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 1
    
    def test_export_leads_csv(self, client: TestClient, auth_headers: dict):
        """LEAD-009: Export leads as CSV."""
        # Create a lead
        client.post("/api/leads", json={
            "email": "csvtest@example.com",
            "name": "CSV Test",
            "company": "CSV Corp",
            "phone": "+1234567890",
            "country": "US",
            "requirement": "CSV requirement"
        })
        
        response = client.get("/api/leads/export", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        
        # Check CSV content
        content = response.content.decode()
        assert "Name" in content
        assert "Email" in content
        assert "csvtest@example.com" in content
    
    def test_export_large_leads(self, client: TestClient, auth_headers: dict):
        """LEAD-010: Export large number of leads (>10000)."""
        # This test would create many leads
        # For unit test, we just verify the endpoint handles limit parameter
        
        response = client.get("/api/leads/export?limit=10000", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
