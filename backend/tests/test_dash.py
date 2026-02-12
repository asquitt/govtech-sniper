"""
RFP Sniper - Dash Tests
=======================
Tests for Dash session and ask endpoints.
"""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.rfp import RFP
from app.models.user import User


class TestDash:
    @pytest.mark.asyncio
    async def test_dash_sessions_and_messages(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
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

        # Add message via /ask with session_id (messages are created through ask)
        response = await client.post(
            "/api/v1/dash/ask",
            headers=auth_headers,
            json={
                "question": "Summarize this opportunity.",
                "session_id": session_id,
                "rfp_id": test_rfp.id,
            },
        )
        assert response.status_code == 200
        assert response.json()["message_id"] is not None

        # Get messages from session
        response = await client.get(
            f"/api/v1/dash/sessions/{session_id}/messages",
            headers=auth_headers,
        )
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_dash_ask(
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
            # Mock response includes the question text
            assert "What is the deadline?" in data["answer"]
            assert isinstance(data["citations"], list)
            assert any(citation.get("type") == "document" for citation in data["citations"])

            # Competitive intel intent
            response = await client.post(
                "/api/v1/awards",
                headers=auth_headers,
                json={
                    "rfp_id": test_rfp.id,
                    "awardee_name": "Test Winner",
                    "award_amount": 100000,
                },
            )
            assert response.status_code == 200

            response = await client.post(
                "/api/v1/dash/ask",
                headers=auth_headers,
                json={"question": "Who are the competitors?", "rfp_id": test_rfp.id},
            )
            assert response.status_code == 200
            data = response.json()
            # Mock response includes the question text
            assert "Who are the competitors?" in data["answer"]
        finally:
            settings.mock_ai = previous_mock_ai
