"""
Integration tests for onboarding.py — /onboarding/ progress, steps, dismiss, metrics
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestGetProgress:
    """GET /api/v1/onboarding/progress"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/onboarding/progress")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_initial_progress(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        assert data["total_steps"] == 6
        assert data["completed_count"] >= 1  # create_account always completed
        assert data["is_dismissed"] is False

    @pytest.mark.asyncio
    async def test_auto_detects_rfp_step(
        self, client: AsyncClient, auth_headers: dict, test_user: User, test_rfp
    ):
        response = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        upload_step = next(s for s in data["steps"] if s["id"] == "upload_rfp")
        assert upload_step["completed"] is True

    @pytest.mark.asyncio
    async def test_auto_detects_proposal_step(
        self, client: AsyncClient, auth_headers: dict, test_user: User, test_proposal
    ):
        response = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        data = response.json()
        proposal_step = next(s for s in data["steps"] if s["id"] == "create_proposal")
        assert proposal_step["completed"] is True

    @pytest.mark.asyncio
    async def test_auto_detects_document_step(
        self, client: AsyncClient, auth_headers: dict, test_user: User, test_document
    ):
        response = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        data = response.json()
        doc_step = next(s for s in data["steps"] if s["id"] == "upload_documents")
        assert doc_step["completed"] is True


class TestMarkStepComplete:
    """POST /api/v1/onboarding/steps/{step_id}/complete"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/onboarding/steps/export_proposal/complete")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_valid_step(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/onboarding/steps/export_proposal/complete", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["step_id"] == "export_proposal"

    @pytest.mark.asyncio
    async def test_mark_invalid_step(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/onboarding/steps/nonexistent_step/complete", headers=auth_headers
        )
        assert response.status_code == 200
        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_step_persists(self, client: AsyncClient, auth_headers: dict, test_user: User):
        await client.post("/api/v1/onboarding/steps/export_proposal/complete", headers=auth_headers)
        progress = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        export_step = next(s for s in progress.json()["steps"] if s["id"] == "export_proposal")
        assert export_step["completed"] is True


class TestDismissOnboarding:
    """POST /api/v1/onboarding/dismiss"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/onboarding/dismiss")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dismiss(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post("/api/v1/onboarding/dismiss", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "dismissed"

        progress = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        assert progress.json()["is_dismissed"] is True


class TestActivationMetrics:
    """GET /api/v1/onboarding/activation-metrics"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/onboarding/activation-metrics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_enterprise_tier(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        # test_user is "professional" tier
        response = await client.get("/api/v1/onboarding/activation-metrics", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_enterprise_can_access(self, client: AsyncClient, db_session: AsyncSession):
        enterprise_user = User(
            email="enterprise@example.com",
            hashed_password=hash_password("EnterprisePass123!"),
            full_name="Enterprise User",
            company_name="Big Corp",
            tier="enterprise",
            is_active=True,
            is_verified=True,
        )
        db_session.add(enterprise_user)
        await db_session.commit()
        await db_session.refresh(enterprise_user)

        tokens = create_token_pair(enterprise_user.id, enterprise_user.email, enterprise_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/onboarding/activation-metrics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "fully_activated" in data
        assert "step_completion_rates" in data
