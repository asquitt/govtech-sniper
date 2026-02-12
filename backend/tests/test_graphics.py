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

    @pytest.mark.asyncio
    async def test_graphic_templates_and_generation(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        templates = await client.get("/api/v1/graphics/templates", headers=auth_headers)
        assert templates.status_code == 200
        payload = templates.json()
        template_types = {item["type"] for item in payload}
        assert {"timeline", "org_chart", "process_flow"}.issubset(template_types)

        generated = await client.post(
            "/api/v1/graphics/generate",
            headers=auth_headers,
            json={
                "content": "Phase 1 planning, phase 2 execution, phase 3 transition.",
                "template_type": "timeline",
                "title": "Delivery Timeline",
            },
        )
        assert generated.status_code == 200
        body = generated.json()
        assert body["template_type"] == "timeline"
        assert "mermaid_code" in body
        assert len(body["mermaid_code"]) > 0
