"""
Tests for teaming_board/discovery routes - Partner search and public profiles.
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
async def public_partner(db_session: AsyncSession, test_user: User) -> TeamingPartner:
    partner = TeamingPartner(
        user_id=test_user.id,
        name="Acme CyberSec",
        is_public=True,
        naics_codes=["541512", "541511"],
        set_asides=["8a", "SDVOSB"],
        capabilities=["Cloud Migration", "Penetration Testing"],
        clearance_level="Secret",
        website="https://acme.example.com",
    )
    db_session.add(partner)
    await db_session.commit()
    await db_session.refresh(partner)
    return partner


@pytest_asyncio.fixture
async def private_partner(db_session: AsyncSession, test_user: User) -> TeamingPartner:
    partner = TeamingPartner(
        user_id=test_user.id,
        name="Stealth Corp",
        is_public=False,
    )
    db_session.add(partner)
    await db_session.commit()
    await db_session.refresh(partner)
    return partner


class TestSearchPartnersAuth:
    @pytest.mark.asyncio
    async def test_search_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/search")
        assert resp.status_code == 401


class TestSearchPartners:
    @pytest.mark.asyncio
    async def test_search_returns_public_only(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
        private_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(f"{BASE}/search", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        ids = [p["id"] for p in data]
        assert public_partner.id in ids
        assert private_partner.id not in ids

    @pytest.mark.asyncio
    async def test_search_filter_naics(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(f"{BASE}/search", headers=auth_headers, params={"naics": "541512"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == public_partner.id

    @pytest.mark.asyncio
    async def test_search_filter_naics_no_match(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(f"{BASE}/search", headers=auth_headers, params={"naics": "999999"})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_filter_set_aside(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(f"{BASE}/search", headers=auth_headers, params={"set_aside": "8a"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_search_filter_capability(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(
            f"{BASE}/search", headers=auth_headers, params={"capability": "cloud"}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_search_filter_capability_no_match(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(
            f"{BASE}/search",
            headers=auth_headers,
            params={"capability": "blockchain"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_filter_clearance(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(
            f"{BASE}/search", headers=auth_headers, params={"clearance": "Secret"}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_search_filter_clearance_no_match(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(
            f"{BASE}/search",
            headers=auth_headers,
            params={"clearance": "Top Secret"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_filter_name_q(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(f"{BASE}/search", headers=auth_headers, params={"q": "Acme"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get(f"{BASE}/search", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetPartnerProfile:
    @pytest.mark.asyncio
    async def test_get_profile_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/profile/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_public_profile(
        self,
        client: AsyncClient,
        auth_headers: dict,
        public_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(f"{BASE}/profile/{public_partner.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == public_partner.id
        assert data["name"] == "Acme CyberSec"
        assert "541512" in data["naics_codes"]

    @pytest.mark.asyncio
    async def test_get_private_profile_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        private_partner: TeamingPartner,
    ) -> None:
        resp = await client.get(f"{BASE}/profile/{private_partner.id}", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile_404(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get(f"{BASE}/profile/99999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_profile_idor_second_user_sees_public(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        public_partner: TeamingPartner,
    ) -> None:
        """A second user can still view a public partner profile."""
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

        resp = await client.get(f"{BASE}/profile/{public_partner.id}", headers=headers2)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme CyberSec"
