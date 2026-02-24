"""
Integration tests for capture/teaming.py:
  - POST   /capture/partners
  - GET    /capture/partners
  - PATCH  /capture/partners/{partner_id}
  - DELETE /capture/partners/{partner_id}
  - POST   /capture/partners/link
  - GET    /capture/partners/links?rfp_id=
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import RFPTeamingPartner, TeamingPartner
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
async def test_partner(db_session: AsyncSession, test_user: User) -> TeamingPartner:
    partner = TeamingPartner(
        user_id=test_user.id,
        name="PartnerCo",
        partner_type="sub",
        contact_name="Jane Doe",
        contact_email="jane@partnerco.com",
        notes="Preferred subcontractor",
    )
    db_session.add(partner)
    await db_session.commit()
    await db_session.refresh(partner)
    return partner


@pytest_asyncio.fixture
async def test_link(
    db_session: AsyncSession,
    test_partner: TeamingPartner,
    test_rfp: RFP,
) -> RFPTeamingPartner:
    link = RFPTeamingPartner(
        rfp_id=test_rfp.id,
        partner_id=test_partner.id,
        role="Key subcontractor",
    )
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)
    return link


# ---------------------------------------------------------------------------
# Create partner
# ---------------------------------------------------------------------------


class TestCreatePartner:
    """Tests for POST /capture/partners."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{PREFIX}/partners", json={"name": "SomeCo"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/partners",
            headers=auth_headers,
            json={
                "name": "NewPartner",
                "partner_type": "prime",
                "contact_name": "Bob",
                "contact_email": "bob@newpartner.com",
                "notes": "Great team",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewPartner"
        assert data["partner_type"] == "prime"
        assert data["contact_email"] == "bob@newpartner.com"

    @pytest.mark.asyncio
    async def test_create_minimal(self, client: AsyncClient, auth_headers: dict):
        """Only name is required."""
        response = await client.post(
            f"{PREFIX}/partners",
            headers=auth_headers,
            json={"name": "MinimalCo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MinimalCo"
        assert data["partner_type"] is None

    @pytest.mark.asyncio
    async def test_create_missing_name(self, client: AsyncClient, auth_headers: dict):
        """Missing required name returns 422."""
        response = await client.post(
            f"{PREFIX}/partners",
            headers=auth_headers,
            json={"partner_type": "sub"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# List partners
# ---------------------------------------------------------------------------


class TestListPartners:
    """Tests for GET /capture/partners."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/partners")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{PREFIX}/partners", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_own(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_partner: TeamingPartner,
    ):
        response = await client.get(f"{PREFIX}/partners", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "PartnerCo"

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_partner: TeamingPartner,
    ):
        """Second user cannot see first user's partners."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(f"{PREFIX}/partners", headers=other_headers)
        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# Update partner
# ---------------------------------------------------------------------------


class TestUpdatePartner:
    """Tests for PATCH /capture/partners/{partner_id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(f"{PREFIX}/partners/1", json={"name": "x"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_partner: TeamingPartner,
    ):
        response = await client.patch(
            f"{PREFIX}/partners/{test_partner.id}",
            headers=auth_headers,
            json={"name": "RenamedCo", "contact_name": "New Contact"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "RenamedCo"
        assert data["contact_name"] == "New Contact"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            f"{PREFIX}/partners/99999",
            headers=auth_headers,
            json={"name": "nope"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_partner: TeamingPartner,
    ):
        """Second user cannot update first user's partner."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.patch(
            f"{PREFIX}/partners/{test_partner.id}",
            headers=other_headers,
            json={"name": "hacked"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete partner
# ---------------------------------------------------------------------------


class TestDeletePartner:
    """Tests for DELETE /capture/partners/{partner_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{PREFIX}/partners/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_partner: TeamingPartner,
    ):
        response = await client.delete(f"{PREFIX}/partners/{test_partner.id}", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify it's gone
        response = await client.get(f"{PREFIX}/partners", headers=auth_headers)
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{PREFIX}/partners/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_partner: TeamingPartner,
    ):
        """Second user cannot delete first user's partner."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.delete(
            f"{PREFIX}/partners/{test_partner.id}", headers=other_headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Link partner to RFP
# ---------------------------------------------------------------------------


class TestLinkPartner:
    """Tests for POST /capture/partners/link."""

    @pytest.mark.asyncio
    async def test_link_requires_auth(self, client: AsyncClient):
        response = await client.post(
            f"{PREFIX}/partners/link",
            json={"rfp_id": 1, "partner_id": 1},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_link_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_partner: TeamingPartner,
    ):
        response = await client.post(
            f"{PREFIX}/partners/link",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "partner_id": test_partner.id,
                "role": "Sub on task 2",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == test_rfp.id
        assert data["partner_id"] == test_partner.id
        assert data["role"] == "Sub on task 2"

    @pytest.mark.asyncio
    async def test_link_rfp_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_partner: TeamingPartner,
    ):
        response = await client.post(
            f"{PREFIX}/partners/link",
            headers=auth_headers,
            json={"rfp_id": 99999, "partner_id": test_partner.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_partner_not_found(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(
            f"{PREFIX}/partners/link",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id, "partner_id": 99999},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_idor_rfp(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
        test_partner: TeamingPartner,
    ):
        """Second user cannot link to first user's RFP."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.post(
            f"{PREFIX}/partners/link",
            headers=other_headers,
            json={"rfp_id": test_rfp.id, "partner_id": test_partner.id},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# List partner links
# ---------------------------------------------------------------------------


class TestListPartnerLinks:
    """Tests for GET /capture/partners/links?rfp_id=."""

    @pytest.mark.asyncio
    async def test_list_links_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/partners/links", params={"rfp_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_links_empty(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.get(
            f"{PREFIX}/partners/links",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["links"] == []

    @pytest.mark.asyncio
    async def test_list_links_returns_entries(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_link: RFPTeamingPartner,
    ):
        response = await client.get(
            f"{PREFIX}/partners/links",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["links"][0]["role"] == "Key subcontractor"

    @pytest.mark.asyncio
    async def test_list_links_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            f"{PREFIX}/partners/links",
            headers=auth_headers,
            params={"rfp_id": 99999},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_links_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
        test_link: RFPTeamingPartner,
    ):
        """Second user cannot list first user's partner links."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(
            f"{PREFIX}/partners/links",
            headers=other_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_links_missing_rfp_id(self, client: AsyncClient, auth_headers: dict):
        """Missing required rfp_id query param returns 422."""
        response = await client.get(f"{PREFIX}/partners/links", headers=auth_headers)
        assert response.status_code == 422
