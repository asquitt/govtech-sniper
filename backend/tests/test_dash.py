"""
RFP Sniper - Dash Tests
=======================
Integration tests for Dash session and ask endpoints.
"""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.rfp import RFP
from app.models.user import User

# ---- Auth guards ----


class TestDashAuth:
    @pytest.mark.asyncio
    async def test_list_sessions_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dash/sessions")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_session_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/dash/sessions", json={"title": "No Auth"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_messages_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/dash/sessions/1/messages")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_session_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/dash/sessions/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ask_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/dash/ask", json={"question": "Hello?"})
        assert resp.status_code == 401


# ---- Session CRUD ----


class TestDashSessions:
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/dash/sessions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_and_list_session(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Research Chat"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Research Chat"
        assert "id" in data

        list_resp = await client.get("/api/v1/dash/sessions", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

    @pytest.mark.asyncio
    async def test_create_session_without_title(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] is None

    @pytest.mark.asyncio
    async def test_delete_session(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "To Delete"},
        )
        session_id = create.json()["id"]

        resp = await client.delete(f"/api/v1/dash/sessions/{session_id}", headers=auth_headers)
        assert resp.status_code == 200

        list_resp = await client.get("/api/v1/dash/sessions", headers=auth_headers)
        assert len(list_resp.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete("/api/v1/dash/sessions/99999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_messages_session_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/dash/sessions/99999/messages", headers=auth_headers)
        assert resp.status_code == 404


# ---- Ask endpoint ----


class TestDashAsk:
    @pytest.mark.asyncio
    async def test_ask_without_session(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Ask without session_id still works (no messages persisted)."""
        resp = await client.post(
            "/api/v1/dash/ask",
            headers=auth_headers,
            json={"question": "Quick question", "rfp_id": test_rfp.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert data["message_id"] is None  # No session = no persisted message

    @pytest.mark.asyncio
    async def test_ask_with_session_persists_messages(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        # Create session
        session_resp = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Discovery"},
        )
        session_id = session_resp.json()["id"]

        # Ask with session
        resp = await client.post(
            "/api/v1/dash/ask",
            headers=auth_headers,
            json={
                "question": "Summarize this opportunity.",
                "session_id": session_id,
                "rfp_id": test_rfp.id,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["message_id"] is not None

        # Verify messages persisted
        msgs = await client.get(
            f"/api/v1/dash/sessions/{session_id}/messages",
            headers=auth_headers,
        )
        assert msgs.status_code == 200
        messages = msgs.json()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_ask_with_mock_ai_and_citations(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_rfp: RFP,
        test_document: KnowledgeBaseDocument,
    ):
        previous_mock_ai = settings.mock_ai
        settings.mock_ai = True
        try:
            response = await client.post(
                "/api/v1/dash/ask",
                headers=auth_headers,
                json={"question": "What is the deadline?", "rfp_id": test_rfp.id},
            )
            assert response.status_code == 200
            data = response.json()
            assert "What is the deadline?" in data["answer"]
            assert isinstance(data["citations"], list)
            assert any(c.get("type") == "document" for c in data["citations"])
        finally:
            settings.mock_ai = previous_mock_ai

    @pytest.mark.asyncio
    async def test_ask_competitive_intel_intent(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_rfp: RFP,
        test_document: KnowledgeBaseDocument,
    ):
        previous_mock_ai = settings.mock_ai
        settings.mock_ai = True
        try:
            # Create award for competitive context
            await client.post(
                "/api/v1/awards",
                headers=auth_headers,
                json={
                    "rfp_id": test_rfp.id,
                    "awardee_name": "Test Winner",
                    "award_amount": 100000,
                },
            )

            response = await client.post(
                "/api/v1/dash/ask",
                headers=auth_headers,
                json={"question": "Who are the competitors?", "rfp_id": test_rfp.id},
            )
            assert response.status_code == 200
            assert "Who are the competitors?" in response.json()["answer"]
        finally:
            settings.mock_ai = previous_mock_ai
