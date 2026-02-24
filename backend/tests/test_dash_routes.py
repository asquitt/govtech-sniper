"""
Integration tests for dash.py — /api/v1/dash/
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestDashSessions:
    """Tests for GET/POST /api/v1/dash/sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/dash/sessions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/dash/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_session(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Test Chat"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Chat"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_session_no_title(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        assert response.json()["title"] is None

    @pytest.mark.asyncio
    async def test_list_sessions_returns_created(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Session A"},
        )
        response = await client.get("/api/v1/dash/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestDashSessionMessages:
    """Tests for GET /api/v1/dash/sessions/{session_id}/messages."""

    @pytest.mark.asyncio
    async def test_messages_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/dash/sessions/1/messages")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_messages_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/dash/sessions/99999/messages", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_messages_empty(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Chat"},
        )
        session_id = create_resp.json()["id"]
        response = await client.get(
            f"/api/v1/dash/sessions/{session_id}/messages", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_messages_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User B cannot read User A's session messages."""
        create_resp = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Private"},
        )
        session_id = create_resp.json()["id"]

        user_b = User(
            email="other@example.com",
            hashed_password=hash_password("Pwd123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user_b)
        await db_session.commit()
        await db_session.refresh(user_b)
        tokens = create_token_pair(user_b.id, user_b.email, user_b.tier)
        headers_b = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(
            f"/api/v1/dash/sessions/{session_id}/messages", headers=headers_b
        )
        assert response.status_code == 404


class TestDeleteDashSession:
    """Tests for DELETE /api/v1/dash/sessions/{session_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/dash/sessions/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_session(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Deleteme"},
        )
        session_id = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/dash/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/dash/sessions/99999", headers=auth_headers)
        assert response.status_code == 404


class TestDashAsk:
    """Tests for POST /api/v1/dash/ask."""

    @pytest.mark.asyncio
    async def test_ask_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/dash/ask",
            json={"question": "What is an RFP?"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.routes.dash.generate_dash_response", new_callable=AsyncMock)
    async def test_ask_with_mock_ai(
        self,
        mock_gen: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        mock_gen.return_value = ("This is the answer.", [{"source": "test"}])
        response = await client.post(
            "/api/v1/dash/ask",
            headers=auth_headers,
            json={"question": "What is an RFP?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is the answer."
        assert len(data["citations"]) == 1

    @pytest.mark.asyncio
    @patch("app.api.routes.dash.generate_dash_response", new_callable=AsyncMock)
    async def test_ask_with_session(
        self,
        mock_gen: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Ask with session_id persists messages."""
        mock_gen.return_value = ("Answer with session.", [])
        create_resp = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "For ask"},
        )
        session_id = create_resp.json()["id"]

        response = await client.post(
            "/api/v1/dash/ask",
            headers=auth_headers,
            json={"question": "Tell me more", "session_id": session_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] is not None

        # Verify messages were persisted
        msgs = await client.get(
            f"/api/v1/dash/sessions/{session_id}/messages", headers=auth_headers
        )
        assert len(msgs.json()) == 2  # user + assistant


class TestDashChat:
    """Tests for POST /api/v1/dash/chat (SSE streaming)."""

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/dash/chat",
            json={"question": "Hello"},
        )
        assert response.status_code == 401
