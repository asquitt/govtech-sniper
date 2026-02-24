"""
Integration tests for admin/organization.py routes:
  - POST /api/v1/admin/organizations
  - GET  /api/v1/admin/organization
  - PATCH /api/v1/admin/organization
  - GET  /api/v1/admin/capability-health
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
        name="Org Routes Org",
        slug="org-routes-org",
        domain="orgroutes.com",
        billing_email="billing@orgroutes.com",
    )
    db_session.add(organization)
    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        email="org-admin@test.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Org Admin",
        company_name="Org Routes Org",
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
        email="org-member@test.com",
        hashed_password=hash_password("MemberPass123!"),
        full_name="Regular Member",
        company_name="Org Routes Org",
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


@pytest_asyncio.fixture
async def no_org_user(db_session: AsyncSession) -> User:
    user = User(
        email="no-org-orgtest@test.com",
        hashed_password=hash_password("NoOrgPass123!"),
        full_name="No Org User",
        company_name="None",
        tier="free",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def no_org_headers(no_org_user: User) -> dict:
    tokens = create_token_pair(no_org_user.id, no_org_user.email, no_org_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


# ---------------------------------------------------------------------------
# POST /api/v1/admin/organizations
# ---------------------------------------------------------------------------


class TestCreateOrganization:
    """POST /api/v1/admin/organizations"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/admin/organizations",
            json={"name": "Test", "slug": "test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_org(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={"name": "Brand New Org", "slug": "brand-new-org-test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Brand New Org"
        assert data["slug"] == "brand-new-org-test"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_duplicate_slug_409(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={"name": "Org A", "slug": "dup-org-slug"},
        )
        response = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={"name": "Org B", "slug": "dup-org-slug"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_with_optional_fields(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={
                "name": "Full Org",
                "slug": "full-org-test",
                "domain": "fullorg.com",
                "billing_email": "billing@fullorg.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "fullorg.com"


# ---------------------------------------------------------------------------
# GET /api/v1/admin/organization
# ---------------------------------------------------------------------------


class TestGetOrganization:
    """GET /api/v1/admin/organization"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/organization")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.get("/api/v1/admin/organization", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_no_org_forbidden(self, client: AsyncClient, no_org_headers: dict):
        response = await client.get("/api/v1/admin/organization", headers=no_org_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_org_details(
        self, client: AsyncClient, admin_headers: dict, org: Organization
    ):
        response = await client.get("/api/v1/admin/organization", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == org.name
        assert data["slug"] == org.slug
        assert "member_count" in data
        assert "sso_enabled" in data
        assert "created_at" in data


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/organization
# ---------------------------------------------------------------------------


class TestUpdateOrganization:
    """PATCH /api/v1/admin/organization"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/admin/organization", json={"name": "New"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.patch(
            "/api/v1/admin/organization",
            headers=member_headers,
            json={"name": "New"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_name(self, client: AsyncClient, admin_headers: dict):
        response = await client.patch(
            "/api/v1/admin/organization",
            headers=admin_headers,
            json={"name": "Updated Org Name"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "updated"

    @pytest.mark.asyncio
    async def test_update_security_policy(self, client: AsyncClient, admin_headers: dict):
        response = await client.patch(
            "/api/v1/admin/organization",
            headers=admin_headers,
            json={"require_step_up_for_sensitive_exports": True},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/admin/capability-health
# ---------------------------------------------------------------------------


class TestCapabilityHealth:
    """GET /api/v1/admin/capability-health"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/capability-health")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.get("/api/v1/admin/capability-health", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_health_data(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/capability-health", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "runtime" in data
        assert "workers" in data
        assert "enterprise" in data
        assert "discoverability" in data
        assert isinstance(data["discoverability"], list)
        assert "organization_id" in data
        assert "integrations_by_provider" in data
