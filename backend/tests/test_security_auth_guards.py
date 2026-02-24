"""
Security Regression Tests - Auth Guards
=========================================
Verifies that all protected endpoints require authentication
and enforce ownership checks (IDOR prevention).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second test user for IDOR testing."""
    user = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPassword123!"),
        full_name="Other User",
        company_name="Other Company",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_auth_headers(other_user: User) -> dict:
    """Auth headers for the second user."""
    tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


class TestAnalyzeAuthGuards:
    """All /analyze endpoints must require authentication."""

    @pytest.mark.asyncio
    async def test_trigger_analysis_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/analyze/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_analysis_status_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/analyze/1/status/fake-task-id")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_compliance_matrix_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/analyze/1/matrix")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_compliance_gaps_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/analyze/1/gaps")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_add_compliance_requirement_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/analyze/1/matrix",
            json={
                "text": "Test requirement",
                "importance": "mandatory",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_compliance_requirement_requires_auth(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/analyze/1/matrix/REQ-001",
            json={
                "text": "Updated",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_compliance_requirement_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/analyze/1/matrix/REQ-001")
        assert resp.status_code == 401


class TestRFPAuthGuards:
    """RFP CRUD endpoints must require auth and enforce ownership."""

    @pytest.mark.asyncio
    async def test_get_rfp_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/rfps/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_rfp_requires_auth(self, client: AsyncClient):
        resp = await client.patch("/api/v1/rfps/1", json={"title": "Hacked"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_rfp_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/v1/rfps/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_rfp_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, other_auth_headers: dict
    ):
        """User 2 should NOT be able to read User 1's RFP."""
        resp = await client.get(f"/api/v1/rfps/{test_rfp.id}", headers=other_auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_rfp_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, other_auth_headers: dict
    ):
        """User 2 should NOT be able to update User 1's RFP."""
        resp = await client.patch(
            f"/api/v1/rfps/{test_rfp.id}",
            headers=other_auth_headers,
            json={"title": "Hacked Title"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_rfp_idor_blocked(
        self, client: AsyncClient, test_rfp: RFP, other_auth_headers: dict
    ):
        """User 2 should NOT be able to delete User 1's RFP."""
        resp = await client.delete(f"/api/v1/rfps/{test_rfp.id}", headers=other_auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_rfp_owner_succeeds(
        self, client: AsyncClient, test_rfp: RFP, auth_headers: dict
    ):
        """Owner CAN read their own RFP."""
        resp = await client.get(f"/api/v1/rfps/{test_rfp.id}", headers=auth_headers)
        assert resp.status_code == 200


class TestDraftAuthGuards:
    """Draft/proposal endpoints must require auth."""

    @pytest.mark.asyncio
    async def test_get_proposal_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/draft/proposals/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_section_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/draft/proposals/1/sections",
            json={
                "title": "Test Section",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_from_matrix_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/draft/proposals/1/generate-from-matrix")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_generation_status_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/draft/fake-task-id/status")
        assert resp.status_code == 401


class TestIngestAuthGuards:
    """Ingest endpoints must require auth."""

    @pytest.mark.asyncio
    async def test_ingest_status_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/ingest/sam/status/fake-task-id")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_quick_search_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/ingest/sam/quick-search?keywords=test")
        assert resp.status_code == 401


class TestCaptureAuthGuards:
    """Capture/bid-decision endpoints must require auth."""

    @pytest.mark.asyncio
    async def test_list_scorecards_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/capture/bid-decision/scorecards/1")
        assert resp.status_code in (401, 404)

    @pytest.mark.asyncio
    async def test_bid_summary_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/capture/bid-decision/scorecards/1/summary")
        assert resp.status_code in (401, 404)


class TestTemplateAuthGuards:
    """Template seed endpoint must require auth."""

    @pytest.mark.asyncio
    async def test_seed_templates_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/templates/seed-system-templates")
        assert resp.status_code == 401


class TestWebSocketAuthGuards:
    """WebSocket HTTP fallback must require auth."""

    @pytest.mark.asyncio
    async def test_task_status_http_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/ws/task/fake-id/status")
        assert resp.status_code == 401
