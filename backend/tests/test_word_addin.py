"""
RFP Sniper - Word Add-in Tests
==============================
Tests for Word add-in session endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP


class TestWordAddin:
    @pytest.mark.asyncio
    async def test_word_addin_sessions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        # Create proposal
        response = await client.post(
            "/api/v1/draft/proposals",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "title": "Test Proposal",
            },
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        # Create session
        response = await client.post(
            "/api/v1/word-addin/sessions",
            headers=auth_headers,
            json={"proposal_id": proposal_id, "document_name": "Draft.docx"},
        )
        assert response.status_code == 200
        session_id = response.json()["id"]

        # List sessions
        response = await client.get(
            "/api/v1/word-addin/sessions",
            headers=auth_headers,
            params={"proposal_id": proposal_id},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Create event
        response = await client.post(
            f"/api/v1/word-addin/sessions/{session_id}/events",
            headers=auth_headers,
            json={"event_type": "sync", "payload": {"sections": 3}},
        )
        assert response.status_code == 200

        # List events
        response = await client.get(
            f"/api/v1/word-addin/sessions/{session_id}/events",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
