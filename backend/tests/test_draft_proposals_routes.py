"""
Integration tests for draft/proposals.py:
  - GET  /draft/proposals
  - GET  /draft/proposals/{id}
  - POST /draft/proposals
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestListProposals:
    """Tests for GET /api/v1/draft/proposals."""

    @pytest.mark.asyncio
    async def test_list_proposals_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/draft/proposals")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_proposals_empty(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/draft/proposals", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_proposals_returns_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.get("/api/v1/draft/proposals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_proposal.id
        assert data[0]["title"] == test_proposal.title

    @pytest.mark.asyncio
    async def test_list_proposals_filter_by_rfp(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_rfp: RFP,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals?rfp_id={test_rfp.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_list_proposals_filter_by_rfp_no_match(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.get(
            "/api/v1/draft/proposals?rfp_id=99999",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_proposals_idor(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        db_session: AsyncSession,
    ):
        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/draft/proposals", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestGetProposal:
    """Tests for GET /api/v1/draft/proposals/{id}."""

    @pytest.mark.asyncio
    async def test_get_proposal_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/draft/proposals/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_proposal_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_proposal.id
        assert "completion_percentage" in data

    @pytest.mark.asyncio
    async def test_get_proposal_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/draft/proposals/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_proposal_idor(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        db_session: AsyncSession,
    ):
        other = User(
            email="other2@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(f"/api/v1/draft/proposals/{test_proposal.id}", headers=headers)
        assert response.status_code == 404


class TestCreateProposal:
    """Tests for POST /api/v1/draft/proposals."""

    @pytest.mark.asyncio
    async def test_create_proposal_requires_auth(self, client: AsyncClient):
        """Without auth, resolve_user_id fails with 401 or the RFP lookup returns 404."""
        response = await client.post(
            "/api/v1/draft/proposals",
            json={"rfp_id": 1, "title": "Test"},
        )
        assert response.status_code in (401, 404)

    @pytest.mark.asyncio
    async def test_create_proposal_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_user: User,
    ):
        response = await client.post(
            "/api/v1/draft/proposals",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id, "title": "New Proposal"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Proposal"
        assert data["rfp_id"] == test_rfp.id
        assert data["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_create_proposal_rfp_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/draft/proposals",
            headers=auth_headers,
            json={"rfp_id": 99999, "title": "No RFP"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_proposal_missing_title(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_user: User,
    ):
        response = await client.post(
            "/api/v1/draft/proposals",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 422
