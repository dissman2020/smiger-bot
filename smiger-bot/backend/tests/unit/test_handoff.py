"""Handoff module tests (HAND-001 ~ HAND-013)."""

import json
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Conversation
from tests.fixtures.base import (
    client, auth_headers, admin_token, mock_llm_gateway, mock_redis
)


@pytest.mark.handoff
@pytest.mark.unit
class TestHandoff:
    """Test handoff endpoints (HAND-001 ~ HAND-013)."""
    
    def test_handoff_count(self, client: TestClient, auth_headers: dict, db_session: AsyncSession):
        """HAND-001: Get pending/active handoff counts."""
        response = client.get("/api/admin/handoff/count", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "pending" in data
        assert "active" in data
        assert isinstance(data["pending"], int)
        assert isinstance(data["active"], int)
    
    def test_handoff_list(self, client: TestClient, auth_headers: dict):
        """HAND-002: Get handoff conversation list."""
        response = client.get("/api/admin/handoff/list", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_handoff_list_filter_status(self, client: TestClient, auth_headers: dict, db_session: AsyncSession):
        """HAND-003: Filter handoff list by status."""
        # Create conversations with different statuses
        # This would require direct DB manipulation in integration tests
        
        response = client.get("/api/admin/handoff/list?status=pending", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # All items should have handoff_status = pending
        for item in data:
            assert item["handoff_status"] == "pending"
    
    def test_handoff_list_filter_region(self, client: TestClient, auth_headers: dict):
        """HAND-004: Filter handoff list by region."""
        response = client.get("/api/admin/handoff/list?region=APAC", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item["customer_region"] == "APAC"
    
    def test_handoff_get_messages(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-005: Get conversation messages for handoff."""
        # Create a conversation first
        chat_resp = client.post("/api/chat", json={
            "message": "I need human help",
            "visitor_id": "handoff-visitor-001",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        response = client.get(f"/api/admin/handoff/{conv_id}/messages", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_handoff_accept(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-006: Accept pending handoff."""
        # Create conversation and set to pending
        chat_resp = client.post("/api/chat", json={
            "message": "Need help",
            "visitor_id": "handoff-visitor-002",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = False
            mock_telegram.return_value = False
            mock_gchat.return_value = False
            
            response = client.post(
                f"/api/admin/handoff/{conv_id}/accept",
                headers=auth_headers,
                json={}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
    
    def test_handoff_accept_already_active(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-007: Accept already active handoff."""
        # Create and accept once
        chat_resp = client.post("/api/chat", json={
            "message": "Help",
            "visitor_id": "handoff-visitor-003",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = False
            mock_telegram.return_value = False
            mock_gchat.return_value = False
            
            # First accept
            client.post(f"/api/admin/handoff/{conv_id}/accept", headers=auth_headers, json={})
            
            # Second accept (should still work)
            response = client.post(
                f"/api/admin/handoff/{conv_id}/accept",
                headers=auth_headers,
                json={}
            )
        
        assert response.status_code == 200
    
    def test_handoff_reply(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-008: Send reply to user in handoff."""
        # Create conversation
        chat_resp = client.post("/api/chat", json={
            "message": "Help needed",
            "visitor_id": "handoff-visitor-004",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        # Accept handoff first
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = False
            mock_telegram.return_value = False
            mock_gchat.return_value = False
            
            client.post(f"/api/admin/handoff/{conv_id}/accept", headers=auth_headers, json={})
        
        # Send reply
        response = client.post(
            f"/api/admin/handoff/{conv_id}/reply",
            headers=auth_headers,
            json={"message": "Hello, I'm here to help you!"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert "message_id" in data
    
    def test_handoff_reply_websocket_push(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-009: Reply triggers WebSocket push to user."""
        # Create conversation with WebSocket
        chat_resp = client.post("/api/chat", json={
            "message": "Help",
            "visitor_id": "handoff-visitor-005",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        # Accept handoff
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = False
            mock_telegram.return_value = False
            mock_gchat.return_value = False
            
            client.post(f"/api/admin/handoff/{conv_id}/accept", headers=auth_headers, json={})
        
        # Mock WebSocket
        with patch("app.api.handoff.get_user_ws") as mock_get_ws:
            ws_mock = AsyncMock()
            mock_get_ws.return_value = ws_mock
            
            # Send reply
            response = client.post(
                f"/api/admin/handoff/{conv_id}/reply",
                headers=auth_headers,
                json={"message": "WebSocket test message"}
            )
            
            assert response.status_code == 200
            # Verify WebSocket was called
            ws_mock.send_text.assert_called_once()
    
    def test_handoff_resolve(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-010: Resolve handoff conversation."""
        # Create and accept handoff
        chat_resp = client.post("/api/chat", json={
            "message": "Help",
            "visitor_id": "handoff-visitor-006",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = False
            mock_telegram.return_value = False
            mock_gchat.return_value = False
            
            client.post(f"/api/admin/handoff/{conv_id}/accept", headers=auth_headers, json={})
        
        # Resolve
        with patch("app.api.handoff.get_user_ws") as mock_get_ws:
            mock_get_ws.return_value = None
            
            response = client.post(
                f"/api/admin/handoff/{conv_id}/resolve",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
    
    def test_handoff_telegram_notification(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-011: Accept handoff sends Telegram notification."""
        chat_resp = client.post("/api/chat", json={
            "message": "Help",
            "visitor_id": "handoff-visitor-007",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.telegram_client.notify_handoff") as mock_notify, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = False
            mock_telegram.return_value = True
            mock_gchat.return_value = False
            mock_notify.return_value = AsyncMock()
            
            response = client.post(
                f"/api/admin/handoff/{conv_id}/accept",
                headers=auth_headers,
                json={}
            )
        
        assert response.status_code == 200
        mock_notify.assert_called_once()
    
    def test_handoff_whatsapp_notification(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-012: Accept handoff sends WhatsApp notification."""
        chat_resp = client.post("/api/chat", json={
            "message": "Help",
            "visitor_id": "handoff-visitor-008",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.whatsapp_client.notify_handoff") as mock_notify, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = True
            mock_telegram.return_value = False
            mock_gchat.return_value = False
            mock_notify.return_value = AsyncMock()
            
            response = client.post(
                f"/api/admin/handoff/{conv_id}/accept",
                headers=auth_headers,
                json={}
            )
        
        assert response.status_code == 200
        mock_notify.assert_called_once()
    
    def test_handoff_update_channel(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """HAND-013: Update handoff Telegram channel."""
        chat_resp = client.post("/api/chat", json={
            "message": "Help",
            "visitor_id": "handoff-visitor-009",
            "language": "en"
        })
        conv_id = chat_resp.json()["conversation_id"]
        
        with patch("app.core.telegram_accounts.list_enabled_telegram_accounts") as mock_list:
            mock_list.return_value = [{"name": "support_bot", "enabled": True}]
            
            response = client.post(
                f"/api/admin/handoff/{conv_id}/channel",
                headers=auth_headers,
                json={"telegram_account_name": "support_bot"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["telegram_account_name"] == "support_bot"
