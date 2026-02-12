"""
RFP Sniper - Word Add-in Tests
==============================
Tests for Word add-in session endpoints.
"""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.models.proposal import ProposalSection
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

    @pytest.mark.asyncio
    async def test_word_addin_section_sync_rewrite_and_compliance(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        db_session,
    ):
        previous_mock_ai = settings.mock_ai
        settings.mock_ai = True
        try:
            response = await client.post(
                "/api/v1/draft/proposals",
                headers=auth_headers,
                json={
                    "rfp_id": test_rfp.id,
                    "title": "Word Addin Section Sync Proposal",
                },
            )
            assert response.status_code == 200
            proposal_id = response.json()["id"]

            section = ProposalSection(
                proposal_id=proposal_id,
                title="Technical Approach",
                section_number="1.0",
                requirement_text="Address all cybersecurity controls and compliance requirements.",
                final_content="Initial section content for Word synchronization checks.",
                display_order=1,
            )
            db_session.add(section)
            await db_session.commit()
            await db_session.refresh(section)

            pull_response = await client.post(
                f"/api/v1/word-addin/sections/{section.id}/pull",
                headers=auth_headers,
            )
            assert pull_response.status_code == 200
            assert pull_response.json()["title"] == "Technical Approach"

            push_response = await client.post(
                f"/api/v1/word-addin/sections/{section.id}/push",
                headers=auth_headers,
                json={"content": "Updated section content pushed from Word."},
            )
            assert push_response.status_code == 200
            assert push_response.json()["message"] == "Section updated"

            compliance_response = await client.post(
                f"/api/v1/word-addin/sections/{section.id}/compliance-check",
                headers=auth_headers,
            )
            assert compliance_response.status_code == 200
            compliance_payload = compliance_response.json()
            assert compliance_payload["section_id"] == section.id
            assert "score" in compliance_payload

            rewrite_response = await client.post(
                "/api/v1/word-addin/ai/rewrite",
                headers=auth_headers,
                json={
                    "content": "This proposal text needs improvement.",
                    "mode": "improve",
                },
            )
            assert rewrite_response.status_code == 200
            rewrite_payload = rewrite_response.json()
            assert rewrite_payload["rewritten"].startswith("[improve]")
        finally:
            settings.mock_ai = previous_mock_ai
