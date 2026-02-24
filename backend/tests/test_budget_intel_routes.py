"""
Integration tests for budget_intel.py routes:
  - GET    /api/v1/budget-intel
  - POST   /api/v1/budget-intel
  - PATCH  /api/v1/budget-intel/{record_id}
  - DELETE /api/v1/budget-intel/{record_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget_intel import BudgetIntelligence
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    user = User(
        email="budget-second@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Budget Second",
        company_name="Other Co",
        tier="free",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_headers(second_user: User) -> dict:
    tokens = create_token_pair(second_user.id, second_user.email, second_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def test_budget(db_session: AsyncSession, test_user: User) -> BudgetIntelligence:
    record = BudgetIntelligence(
        user_id=test_user.id,
        title="FY2026 Budget Item",
        fiscal_year=2026,
        amount=1500000.0,
        notes="Initial allocation",
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# GET /api/v1/budget-intel
# ---------------------------------------------------------------------------


class TestListBudgetIntel:
    """GET /api/v1/budget-intel"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/budget-intel")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/budget-intel", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_records(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_budget: BudgetIntelligence,
    ):
        response = await client.get("/api/v1/budget-intel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "FY2026 Budget Item"
        assert data[0]["fiscal_year"] == 2026

    @pytest.mark.asyncio
    async def test_filter_by_rfp_id(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        test_user: User,
        test_rfp: RFP,
    ):
        record = BudgetIntelligence(
            user_id=test_user.id,
            rfp_id=test_rfp.id,
            title="RFP Budget",
        )
        db_session.add(record)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/budget-intel?rfp_id={test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rfp_id"] == test_rfp.id

    @pytest.mark.asyncio
    async def test_idor_isolation(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_budget: BudgetIntelligence,
    ):
        response = await client.get("/api/v1/budget-intel", headers=second_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# POST /api/v1/budget-intel
# ---------------------------------------------------------------------------


class TestCreateBudgetIntel:
    """POST /api/v1/budget-intel"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/budget-intel",
            json={"title": "Test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_record(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={
                "title": "New Budget Item",
                "fiscal_year": 2027,
                "amount": 2000000.0,
                "notes": "Planning phase",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Budget Item"
        assert data["fiscal_year"] == 2027
        assert data["amount"] == 2000000.0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_with_rfp(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={
                "title": "RFP Budget",
                "rfp_id": test_rfp.id,
            },
        )
        assert response.status_code == 200
        assert response.json()["rfp_id"] == test_rfp.id

    @pytest.mark.asyncio
    async def test_create_with_nonexistent_rfp(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={
                "title": "Bad RFP",
                "rfp_id": 999999,
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_with_other_users_rfp(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_rfp: RFP,
    ):
        response = await client.post(
            "/api/v1/budget-intel",
            headers=second_headers,
            json={
                "title": "IDOR Budget",
                "rfp_id": test_rfp.id,
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_missing_title(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/budget-intel",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/budget-intel/{record_id}
# ---------------------------------------------------------------------------


class TestUpdateBudgetIntel:
    """PATCH /api/v1/budget-intel/{record_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_budget: BudgetIntelligence):
        response = await client.patch(
            f"/api/v1/budget-intel/{test_budget.id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_record(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_budget: BudgetIntelligence,
    ):
        response = await client.patch(
            f"/api/v1/budget-intel/{test_budget.id}",
            headers=auth_headers,
            json={"title": "Updated Title", "amount": 2500000.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["amount"] == 2500000.0

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/budget-intel/999999",
            headers=auth_headers,
            json={"title": "Nope"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_update(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_budget: BudgetIntelligence,
    ):
        response = await client.patch(
            f"/api/v1/budget-intel/{test_budget.id}",
            headers=second_headers,
            json={"title": "Hacked"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/budget-intel/{record_id}
# ---------------------------------------------------------------------------


class TestDeleteBudgetIntel:
    """DELETE /api/v1/budget-intel/{record_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_budget: BudgetIntelligence):
        response = await client.delete(f"/api/v1/budget-intel/{test_budget.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_record(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_budget: BudgetIntelligence,
    ):
        response = await client.delete(
            f"/api/v1/budget-intel/{test_budget.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Budget record deleted"

        # Verify deleted
        get_resp = await client.get("/api/v1/budget-intel", headers=auth_headers)
        assert len(get_resp.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/budget-intel/999999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_delete(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_budget: BudgetIntelligence,
    ):
        response = await client.delete(
            f"/api/v1/budget-intel/{test_budget.id}", headers=second_headers
        )
        assert response.status_code == 404
