"""
Integration tests for admin/integrations.py routes:
  - GET /api/v1/admin/provider-maturity
  - GET /api/v1/admin/release-gate
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    organization = Organization(
        name="Integrations Org",
        slug="integrations-org",
        domain="integ.com",
    )
    db_session.add(organization)
    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        email="integ-admin@test.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Integrations Admin",
        company_name="Integrations Org",
        tier="professional",
        is_active=True,
        is_verified=True,
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.flush()
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrgRole.OWNER,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict:
    tokens = create_token_pair(admin_user.id, admin_user.email, admin_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        email="integ-member@test.com",
        hashed_password=hash_password("MemberPass123!"),
        full_name="Regular Member",
        company_name="Integrations Org",
        tier="free",
        is_active=True,
        is_verified=True,
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.flush()
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrgRole.MEMBER,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def member_headers(member_user: User) -> dict:
    tokens = create_token_pair(member_user.id, member_user.email, member_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


# ---------------------------------------------------------------------------
# GET /api/v1/admin/provider-maturity
# ---------------------------------------------------------------------------


class TestGetProviderMaturity:
    """GET /api/v1/admin/provider-maturity"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/provider-maturity")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.get("/api/v1/admin/provider-maturity", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_provider_list(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/provider-maturity", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "total" in data
        assert "timestamp" in data
        assert isinstance(data["providers"], list)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/release-gate
# ---------------------------------------------------------------------------


class TestGetReleaseGate:
    """GET /api/v1/admin/release-gate"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/release-gate")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.get("/api/v1/admin/release-gate", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_release_gate_data(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/release-gate", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Release gate returns structured SLO data
        assert isinstance(data, dict)
