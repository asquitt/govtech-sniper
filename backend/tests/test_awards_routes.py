"""
Integration tests for awards.py routes:
  - GET    /api/v1/awards
  - POST   /api/v1/awards
  - PATCH  /api/v1/awards/{award_id}
  - DELETE /api/v1/awards/{award_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.award import AwardRecord
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    user = User(
        email="award-second@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Award Second",
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
async def test_award(db_session: AsyncSession, test_user: User) -> AwardRecord:
    award = AwardRecord(
        user_id=test_user.id,
        awardee_name="Test Corp",
        agency="DoD",
        award_amount=500000,
    )
    db_session.add(award)
    await db_session.commit()
    await db_session.refresh(award)
    return award


# ---------------------------------------------------------------------------
# GET /api/v1/awards
# ---------------------------------------------------------------------------


class TestListAwards:
    """GET /api/v1/awards"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/awards")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/awards", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_awards(
        self, client: AsyncClient, auth_headers: dict, test_award: AwardRecord
    ):
        response = await client.get("/api/v1/awards", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["awardee_name"] == "Test Corp"

    @pytest.mark.asyncio
    async def test_filter_by_rfp_id(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        test_user: User,
        test_rfp: RFP,
    ):
        award = AwardRecord(
            user_id=test_user.id,
            rfp_id=test_rfp.id,
            awardee_name="RFP Linked Corp",
        )
        db_session.add(award)
        await db_session.commit()

        response = await client.get(f"/api/v1/awards?rfp_id={test_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rfp_id"] == test_rfp.id

    @pytest.mark.asyncio
    async def test_idor_isolation(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_award: AwardRecord,
    ):
        response = await client.get("/api/v1/awards", headers=second_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# POST /api/v1/awards
# ---------------------------------------------------------------------------


class TestCreateAward:
    """POST /api/v1/awards"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/awards",
            json={"awardee_name": "Test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_award(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={
                "awardee_name": "New Corp",
                "agency": "NASA",
                "award_amount": 1000000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["awardee_name"] == "New Corp"
        assert data["agency"] == "NASA"
        assert data["award_amount"] == 1000000
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_with_rfp(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={
                "awardee_name": "RFP Corp",
                "rfp_id": test_rfp.id,
            },
        )
        assert response.status_code == 200
        assert response.json()["rfp_id"] == test_rfp.id

    @pytest.mark.asyncio
    async def test_create_with_nonexistent_rfp(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={
                "awardee_name": "Bad Corp",
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
        """Cannot link award to another user's RFP."""
        response = await client.post(
            "/api/v1/awards",
            headers=second_headers,
            json={
                "awardee_name": "IDOR Corp",
                "rfp_id": test_rfp.id,
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_missing_awardee(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/awards",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/awards/{award_id}
# ---------------------------------------------------------------------------


class TestUpdateAward:
    """PATCH /api/v1/awards/{award_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_award: AwardRecord):
        response = await client.patch(
            f"/api/v1/awards/{test_award.id}",
            json={"agency": "NSA"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_award(
        self, client: AsyncClient, auth_headers: dict, test_award: AwardRecord
    ):
        response = await client.patch(
            f"/api/v1/awards/{test_award.id}",
            headers=auth_headers,
            json={"agency": "NSA", "award_amount": 750000},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agency"] == "NSA"
        assert data["award_amount"] == 750000

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/awards/999999",
            headers=auth_headers,
            json={"agency": "Updated"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_update(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_award: AwardRecord,
    ):
        response = await client.patch(
            f"/api/v1/awards/{test_award.id}",
            headers=second_headers,
            json={"agency": "Hacked"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/awards/{award_id}
# ---------------------------------------------------------------------------


class TestDeleteAward:
    """DELETE /api/v1/awards/{award_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_award: AwardRecord):
        response = await client.delete(f"/api/v1/awards/{test_award.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_award(
        self, client: AsyncClient, auth_headers: dict, test_award: AwardRecord
    ):
        response = await client.delete(f"/api/v1/awards/{test_award.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Award deleted"

        # Verify deleted
        get_resp = await client.get("/api/v1/awards", headers=auth_headers)
        assert len(get_resp.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/awards/999999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_delete(
        self,
        client: AsyncClient,
        second_headers: dict,
        test_award: AwardRecord,
    ):
        response = await client.delete(f"/api/v1/awards/{test_award.id}", headers=second_headers)
        assert response.status_code == 404
