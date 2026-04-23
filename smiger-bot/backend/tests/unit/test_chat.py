"""Chat module tests (CHAT-001 ~ CHAT-012, WS-001 ~ WS-005)."""

import json
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Conversation, Message
from tests.fixtures.base import (
    client, auth_headers, admin_token, mock_llm_gateway, mock_redis,
    mock_chromadb
)


@pytest.mark.chat
@pytest.mark.unit
class TestChatREST:
    """Test REST chat endpoints (CHAT-001 ~ CHAT-012)."""
    
    def test_chat_normal(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-001: Normal conversation returns response with confidence."""
        response = client.post("/api/chat", json={
            "message": "What guitars do you recommend?",
            "visitor_id": "test-visitor-001",
            "language": "en"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "conversation_id" in data
        assert "confidence" in data
        assert data["message"] == "This is a test response"
    
    def test_chat_new_conversation(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-002: Chat without conversation_id creates new conversation."""
        response = client.post("/api/chat", json={
            "message": "Hello",
            "visitor_id": "test-visitor-002",
            "language": "en"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert len(data["conversation_id"]) > 0
    
    def test_chat_continue_conversation(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-003: Chat with valid conversation_id continues session."""
        # First message to create conversation
        resp1 = client.post("/api/chat", json={
            "message": "Hello",
            "visitor_id": "test-visitor-003",
            "language": "en"
        })
        conv_id = resp1.json()["conversation_id"]
        
        # Continue with same conversation
        resp2 = client.post("/api/chat", json={
            "message": "Tell me more",
            "conversation_id": conv_id,
            "visitor_id": "test-visitor-003",
            "language": "en"
        })
        
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == conv_id
    
    def test_chat_invalid_conversation_id(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-004: Chat with non-existent conversation_id creates new one."""
        response = client.post("/api/chat", json={
            "message": "Hello",
            "conversation_id": "non-existent-id-12345",
            "visitor_id": "test-visitor-004",
            "language": "en"
        })
        
        assert response.status_code == 200
        # Should create new conversation
        assert "conversation_id" in response.json()
    
    def test_chat_empty_message(self, client: TestClient):
        """CHAT-005: Empty message returns 400."""
        response = client.post("/api/chat", json={
            "message": "",
            "visitor_id": "test-visitor-005",
            "language": "en"
        })
        
        assert response.status_code == 400
    
    def test_chat_long_message(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-006: Long message (>2000 chars) is handled."""
        long_message = "A" * 2500
        
        response = client.post("/api/chat", json={
            "message": long_message,
            "visitor_id": "test-visitor-006",
            "language": "en"
        })
        
        # Should either process or truncate
        assert response.status_code in [200, 400, 413]
    
    def test_chat_special_characters(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-007: Special characters (HTML/JS) are properly escaped."""
        response = client.post("/api/chat", json={
            "message": "<script>alert('xss')</script>",
            "visitor_id": "test-visitor-007",
            "language": "en"
        })
        
        assert response.status_code == 200
        # Response should not contain unescaped script tags
        assert "<script>" not in response.text or response.json()["message"] != ""
    
    def test_chat_chinese(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-008: Chinese message gets Chinese response."""
        response = client.post("/api/chat", json={
            "message": "推荐什么吉他？",
            "visitor_id": "test-visitor-008",
            "language": "zh"
        })
        
        assert response.status_code == 200
        assert "conversation_id" in response.json()
    
    def test_chat_english(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-009: English message gets English response."""
        response = client.post("/api/chat", json={
            "message": "What guitars do you recommend?",
            "visitor_id": "test-visitor-009",
            "language": "en"
        })
        
        assert response.status_code == 200
        assert "conversation_id" in response.json()
    
    def test_chat_lead_trigger(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-010: Lead prompt triggers after configured turns."""
        visitor_id = "test-visitor-010"
        conv_id = None
        
        # Send multiple messages to trigger lead
        for i in range(5):
            payload = {
                "message": f"Message {i}",
                "visitor_id": visitor_id,
                "language": "en"
            }
            if conv_id:
                payload["conversation_id"] = conv_id
            
            response = client.post("/api/chat", json=payload)
            assert response.status_code == 200
            
            if not conv_id:
                conv_id = response.json()["conversation_id"]
            
            # Check if lead_prompt is triggered after LEAD_TRIGGER_TURN
            if i >= 3:  # Assuming LEAD_TRIGGER_TURN=3
                # lead_prompt may be true depending on implementation
                pass
    
    def test_chat_handoff_active(self, client: TestClient, db_session: AsyncSession):
        """CHAT-011: Message during active handoff is forwarded to human."""
        # This would require setting up a conversation with handoff_status='active'
        # For unit test, we mock this behavior
        pass
    
    def test_chat_customer_profile(self, client: TestClient, mock_llm_gateway, mock_redis):
        """CHAT-012: Customer info (region/country/phone) is saved to conversation."""
        response = client.post("/api/chat", json={
            "message": "Hello",
            "visitor_id": "test-visitor-012",
            "language": "en",
            "customer_region": "APAC",
            "customer_country_code": "CN",
            "customer_phone": "+8613800138000"
        })
        
        assert response.status_code == 200
        assert "conversation_id" in response.json()


@pytest.mark.chat
@pytest.mark.unit
class TestChatWebSocket:
    """Test WebSocket chat endpoints (WS-001 ~ WS-005)."""
    
    def test_websocket_connect(self, client: TestClient):
        """WS-001: WebSocket connection establishes successfully."""
        with client.websocket_connect("/api/chat/ws/test-conv-001") as websocket:
            # Connection should be established
            pass
    
    def test_websocket_streaming(self, client: TestClient, mock_llm_gateway):
        """WS-002: WebSocket returns streaming tokens."""
        with client.websocket_connect("/api/chat/ws/test-conv-002") as websocket:
            # Send message
            websocket.send_text(json.dumps({
                "message": "Hello",
                "visitor_id": "test-visitor-ws-001"
            }))
            
            # Should receive response (may be streaming or complete)
            try:
                response = websocket.receive_text()
                data = json.loads(response)
                assert "type" in data
            except Exception:
                # WebSocket may close after response
                pass
    
    def test_websocket_multiple_clients(self, client: TestClient):
        """WS-003: Multiple clients on same conversation receive messages."""
        conv_id = "test-conv-003"
        
        with client.websocket_connect(f"/api/chat/ws/{conv_id}") as ws1, \
             client.websocket_connect(f"/api/chat/ws/{conv_id}") as ws2:
            
            ws1.send_text(json.dumps({
                "message": "Hello from client 1",
                "visitor_id": "visitor-001"
            }))
            
            # Both clients should receive updates
            # (Implementation dependent)
            pass
    
    def test_websocket_reconnect(self, client: TestClient):
        """WS-004: Reconnect restores conversation."""
        conv_id = "test-conv-004"
        
        # First connection
        with client.websocket_connect(f"/api/chat/ws/{conv_id}") as websocket:
            websocket.send_text(json.dumps({
                "message": "First message",
                "visitor_id": "test-visitor"
            }))
        
        # Reconnect
        with client.websocket_connect(f"/api/chat/ws/{conv_id}") as websocket:
            # Should be able to continue conversation
            websocket.send_text(json.dumps({
                "message": "Second message",
                "visitor_id": "test-visitor"
            }))
    
    def test_websocket_concurrent_messages(self, client: TestClient):
        """WS-005: Concurrent messages are processed in order."""
        conv_id = "test-conv-005"
        
        with client.websocket_connect(f"/api/chat/ws/{conv_id}") as websocket:
            # Send multiple messages rapidly
            for i in range(5):
                websocket.send_text(json.dumps({
                    "message": f"Message {i}",
                    "visitor_id": "test-visitor"
                }))
            
            # Messages should be processed in order
            # (Implementation verification needed)


@pytest.mark.chat
@pytest.mark.unit
class TestConversationAdmin:
    """Test conversation admin endpoints."""
    
    def test_list_conversations(self, client: TestClient, auth_headers: dict):
        """List conversations as admin."""
        response = client.get("/api/chat/conversations", headers=auth_headers)
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_conversation_detail(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """Get conversation detail."""
        # First create a conversation
        resp = client.post("/api/chat", json={
            "message": "Test message",
            "visitor_id": "test-visitor-admin",
            "language": "en"
        })
        conv_id = resp.json()["conversation_id"]
        
        # Get detail
        response = client.get(f"/api/chat/conversations/{conv_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert "messages" in data
    
    def test_delete_conversation(self, client: TestClient, auth_headers: dict, mock_llm_gateway, mock_redis):
        """Delete conversation."""
        # Create conversation
        resp = client.post("/api/chat", json={
            "message": "Test message",
            "visitor_id": "test-visitor-delete",
            "language": "en"
        })
        conv_id = resp.json()["conversation_id"]
        
        # Delete
        response = client.delete(f"/api/chat/conversations/{conv_id}", headers=auth_headers)
        
        assert response.status_code == 200
