"""
Integration tests for capture/fields.py:
  - GET    /capture/fields
  - POST   /capture/fields
  - PATCH  /capture/fields/{field_id}
  - DELETE /capture/fields/{field_id}
  - GET    /capture/plans/{plan_id}/fields
  - PUT    /capture/plans/{plan_id}/fields
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import (
    BidDecision,
    CaptureCustomField,
    CaptureFieldType,
    CapturePlan,
    CaptureStage,
)
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

PREFIX = "/api/v1/capture"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_field(db_session: AsyncSession, test_user: User) -> CaptureCustomField:
    """Create a custom field for the test user."""
    field = CaptureCustomField(
        user_id=test_user.id,
        name="Priority Level",
        field_type=CaptureFieldType.SELECT,
        options=["low", "medium", "high"],
        stage=CaptureStage.IDENTIFIED,
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)
    return field


@pytest_asyncio.fixture
async def test_plan(db_session: AsyncSession, test_user: User, test_rfp: RFP) -> CapturePlan:
    plan = CapturePlan(
        rfp_id=test_rfp.id,
        owner_id=test_user.id,
        stage=CaptureStage.IDENTIFIED,
        bid_decision=BidDecision.PENDING,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# List custom fields
# ---------------------------------------------------------------------------


class TestListCaptureFields:
    """Tests for GET /capture/fields."""

    @pytest.mark.asyncio
    async def test_list_fields_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/fields")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_fields_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{PREFIX}/fields", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_fields_returns_own(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_field: CaptureCustomField,
    ):
        response = await client.get(f"{PREFIX}/fields", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Priority Level"

    @pytest.mark.asyncio
    async def test_list_fields_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_field: CaptureCustomField,
    ):
        """Second user should not see the first user's fields."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(f"{PREFIX}/fields", headers=other_headers)
        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# Create custom field
# ---------------------------------------------------------------------------


class TestCreateCaptureField:
    """Tests for POST /capture/fields."""

    @pytest.mark.asyncio
    async def test_create_field_requires_auth(self, client: AsyncClient):
        response = await client.post(
            f"{PREFIX}/fields", json={"name": "Test", "field_type": "text"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_field_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/fields",
            headers=auth_headers,
            json={
                "name": "Budget Range",
                "field_type": "text",
                "is_required": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Budget Range"
        assert data["field_type"] == "text"
        assert data["is_required"] is True

    @pytest.mark.asyncio
    async def test_create_field_with_options(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/fields",
            headers=auth_headers,
            json={
                "name": "Status",
                "field_type": "select",
                "options": ["active", "inactive"],
                "stage": "qualified",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["options"] == ["active", "inactive"]
        assert data["stage"] == "qualified"


# ---------------------------------------------------------------------------
# Update custom field
# ---------------------------------------------------------------------------


class TestUpdateCaptureField:
    """Tests for PATCH /capture/fields/{field_id}."""

    @pytest.mark.asyncio
    async def test_update_field_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{PREFIX}/fields/1", json={"name": "x"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_field_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_field: CaptureCustomField,
    ):
        response = await client.patch(
            f"{PREFIX}/fields/{test_field.id}",
            headers=auth_headers,
            json={"name": "Updated Name", "is_required": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["is_required"] is True

    @pytest.mark.asyncio
    async def test_update_field_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{PREFIX}/fields/99999",
            headers=auth_headers,
            json={"name": "nope"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_field_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_field: CaptureCustomField,
    ):
        """Second user cannot update first user's field."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.patch(
            f"{PREFIX}/fields/{test_field.id}",
            headers=other_headers,
            json={"name": "hacked"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete custom field
# ---------------------------------------------------------------------------


class TestDeleteCaptureField:
    """Tests for DELETE /capture/fields/{field_id}."""

    @pytest.mark.asyncio
    async def test_delete_field_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{PREFIX}/fields/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_field_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_field: CaptureCustomField,
    ):
        response = await client.delete(f"{PREFIX}/fields/{test_field.id}", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify it's gone
        response = await client.get(f"{PREFIX}/fields", headers=auth_headers)
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_delete_field_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{PREFIX}/fields/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_field_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_field: CaptureCustomField,
    ):
        """Second user cannot delete first user's field."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.delete(f"{PREFIX}/fields/{test_field.id}", headers=other_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# List plan field values
# ---------------------------------------------------------------------------


class TestListPlanFields:
    """Tests for GET /capture/plans/{plan_id}/fields."""

    @pytest.mark.asyncio
    async def test_list_plan_fields_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/plans/1/fields")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_plan_fields_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
        test_field: CaptureCustomField,
    ):
        response = await client.get(f"{PREFIX}/plans/{test_plan.id}/fields", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["fields"]) == 1
        assert data["fields"][0]["field"]["name"] == "Priority Level"
        assert data["fields"][0]["value"] is None

    @pytest.mark.asyncio
    async def test_list_plan_fields_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{PREFIX}/plans/99999/fields", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_plan_fields_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_plan: CapturePlan,
    ):
        """Second user cannot view first user's plan fields."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(f"{PREFIX}/plans/{test_plan.id}/fields", headers=other_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update plan field values
# ---------------------------------------------------------------------------


class TestUpdatePlanFields:
    """Tests for PUT /capture/plans/{plan_id}/fields."""

    @pytest.mark.asyncio
    async def test_update_plan_fields_requires_auth(self, client: AsyncClient):
        response = await client.put(f"{PREFIX}/plans/1/fields", json=[])
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_plan_fields_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
        test_field: CaptureCustomField,
    ):
        response = await client.put(
            f"{PREFIX}/plans/{test_plan.id}/fields",
            headers=auth_headers,
            json=[{"field_id": test_field.id, "value": "high"}],
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["fields"]) == 1
        assert data["fields"][0]["value"] == "high"

    @pytest.mark.asyncio
    async def test_update_plan_fields_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.put(
            f"{PREFIX}/plans/99999/fields",
            headers=auth_headers,
            json=[],
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_plan_fields_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_plan: CapturePlan,
    ):
        """Second user cannot update first user's plan field values."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.put(
            f"{PREFIX}/plans/{test_plan.id}/fields",
            headers=other_headers,
            json=[],
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_plan_fields_unknown_field_ignored(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_plan: CapturePlan,
    ):
        """Field IDs not owned by the user are silently ignored."""
        response = await client.put(
            f"{PREFIX}/plans/{test_plan.id}/fields",
            headers=auth_headers,
            json=[{"field_id": 99999, "value": "something"}],
        )
        assert response.status_code == 200
        assert response.json()["fields"] == []
