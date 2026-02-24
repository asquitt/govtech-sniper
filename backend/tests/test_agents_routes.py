"""
Integration tests for agents.py — /api/v1/agents/
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestAgentCatalog:
    """Tests for GET /api/v1/agents/catalog."""

    @pytest.mark.asyncio
    async def test_catalog_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/agents/catalog")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_catalog_returns_agents(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/agents/catalog", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 4
        ids = {a["id"] for a in data}
        assert ids == {"research", "capture_planning", "proposal_prep", "competitive_intel"}


class TestResearchAgent:
    """Tests for POST /api/v1/agents/research/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_research_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        response = await client.post(f"/api/v1/agents/research/{test_rfp.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_research_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/v1/agents/research/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_research_runs_successfully(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(f"/api/v1/agents/research/{test_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "research"
        assert data["rfp_id"] == test_rfp.id
        assert "summary" in data
        assert isinstance(data["actions_taken"], list)
        assert isinstance(data["artifacts"], dict)

    @pytest.mark.asyncio
    async def test_research_idor(
        self, client: AsyncClient, db_session: AsyncSession, test_rfp: RFP
    ):
        """User B cannot run research agent on User A's RFP."""
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
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(f"/api/v1/agents/research/{test_rfp.id}", headers=headers)
        assert response.status_code == 404


class TestCapturePlanningAgent:
    """Tests for POST /api/v1/agents/capture-planning/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_capture_planning_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        response = await client.post(f"/api/v1/agents/capture-planning/{test_rfp.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_capture_planning_creates_plan(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(
            f"/api/v1/agents/capture-planning/{test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "capture_planning"
        assert data["rfp_id"] == test_rfp.id
        assert "Created capture plan" in data["actions_taken"]
        assert "capture_plan_id" in data["artifacts"]

    @pytest.mark.asyncio
    async def test_capture_planning_idempotent(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Running twice reuses the existing plan."""
        await client.post(f"/api/v1/agents/capture-planning/{test_rfp.id}", headers=auth_headers)
        response = await client.post(
            f"/api/v1/agents/capture-planning/{test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "Validated existing capture plan" in data["actions_taken"]


class TestProposalPrepAgent:
    """Tests for POST /api/v1/agents/proposal-prep/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_proposal_prep_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        response = await client.post(f"/api/v1/agents/proposal-prep/{test_rfp.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_proposal_prep_creates_workspace(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(
            f"/api/v1/agents/proposal-prep/{test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "proposal_prep"
        assert "Created proposal workspace" in data["actions_taken"]
        assert data["artifacts"]["section_count"] >= 1

    @pytest.mark.asyncio
    async def test_proposal_prep_uses_existing_proposal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_proposal: Proposal,
    ):
        """If a proposal already exists, reuses it."""
        response = await client.post(
            f"/api/v1/agents/proposal-prep/{test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"]["proposal_id"] == test_proposal.id


class TestCompetitiveIntelAgent:
    """Tests for POST /api/v1/agents/competitive-intel/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_competitive_intel_requires_auth(self, client: AsyncClient, test_rfp: RFP):
        response = await client.post(f"/api/v1/agents/competitive-intel/{test_rfp.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_competitive_intel_runs_successfully(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(
            f"/api/v1/agents/competitive-intel/{test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "competitive_intel"
        assert data["rfp_id"] == test_rfp.id
        assert "competitors" in data["artifacts"]
        assert "award_patterns" in data["artifacts"]
