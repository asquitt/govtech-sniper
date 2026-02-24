"""
Tests for teaming_board/profile routes - Partner profile management.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import TeamingPartner
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/teaming"


@pytest_asyncio.fixture
async def my_partner(db_session: AsyncSession, test_user: User) -> TeamingPartner:
    partner = TeamingPartner(
        user_id=test_user.id,
        name="My Company Profile",
        is_public=False,
        naics_codes=["541512"],
        set_asides=["8a"],
        capabilities=["Cloud"],
        clearance_level="Secret",
    )
    db_session.add(partner)
    await db_session.commit()
    await db_session.refresh(partner)
    return partner


class TestUpdateMyProfileAuth:
    @pytest.mark.asyncio
    async def test_update_profile_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.patch(f"{BASE}/my-profile/1")
        assert resp.status_code == 401


class TestUpdateMyProfile:
    @pytest.mark.asyncio
    async def test_update_is_public(
        self,
        client: AsyncClient,
        auth_headers: dict,
        my_partner: TeamingPartner,
    ) -> None:
        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=auth_headers,
            params={"is_public": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_public"] is True

    @pytest.mark.asyncio
    async def test_update_naics_codes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        my_partner: TeamingPartner,
    ) -> None:
        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=auth_headers,
            params={"naics_codes": ["541512", "541611"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "541611" in data["naics_codes"]

    @pytest.mark.asyncio
    async def test_update_capabilities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        my_partner: TeamingPartner,
    ) -> None:
        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=auth_headers,
            params={"capabilities": ["Cloud", "AI/ML"]},
        )
        assert resp.status_code == 200
        assert "AI/ML" in resp.json()["capabilities"]

    @pytest.mark.asyncio
    async def test_update_clearance_level(
        self,
        client: AsyncClient,
        auth_headers: dict,
        my_partner: TeamingPartner,
    ) -> None:
        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=auth_headers,
            params={"clearance_level": "Top Secret"},
        )
        assert resp.status_code == 200
        assert resp.json()["clearance_level"] == "Top Secret"

    @pytest.mark.asyncio
    async def test_update_website_and_duns(
        self,
        client: AsyncClient,
        auth_headers: dict,
        my_partner: TeamingPartner,
    ) -> None:
        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=auth_headers,
            params={
                "website": "https://new.example.com",
                "company_duns": "123456789",
                "cage_code": "ABC12",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["website"] == "https://new.example.com"
        assert data["company_duns"] == "123456789"
        assert data["cage_code"] == "ABC12"

    @pytest.mark.asyncio
    async def test_update_past_performance(
        self,
        client: AsyncClient,
        auth_headers: dict,
        my_partner: TeamingPartner,
    ) -> None:
        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=auth_headers,
            params={"past_performance_summary": "Delivered 10 contracts on time."},
        )
        assert resp.status_code == 200
        assert "10 contracts" in resp.json()["past_performance_summary"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_partner_404(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.patch(f"{BASE}/my-profile/99999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_other_users_partner_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        my_partner: TeamingPartner,
    ) -> None:
        """A second user cannot update a partner owned by the first user."""
        user2 = User(
            email="user2@example.com",
            hashed_password=hash_password("Password123!"),
            full_name="User Two",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user2)
        tokens = create_token_pair(user2.id, user2.email, user2.tier)
        headers2 = {"Authorization": f"Bearer {tokens.access_token}"}

        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=headers2,
            params={"is_public": True},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_returns_extended_fields(
        self,
        client: AsyncClient,
        auth_headers: dict,
        my_partner: TeamingPartner,
    ) -> None:
        resp = await client.patch(
            f"{BASE}/my-profile/{my_partner.id}",
            headers=auth_headers,
            params={"set_asides": ["WOSB"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Verify extended schema fields are present
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
        assert "updated_at" in data
