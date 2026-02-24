"""
Integration tests for graphics.py — /api/v1/graphics/
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestListGraphicsRequests:
    """Tests for GET /api/v1/graphics."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/graphics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/graphics", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_filtered_by_proposal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        # Create a request first
        await client.post(
            "/api/v1/graphics",
            headers=auth_headers,
            json={"proposal_id": test_proposal.id, "title": "Architecture Diagram"},
        )
        response = await client.get(
            f"/api/v1/graphics?proposal_id={test_proposal.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Architecture Diagram"


class TestCreateGraphicsRequest:
    """Tests for POST /api/v1/graphics."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/graphics",
            json={"proposal_id": 1, "title": "Test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_request(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        response = await client.post(
            "/api/v1/graphics",
            headers=auth_headers,
            json={
                "proposal_id": test_proposal.id,
                "title": "Network Topology",
                "description": "Show zero-trust architecture",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Network Topology"
        assert data["status"] == "requested"
        assert data["proposal_id"] == test_proposal.id

    @pytest.mark.asyncio
    async def test_create_proposal_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/graphics",
            headers=auth_headers,
            json={"proposal_id": 99999, "title": "Ghost"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """User B cannot create graphics request for User A's proposal."""
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

        response = await client.post(
            "/api/v1/graphics",
            headers=headers_b,
            json={"proposal_id": test_proposal.id, "title": "Unauthorized"},
        )
        assert response.status_code == 404


class TestUpdateGraphicsRequest:
    """Tests for PATCH /api/v1/graphics/{request_id}."""

    @pytest.mark.asyncio
    async def test_update_request(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        create_resp = await client.post(
            "/api/v1/graphics",
            headers=auth_headers,
            json={"proposal_id": test_proposal.id, "title": "Original"},
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/graphics/{rid}",
            headers=auth_headers,
            json={"title": "Updated Title", "status": "in_progress"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
        assert response.json()["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/graphics/99999",
            headers=auth_headers,
            json={"title": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteGraphicsRequest:
    """Tests for DELETE /api/v1/graphics/{request_id}."""

    @pytest.mark.asyncio
    async def test_delete_request(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        create_resp = await client.post(
            "/api/v1/graphics",
            headers=auth_headers,
            json={"proposal_id": test_proposal.id, "title": "To Delete"},
        )
        rid = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/graphics/{rid}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/graphics/99999", headers=auth_headers)
        assert response.status_code == 404


class TestListTemplates:
    """Tests for GET /api/v1/graphics/templates."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/graphics/templates")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/graphics/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "type" in data[0]
            assert "label" in data[0]


class TestGenerateGraphic:
    """Tests for POST /api/v1/graphics/generate."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/graphics/generate",
            json={"content": "test", "template_type": "flowchart"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.routes.graphics.generate_graphic", new_callable=AsyncMock)
    async def test_generate_success(
        self, mock_gen: AsyncMock, client: AsyncClient, auth_headers: dict
    ):
        mock_gen.return_value = {
            "mermaid_code": "graph TD; A-->B;",
            "template_type": "flowchart",
            "title": "Test",
        }
        response = await client.post(
            "/api/v1/graphics/generate",
            headers=auth_headers,
            json={"content": "Zero trust architecture", "template_type": "flowchart"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "mermaid_code" in data
        assert data["template_type"] == "flowchart"


class TestStoreGraphicAsset:
    """Tests for POST /api/v1/graphics/{request_id}/asset."""

    @pytest.mark.asyncio
    async def test_store_asset(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        create_resp = await client.post(
            "/api/v1/graphics",
            headers=auth_headers,
            json={"proposal_id": test_proposal.id, "title": "Asset Test"},
        )
        rid = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/graphics/{rid}/asset?asset_url=https://example.com/img.png",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["asset_url"] == "https://example.com/img.png"
        assert data["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_store_asset_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/graphics/99999/asset?asset_url=https://example.com/x.png",
            headers=auth_headers,
        )
        assert response.status_code == 404
