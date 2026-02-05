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
