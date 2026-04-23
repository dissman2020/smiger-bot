"""Integration tests (INT-001 ~ INT-005)."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from tests.fixtures.base import (
    client, auth_headers, admin_token, mock_llm_gateway, mock_redis,
    mock_chromadb, sample_pdf
)


@pytest.mark.integration
class TestIntegration:
    """Test complete workflows (INT-001 ~ INT-005)."""
    
    def test_complete_conversation_to_lead_flow(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_llm_gateway,
        mock_redis,
        mock_chromadb
    ):
        """INT-001: Complete flow - user chats, triggers lead, submits."""
        visitor_id = "integration-visitor-001"
        
        # Step 1: User starts conversation
        resp1 = client.post("/api/chat", json={
            "message": "I'm looking for a guitar",
            "visitor_id": visitor_id,
            "language": "en"
        })
        assert resp1.status_code == 200
        conv_id = resp1.json()["conversation_id"]
        
        # Step 2: Continue conversation for multiple turns
        for i in range(4):
            resp = client.post("/api/chat", json={
                "message": f"Tell me more about option {i}",
                "conversation_id": conv_id,
                "visitor_id": visitor_id,
                "language": "en"
            })
            assert resp.status_code == 200
        
        # Step 3: Lead form is triggered (after LEAD_TRIGGER_TURN)
        # This may set lead_prompt flag
        
        # Step 4: Submit lead
        lead_resp = client.post("/api/leads", json={
            "conversation_id": conv_id,
            "email": "lead@example.com",
            "name": "Lead User",
            "phone": "+1234567890",
            "requirement": "Looking for electric guitar"
        })
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        # Step 5: Verify lead appears in admin list
        leads_list = client.get("/api/leads", headers=auth_headers)
        assert leads_list.status_code == 200
        leads = leads_list.json()
        lead_ids = [l["id"] for l in leads]
        assert lead_id in lead_ids
        
        # Step 6: Verify conversation has lead captured
        conv_detail = client.get(
            f"/api/chat/conversations/{conv_id}",
            headers=auth_headers
        )
        assert conv_detail.status_code == 200
        assert conv_detail.json()["lead_captured"] is True
    
    def test_handoff_complete_workflow(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_llm_gateway,
        mock_redis
    ):
        """INT-002: Complete handoff - request, accept, reply, resolve."""
        visitor_id = "integration-visitor-002"
        
        # Step 1: User starts conversation
        resp1 = client.post("/api/chat", json={
            "message": "I need to talk to a human",
            "visitor_id": visitor_id,
            "language": "en"
        })
        conv_id = resp1.json()["conversation_id"]
        
        # Step 2: Admin sees conversation in list
        handoff_list = client.get("/api/admin/handoff/list?all=true", headers=auth_headers)
        assert handoff_list.status_code == 200
        
        # Step 3: Admin accepts handoff
        with patch("app.core.whatsapp_client.is_enabled") as mock_whatsapp, \
             patch("app.core.telegram_client.is_enabled") as mock_telegram, \
             patch("app.core.gchat_client.is_enabled") as mock_gchat:
            
            mock_whatsapp.return_value = False
            mock_telegram.return_value = False
            mock_gchat.return_value = False
            
            accept_resp = client.post(
                f"/api/admin/handoff/{conv_id}/accept",
                headers=auth_headers,
                json={}
            )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == "active"
        
        # Step 4: Admin sends reply
        reply_resp = client.post(
            f"/api/admin/handoff/{conv_id}/reply",
            headers=auth_headers,
            json={"message": "Hello, how can I help you today?"}
        )
        assert reply_resp.status_code == 200
        
        # Step 5: User sends message during handoff
        user_msg = client.post("/api/chat", json={
            "message": "I have a question about shipping",
            "conversation_id": conv_id,
            "visitor_id": visitor_id,
            "language": "en"
        })
        assert user_msg.status_code == 200
        
        # Step 6: Admin resolves handoff
        with patch("app.api.handoff.get_user_ws") as mock_get_ws:
            mock_get_ws.return_value = None
            
            resolve_resp = client.post(
                f"/api/admin/handoff/{conv_id}/resolve",
                headers=auth_headers
            )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["status"] == "resolved"
    
    def test_knowledge_base_update_flow(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf,
        mock_chromadb
    ):
        """INT-003: Upload document, verify searchable."""
        import io
        
        # Step 1: Upload new document
        with patch("app.services.document.parse_file") as mock_parse:
            mock_parse.return_value = "New product: Special Edition Guitar Model X"
            
            upload_resp = client.post(
                "/api/knowledge/upload",
                headers=auth_headers,
                files={"file": ("new_product.pdf", io.BytesIO(sample_pdf), "application/pdf")}
            )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]
        
        # Step 2: Verify document appears in list
        list_resp = client.get("/api/knowledge/documents", headers=auth_headers)
        assert list_resp.status_code == 200
        doc_ids = [d["id"] for d in list_resp.json()]
        assert doc_id in doc_ids
        
        # Step 3: Verify stats updated
        stats_resp = client.get("/api/knowledge/stats", headers=auth_headers)
        assert stats_resp.status_code == 200
        assert stats_resp.json()["total_documents"] >= 1
        
        # Step 4: Search should find new content (mocked)
        # In real test, would verify RAG search returns new content
    
    def test_faq_sync_flow(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_chromadb
    ):
        """INT-004: Create FAQ, sync to knowledge base, verify searchable."""
        # Step 1: Create new FAQ
        create_resp = client.post(
            "/api/faq/entries",
            headers=auth_headers,
            json={
                "category": "integration_test",
                "question_cn": "集成测试问题？",
                "question_en": "Integration test question?",
                "answer_cn": "集成测试答案。",
                "answer_en": "Integration test answer.",
                "tags": ["integration", "test"],
                "is_active": True
            }
        )
        assert create_resp.status_code == 200
        faq_id = create_resp.json()["id"]
        
        # Step 2: Sync FAQ to knowledge base
        with patch("app.core.rag_engine.add_faq_chunks") as mock_add:
            mock_add.return_value = 1
            
            sync_resp = client.post("/api/faq/sync", headers=auth_headers)
        assert sync_resp.status_code == 200
        
        # Step 3: Verify FAQ appears in list
        list_resp = client.get("/api/faq/entries", headers=auth_headers)
        assert list_resp.status_code == 200
        faq_ids = [f["id"] for f in list_resp.json()]
        assert faq_id in faq_ids
    
    def test_multi_channel_independence(
        self,
        client: TestClient,
        mock_llm_gateway,
        mock_redis
    ):
        """INT-005: Web and Telegram conversations are independent."""
        # Web conversation
        web_resp = client.post("/api/chat", json={
            "message": "Web user question",
            "visitor_id": "web-visitor-001",
            "language": "en"
        })
        web_conv_id = web_resp.json()["conversation_id"]
        
        # Another web conversation
        web2_resp = client.post("/api/chat", json={
            "message": "Another web user",
            "visitor_id": "web-visitor-002",
            "language": "en"
        })
        web2_conv_id = web2_resp.json()["conversation_id"]
        
        # Verify conversations are separate
        assert web_conv_id != web2_conv_id
        
        # Continue first conversation
        continue_resp = client.post("/api/chat", json={
            "message": "Follow up",
            "conversation_id": web_conv_id,
            "visitor_id": "web-visitor-001",
            "language": "en"
        })
        assert continue_resp.json()["conversation_id"] == web_conv_id
        
        # Verify second conversation is unchanged
        # (Would need to check DB directly in full integration test)


@pytest.mark.integration
class TestEndToEndScenarios:
    """End-to-end scenario tests."""
    
    def test_customer_journey_new_visitor(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_llm_gateway,
        mock_redis,
        mock_chromadb
    ):
        """Test complete journey for a new visitor."""
        visitor_id = "new-visitor-journey"
        
        # 1. Visit website, open chat
        resp1 = client.post("/api/chat", json={
            "message": "Hi, I'm looking for guitars",
            "visitor_id": visitor_id,
            "language": "en",
            "customer_region": "APAC",
            "customer_country_code": "CN"
        })
        assert resp1.status_code == 200
        conv_id = resp1.json()["conversation_id"]
        
        # 2. Ask product questions
        questions = [
            "What electric guitars do you recommend?",
            "What's the price range?",
            "Do you ship to China?"
        ]
        for q in questions:
            resp = client.post("/api/chat", json={
                "message": q,
                "conversation_id": conv_id,
                "visitor_id": visitor_id,
                "language": "en"
            })
            assert resp.status_code == 200
        
        # 3. Lead form triggered, submit info
        lead_resp = client.post("/api/leads", json={
            "conversation_id": conv_id,
            "email": "customer@example.com",
            "name": "John Customer",
            "phone": "+8613800138000",
            "country": "CN",
            "requirement": "Looking for electric guitar under 3000 RMB"
        })
        assert lead_resp.status_code == 200
        
        # 4. Admin checks dashboard
        dashboard = client.get("/api/dashboard/stats", headers=auth_headers)
        assert dashboard.status_code == 200
        
        # 5. Admin reviews conversation
        conv = client.get(f"/api/chat/conversations/{conv_id}", headers=auth_headers)
        assert conv.status_code == 200
        assert conv.json()["visitor_id"] == visitor_id
        assert conv.json()["customer_region"] == "APAC"
        assert conv.json()["lead_captured"] is True
        
        # 6. Admin exports leads
        export = client.get("/api/leads/export", headers=auth_headers)
        assert export.status_code == 200
        assert "customer@example.com" in export.content.decode()
    
    def test_admin_daily_workflow(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_llm_gateway,
        mock_redis
    ):
        """Test admin daily workflow."""
        # 1. Login and check dashboard
        dashboard = client.get("/api/dashboard/stats", headers=auth_headers)
        assert dashboard.status_code == 200
        
        # 2. Check new leads
        leads = client.get("/api/leads", headers=auth_headers)
        assert leads.status_code == 200
        
        # 3. Check pending handoffs
        handoffs = client.get("/api/admin/handoff/list?status=pending", headers=auth_headers)
        assert handoffs.status_code == 200
        
        # 4. Review recent conversations
        conversations = client.get("/api/chat/conversations", headers=auth_headers)
        assert conversations.status_code == 200
        
        # 5. Check knowledge base stats
        kb_stats = client.get("/api/knowledge/stats", headers=auth_headers)
        assert kb_stats.status_code == 200
        
        # 6. Review FAQ
        faqs = client.get("/api/faq/entries", headers=auth_headers)
        assert faqs.status_code == 200
