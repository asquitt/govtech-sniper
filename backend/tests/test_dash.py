"""
RFP Sniper - Dash Tests
=======================
Tests for Dash session and ask endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.rfp import RFP
from app.models.knowledge_base import KnowledgeBaseDocument


class TestDash:
    @pytest.mark.asyncio
    async def test_dash_sessions_and_messages(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        # Create session
        response = await client.post(
            "/api/v1/dash/sessions",
            headers=auth_headers,
            json={"title": "Discovery"},
        )
        assert response.status_code == 200
        session_id = response.json()["id"]

        # List sessions
        response = await client.get("/api/v1/dash/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Add message
        response = await client.post(
            f"/api/v1/dash/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"role": "user", "content": "Summarize this opportunity."},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "user"

    @pytest.mark.asyncio
    async def test_dash_ask(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_rfp: RFP,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.post(
            "/api/v1/dash/ask",
            headers=auth_headers,
            json={"question": "What is the deadline?", "rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert test_rfp.title in data["answer"]
        assert "Deadline" in data["answer"]
        assert isinstance(data["citations"], list)
        assert any(citation.get("type") == "document" for citation in data["citations"])
