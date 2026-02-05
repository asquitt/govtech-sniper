"""
RFP Sniper - Draft Tests
========================
Tests for proposal listing endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP
from app.models.user import User


class TestDraftProposals:
    @pytest.mark.asyncio
    async def test_list_proposals(self, client: AsyncClient, test_user: User, test_rfp: RFP):
        # Create proposal
        response = await client.post(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
            json={"rfp_id": test_rfp.id, "title": "Test Proposal"},
        )
        assert response.status_code == 200

        # List proposals
        response = await client.get(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Proposal"

    @pytest.mark.asyncio
    async def test_section_evidence_and_submission_packages(
        self,
        client: AsyncClient,
        test_user: User,
        test_rfp: RFP,
        test_document,
    ):
        # Create proposal
        response = await client.post(
            "/api/v1/draft/proposals",
            params={"user_id": test_user.id},
            json={"rfp_id": test_rfp.id, "title": "Evidence Proposal"},
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        # Create section
        response = await client.post(
            f"/api/v1/draft/proposals/{proposal_id}/sections",
            json={
                "title": "Technical Approach",
                "section_number": "1.1",
                "requirement_text": "Provide an approach to meet requirements.",
                "display_order": 0,
            },
        )
        assert response.status_code == 200
        section_id = response.json()["id"]

        # Update section
        response = await client.patch(
            f"/api/v1/draft/sections/{section_id}",
            params={"user_id": test_user.id},
            json={"final_content": "We propose an agile delivery model."},
        )
        assert response.status_code == 200
        assert response.json()["final_content"] == "We propose an agile delivery model."

        # Add evidence
        response = await client.post(
            f"/api/v1/draft/sections/{section_id}/evidence",
            params={"user_id": test_user.id},
            json={
                "document_id": test_document.id,
                "citation": "Capability Statement, page 2",
            },
        )
        assert response.status_code == 200
        evidence_id = response.json()["id"]

        # List evidence
        response = await client.get(
            f"/api/v1/draft/sections/{section_id}/evidence",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        evidence = response.json()
        assert len(evidence) == 1
        assert evidence[0]["id"] == evidence_id

        # Create submission package
        response = await client.post(
            f"/api/v1/draft/proposals/{proposal_id}/submission-packages",
            params={"user_id": test_user.id},
            json={"title": "Final Package"},
        )
        assert response.status_code == 200
        package_id = response.json()["id"]

        # Update submission package
        response = await client.patch(
            f"/api/v1/draft/submission-packages/{package_id}",
            params={"user_id": test_user.id},
            json={"notes": "Ready for export"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Ready for export"

        # Submit package
        response = await client.post(
            f"/api/v1/draft/submission-packages/{package_id}/submit",
            params={"user_id": test_user.id},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"
