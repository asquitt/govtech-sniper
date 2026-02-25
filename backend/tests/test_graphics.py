"""
RFP Sniper - Proposal Graphics Tests
====================================
Integration tests for proposal graphics request endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import RFP

# ---- Auth guards ----


class TestGraphicsAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/graphics")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/graphics",
            json={"proposal_id": 1, "title": "Test"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        resp = await client.patch("/api/v1/graphics/1", json={"title": "X"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/graphics/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_templates_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/graphics/templates")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/graphics/generate",
            json={"content": "test", "template_type": "timeline", "title": "T"},
        )
        assert resp.status_code == 401


# ---- CRUD happy path ----


class TestGraphicsCRUD:
    @pytest.mark.asyncio
    async def test_full_crud_cycle(
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


# ---- Not-found cases ----


class TestGraphicsNotFound:
    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.patch(
            "/api/v1/graphics/99999",
            headers=auth_headers,
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete("/api/v1/graphics/99999", headers=auth_headers)
        assert resp.status_code == 404


# ---- Templates and generation ----


class TestGraphicsTemplatesAndGeneration:
    @pytest.mark.asyncio
    async def test_templates_list(self, client: AsyncClient, auth_headers: dict):
        templates = await client.get("/api/v1/graphics/templates", headers=auth_headers)
        assert templates.status_code == 200
        payload = templates.json()
        template_types = {item["type"] for item in payload}
        assert {"timeline", "org_chart", "process_flow"}.issubset(template_types)

    @pytest.mark.asyncio
    async def test_generate_timeline(self, client: AsyncClient, auth_headers: dict):
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

    @pytest.mark.asyncio
    async def test_generate_org_chart(self, client: AsyncClient, auth_headers: dict):
        generated = await client.post(
            "/api/v1/graphics/generate",
            headers=auth_headers,
            json={
                "content": "PM leads dev team and QA team.",
                "template_type": "org_chart",
                "title": "Org Chart",
            },
        )
        assert generated.status_code == 200
        body = generated.json()
        assert body["template_type"] == "org_chart"
        assert "mermaid_code" in body

    @pytest.mark.asyncio
    async def test_generate_process_flow(self, client: AsyncClient, auth_headers: dict):
        generated = await client.post(
            "/api/v1/graphics/generate",
            headers=auth_headers,
            json={
                "content": "Receive requirements, analyze, design, implement, test, deploy.",
                "template_type": "process_flow",
                "title": "Dev Process",
            },
        )
        assert generated.status_code == 200
        body = generated.json()
        assert body["template_type"] == "process_flow"
        assert "mermaid_code" in body


# ---- List edge cases ----


class TestGraphicsList:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/graphics", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []
