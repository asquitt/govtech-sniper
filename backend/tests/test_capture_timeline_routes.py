"""
Integration tests for capture_timeline.py — /api/v1/capture/timeline/
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CapturePlan, CaptureStage
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def test_capture_plan(
    db_session: AsyncSession, test_user: User, test_rfp: RFP
) -> CapturePlan:
    plan = CapturePlan(
        rfp_id=test_rfp.id,
        owner_id=test_user.id,
        stage=CaptureStage.QUALIFIED,
        win_probability=60,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


class TestListActivities:
    """Tests for GET /api/v1/capture/timeline/{plan_id}/activities."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/capture/timeline/1/activities")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_plan_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/capture/timeline/99999/activities", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict, test_capture_plan: CapturePlan
    ):
        response = await client.get(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []


class TestCreateActivity:
    """Tests for POST /api/v1/capture/timeline/{plan_id}/activities."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/capture/timeline/1/activities",
            json={"title": "Kickoff Meeting"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_activity(
        self, client: AsyncClient, auth_headers: dict, test_capture_plan: CapturePlan
    ):
        response = await client.post(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities",
            headers=auth_headers,
            json={"title": "Kickoff Meeting", "is_milestone": True, "sort_order": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Kickoff Meeting"
        assert data["is_milestone"] is True
        assert data["capture_plan_id"] == test_capture_plan.id

    @pytest.mark.asyncio
    async def test_create_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_capture_plan: CapturePlan,
    ):
        """User B cannot create activity on User A's plan."""
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

        response = await client.post(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities",
            headers=headers,
            json={"title": "Unauthorized"},
        )
        assert response.status_code == 404


class TestUpdateActivity:
    """Tests for PATCH /api/v1/capture/timeline/{plan_id}/activities/{activity_id}."""

    @pytest.mark.asyncio
    async def test_update_activity(
        self, client: AsyncClient, auth_headers: dict, test_capture_plan: CapturePlan
    ):
        # Create first
        create_resp = await client.post(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities",
            headers=auth_headers,
            json={"title": "Draft Review"},
        )
        activity_id = create_resp.json()["id"]

        # Update
        response = await client.patch(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities/{activity_id}",
            headers=auth_headers,
            json={"title": "Final Review", "status": "in_progress"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Final Review"

    @pytest.mark.asyncio
    async def test_update_not_found(
        self, client: AsyncClient, auth_headers: dict, test_capture_plan: CapturePlan
    ):
        response = await client.patch(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities/99999",
            headers=auth_headers,
            json={"title": "Ghost"},
        )
        assert response.status_code == 404


class TestDeleteActivity:
    """Tests for DELETE /api/v1/capture/timeline/{plan_id}/activities/{activity_id}."""

    @pytest.mark.asyncio
    async def test_delete_activity(
        self, client: AsyncClient, auth_headers: dict, test_capture_plan: CapturePlan
    ):
        create_resp = await client.post(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities",
            headers=auth_headers,
            json={"title": "To Delete"},
        )
        activity_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities/{activity_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Activity deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, client: AsyncClient, auth_headers: dict, test_capture_plan: CapturePlan
    ):
        response = await client.delete(
            f"/api/v1/capture/timeline/{test_capture_plan.id}/activities/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestTimelineOverview:
    """Tests for GET /api/v1/capture/timeline/overview."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/capture/timeline/overview")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_overview_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/capture/timeline/overview", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_overview_with_plan(
        self, client: AsyncClient, auth_headers: dict, test_capture_plan: CapturePlan
    ):
        response = await client.get("/api/v1/capture/timeline/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["plan_id"] == test_capture_plan.id
