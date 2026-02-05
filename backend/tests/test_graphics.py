"""
RFP Sniper - Proposal Graphics Tests
====================================
Tests for proposal graphics request endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP


class TestProposalGraphics:
    @pytest.mark.asyncio
    async def test_graphics_requests_crud(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
    ):
        # Create proposal
        response = await client.post(
            "/api/v1/draft/proposals",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id, "title": "Graphics Proposal"},
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        # Create graphics request
        response = await client.post(
            "/api/v1/graphics",
            headers=auth_headers,
            json={
                "proposal_id": proposal_id,
                "title": "Infographic",
                "description": "Create a win themes diagram.",
            },
        )
        assert response.status_code == 200
        request_id = response.json()["id"]
        assert response.json()["status"] == "requested"

        # List requests
        response = await client.get(
            "/api/v1/graphics",
            headers=auth_headers,
            params={"proposal_id": proposal_id},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Update request
        response = await client.patch(
            f"/api/v1/graphics/{request_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "delivered"

        # Delete request
        response = await client.delete(
            f"/api/v1/graphics/{request_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
