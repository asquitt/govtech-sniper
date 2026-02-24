"""
Integration tests for capture/plans.py:
  - POST   /capture/plans
  - GET    /capture/plans
  - GET    /capture/plans/{rfp_id}
  - GET    /capture/plans/{plan_id}/match-insight
  - PATCH  /capture/plans/{plan_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import BidDecision, CapturePlan, CaptureStage
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

PREFIX = "/api/v1/capture"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    """Create a second user and return (user, auth_headers)."""
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
    tokens = create_token_pair(user.id, user.email, user.tier)
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_plan(db_session: AsyncSession, test_user: User, test_rfp: RFP) -> CapturePlan:
    """Create a capture plan for the test user's RFP."""
    plan = CapturePlan(
        rfp_id=test_rfp.id,
        owner_id=test_user.id,
        stage=CaptureStage.IDENTIFIED,
        bid_decision=BidDecision.PENDING,
        win_probability=50,
        notes="Test plan notes",
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# Create capture plan
# ---------------------------------------------------------------------------


class TestCreateCapturePlan:
    """Tests for POST /capture/plans."""

    @pytest.mark.asyncio
    async def test_create_plan_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{PREFIX}/plans", json={"rfp_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_plan_success(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(
            f"{PREFIX}/plans",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "stage": "identified",
                "bid_decision": "pending",
                "win_probability": 40,
                "notes": "New capture plan",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == test_rfp.id
        assert data["stage"] == "identified"
        assert data["win_probability"] == 40

    @pytest.mark.asyncio
    async def test_create_plan_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/plans",
            headers=auth_headers,
            json={"rfp_id": 99999},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_plan_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        """A second user cannot create a plan for another user's RFP."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.post(
            f"{PREFIX}/plans",
            headers=other_headers,
            json={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_plan_duplicate(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
        test_rfp: RFP,
    ):
        """Cannot create two capture plans for the same RFP."""
        response = await client.post(
            f"{PREFIX}/plans",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# List capture plans
# ---------------------------------------------------------------------------


class TestListCapturePlans:
    """Tests for GET /capture/plans."""

    @pytest.mark.asyncio
    async def test_list_plans_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/plans")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_plans_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{PREFIX}/plans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["plans"] == []

    @pytest.mark.asyncio
    async def test_list_plans_returns_own_plans(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
    ):
        response = await client.get(f"{PREFIX}/plans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["plans"][0]["id"] == test_plan.id

    @pytest.mark.asyncio
    async def test_list_plans_with_include_rfp(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
        test_rfp: RFP,
    ):
        response = await client.get(
            f"{PREFIX}/plans",
            headers=auth_headers,
            params={"include_rfp": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        plan = data["plans"][0]
        assert plan["rfp_title"] == test_rfp.title
        assert plan["rfp_agency"] == test_rfp.agency

    @pytest.mark.asyncio
    async def test_list_plans_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_plan: CapturePlan,
    ):
        """Second user should not see the first user's plans."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(f"{PREFIX}/plans", headers=other_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# Get capture plan by RFP ID
# ---------------------------------------------------------------------------


class TestGetCapturePlan:
    """Tests for GET /capture/plans/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_get_plan_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/plans/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_plan_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
        test_rfp: RFP,
    ):
        response = await client.get(f"{PREFIX}/plans/{test_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == test_rfp.id
        assert data["id"] == test_plan.id

    @pytest.mark.asyncio
    async def test_get_plan_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{PREFIX}/plans/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_plan_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_plan: CapturePlan,
        test_rfp: RFP,
    ):
        """Second user cannot read first user's capture plan."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(f"{PREFIX}/plans/{test_rfp.id}", headers=other_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update capture plan
# ---------------------------------------------------------------------------


class TestUpdateCapturePlan:
    """Tests for PATCH /capture/plans/{plan_id}."""

    @pytest.mark.asyncio
    async def test_update_plan_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{PREFIX}/plans/1", json={"notes": "x"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_plan_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
    ):
        response = await client.patch(
            f"{PREFIX}/plans/{test_plan.id}",
            headers=auth_headers,
            json={"stage": "qualified", "notes": "Updated notes"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "qualified"
        assert data["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_plan_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{PREFIX}/plans/99999",
            headers=auth_headers,
            json={"notes": "irrelevant"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_plan_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_plan: CapturePlan,
    ):
        """Second user cannot update first user's capture plan."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.patch(
            f"{PREFIX}/plans/{test_plan.id}",
            headers=other_headers,
            json={"notes": "hacked"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Match insight
# ---------------------------------------------------------------------------


class TestMatchInsight:
    """Tests for GET /capture/plans/{plan_id}/match-insight."""

    @pytest.mark.asyncio
    async def test_match_insight_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/plans/1/match-insight")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_match_insight_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
    ):
        response = await client.get(
            f"{PREFIX}/plans/{test_plan.id}/match-insight",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == test_plan.id
        assert "summary" in data
        assert isinstance(data["factors"], list)

    @pytest.mark.asyncio
    async def test_match_insight_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{PREFIX}/plans/99999/match-insight", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_match_insight_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_plan: CapturePlan,
    ):
        """Second user cannot view first user's match insight."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(
            f"{PREFIX}/plans/{test_plan.id}/match-insight",
            headers=other_headers,
        )
        assert response.status_code == 404
