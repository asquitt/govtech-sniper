"""
Integration tests for capture/intelligence.py:
  - GET    /capture/competitors?rfp_id=
  - POST   /capture/competitors
  - PATCH  /capture/competitors/{competitor_id}
  - DELETE /capture/competitors/{competitor_id}
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureCompetitor
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
async def test_competitor(
    db_session: AsyncSession, test_user: User, test_rfp: RFP
) -> CaptureCompetitor:
    comp = CaptureCompetitor(
        rfp_id=test_rfp.id,
        user_id=test_user.id,
        name="Acme Corp",
        incumbent=True,
        strengths="Established presence",
        weaknesses="High pricing",
        notes="Main competitor",
    )
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)
    return comp


# ---------------------------------------------------------------------------
# List competitors
# ---------------------------------------------------------------------------


class TestListCompetitors:
    """Tests for GET /capture/competitors?rfp_id=."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/competitors", params={"rfp_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.get(
            f"{PREFIX}/competitors",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_own_competitors(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_competitor: CaptureCompetitor,
    ):
        response = await client.get(
            f"{PREFIX}/competitors",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Acme Corp"
        assert data[0]["incumbent"] is True

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
        test_competitor: CaptureCompetitor,
    ):
        """Second user cannot see first user's competitors."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(
            f"{PREFIX}/competitors",
            headers=other_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_missing_rfp_id(self, client: AsyncClient, auth_headers: dict):
        """Missing required rfp_id query param returns 422."""
        response = await client.get(f"{PREFIX}/competitors", headers=auth_headers)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Create competitor
# ---------------------------------------------------------------------------


class TestCreateCompetitor:
    """Tests for POST /capture/competitors."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(
            f"{PREFIX}/competitors",
            json={"rfp_id": 1, "name": "BadCorp"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.post(
            f"{PREFIX}/competitors",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "name": "NewCo",
                "incumbent": False,
                "strengths": "Fast delivery",
                "weaknesses": "No past performance",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewCo"
        assert data["incumbent"] is False
        assert data["rfp_id"] == test_rfp.id

    @pytest.mark.asyncio
    async def test_create_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/competitors",
            headers=auth_headers,
            json={"rfp_id": 99999, "name": "NoCo"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        """Second user cannot create a competitor for first user's RFP."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.post(
            f"{PREFIX}/competitors",
            headers=other_headers,
            json={"rfp_id": test_rfp.id, "name": "HackCo"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update competitor
# ---------------------------------------------------------------------------


class TestUpdateCompetitor:
    """Tests for PATCH /capture/competitors/{competitor_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{PREFIX}/competitors/1", json={"name": "x"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_competitor: CaptureCompetitor,
    ):
        response = await client.patch(
            f"{PREFIX}/competitors/{test_competitor.id}",
            headers=auth_headers,
            json={"name": "Acme Industries", "incumbent": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Acme Industries"
        assert data["incumbent"] is False

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{PREFIX}/competitors/99999",
            headers=auth_headers,
            json={"name": "nope"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_competitor: CaptureCompetitor,
    ):
        """Second user cannot update first user's competitor."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.patch(
            f"{PREFIX}/competitors/{test_competitor.id}",
            headers=other_headers,
            json={"name": "hacked"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete competitor
# ---------------------------------------------------------------------------


class TestDeleteCompetitor:
    """Tests for DELETE /capture/competitors/{competitor_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{PREFIX}/competitors/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_competitor: CaptureCompetitor,
        test_rfp: RFP,
    ):
        response = await client.delete(
            f"{PREFIX}/competitors/{test_competitor.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify it's gone
        response = await client.get(
            f"{PREFIX}/competitors",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{PREFIX}/competitors/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_competitor: CaptureCompetitor,
    ):
        """Second user cannot delete first user's competitor."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.delete(
            f"{PREFIX}/competitors/{test_competitor.id}",
            headers=other_headers,
        )
        assert response.status_code == 404
