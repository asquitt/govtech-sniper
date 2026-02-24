"""
Integration tests for admin route modules:
  - admin/analytics.py  (GET /admin/usage, GET /admin/audit)
  - admin/members.py    (POST /admin/members/invite, GET /admin/member-invitations, etc.)
  - admin/organization.py (POST /admin/organizations, GET /admin/organization, PATCH /admin/organization,
                           GET /admin/capability-health)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import (
    Organization,
    OrganizationMember,
    OrgRole,
)
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    organization = Organization(
        name="Test Org",
        slug="test-org-admin",
        domain="testorg.com",
        billing_email="billing@testorg.com",
    )
    db_session.add(organization)
    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, org: Organization) -> User:
    """Create an admin user linked to the test org."""
    user = User(
        email="admin@testorg.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
        company_name="Test Org",
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
    """Auth headers for the admin user."""
    tokens = create_token_pair(admin_user.id, admin_user.email, admin_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def regular_member(db_session: AsyncSession, org: Organization) -> User:
    """Create a regular (non-admin) member."""
    user = User(
        email="member@testorg.com",
        hashed_password=hash_password("MemberPass123!"),
        full_name="Regular Member",
        company_name="Test Org",
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
async def member_headers(regular_member: User) -> dict:
    """Auth headers for the regular member (non-admin)."""
    tokens = create_token_pair(regular_member.id, regular_member.email, regular_member.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def no_org_user(db_session: AsyncSession) -> User:
    """Create a user with no org membership."""
    user = User(
        email="noorg@example.com",
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
# Analytics tests
# ---------------------------------------------------------------------------


class TestAdminAnalytics:
    """Tests for GET /admin/usage and GET /admin/audit."""

    @pytest.mark.asyncio
    async def test_usage_analytics_empty_org(self, client: AsyncClient, admin_headers: dict):
        """Usage analytics returns zero counts when no activity exists."""
        response = await client.get("/api/v1/admin/usage", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert "proposals" in data
        assert "rfps" in data
        assert "audit_events" in data
        assert "period_days" in data
        assert data["period_days"] == 30

    @pytest.mark.asyncio
    async def test_usage_analytics_custom_days(self, client: AsyncClient, admin_headers: dict):
        """Usage analytics respects the ?days query param."""
        response = await client.get("/api/v1/admin/usage?days=7", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["period_days"] == 7

    @pytest.mark.asyncio
    async def test_usage_analytics_invalid_days(self, client: AsyncClient, admin_headers: dict):
        """Usage analytics rejects days out of 7-90 range."""
        response = await client.get("/api/v1/admin/usage?days=1", headers=admin_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_usage_analytics_requires_admin(self, client: AsyncClient, member_headers: dict):
        """Non-admin member is rejected with 403."""
        response = await client.get("/api/v1/admin/usage", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_usage_analytics_requires_org(self, client: AsyncClient, no_org_headers: dict):
        """User without org membership is rejected with 403."""
        response = await client.get("/api/v1/admin/usage", headers=no_org_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_audit_log_empty(self, client: AsyncClient, admin_headers: dict):
        """Audit log returns empty list with no events."""
        response = await client.get("/api/v1/admin/audit", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)

    @pytest.mark.asyncio
    async def test_audit_log_requires_admin(self, client: AsyncClient, member_headers: dict):
        """Audit log is blocked for non-admin members."""
        response = await client.get("/api/v1/admin/audit", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_audit_log_pagination(self, client: AsyncClient, admin_headers: dict):
        """Audit log pagination params are accepted."""
        response = await client.get("/api/v1/admin/audit?limit=10&offset=0", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_audit_log_requires_auth(self, client: AsyncClient):
        """Audit log returns 401 without auth token."""
        response = await client.get("/api/v1/admin/audit")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Member management tests
# ---------------------------------------------------------------------------


class TestAdminMembers:
    """Tests for member listing, role updates, and deactivation."""

    @pytest.mark.asyncio
    async def test_list_members(
        self,
        client: AsyncClient,
        admin_headers: dict,
        regular_member: User,
    ):
        """Admin can list org members."""
        response = await client.get("/api/v1/admin/members", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert "total" in data
        # At minimum the admin + regular_member are present
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_list_members_requires_admin(self, client: AsyncClient, member_headers: dict):
        """Regular member cannot list members."""
        response = await client.get("/api/v1/admin/members", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_member_role(
        self,
        client: AsyncClient,
        admin_headers: dict,
        regular_member: User,
    ):
        """Owner can update a member's role."""
        response = await client.patch(
            f"/api/v1/admin/members/{regular_member.id}/role",
            headers=admin_headers,
            json={"role": "member"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["user_id"] == regular_member.id

    @pytest.mark.asyncio
    async def test_update_member_role_self_not_allowed(
        self, client: AsyncClient, admin_user: User, admin_headers: dict
    ):
        """Admin cannot change their own role."""
        response = await client.patch(
            f"/api/v1/admin/members/{admin_user.id}/role",
            headers=admin_headers,
            json={"role": "member"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_member_role_nonexistent(self, client: AsyncClient, admin_headers: dict):
        """Returns 404 for unknown user_id."""
        response = await client.patch(
            "/api/v1/admin/members/999999/role",
            headers=admin_headers,
            json={"role": "member"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_member(
        self,
        client: AsyncClient,
        admin_headers: dict,
        regular_member: User,
    ):
        """Owner can deactivate a member."""
        response = await client.post(
            f"/api/v1/admin/members/{regular_member.id}/deactivate",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deactivated"

    @pytest.mark.asyncio
    async def test_deactivate_self_not_allowed(
        self, client: AsyncClient, admin_user: User, admin_headers: dict
    ):
        """Admin cannot deactivate themselves."""
        response = await client.post(
            f"/api/v1/admin/members/{admin_user.id}/deactivate",
            headers=admin_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_reactivate_member(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org: Organization,
        admin_headers: dict,
        regular_member: User,
    ):
        """Owner can reactivate a deactivated member."""
        # First deactivate
        await client.post(
            f"/api/v1/admin/members/{regular_member.id}/deactivate",
            headers=admin_headers,
        )
        response = await client.post(
            f"/api/v1/admin/members/{regular_member.id}/reactivate",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reactivated"


# ---------------------------------------------------------------------------
# Invitation tests
# ---------------------------------------------------------------------------


class TestAdminInvitations:
    """Tests for invitation CRUD."""

    @pytest.mark.asyncio
    async def test_invite_member(self, client: AsyncClient, admin_headers: dict):
        """Admin can create an invitation for a new email."""
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=admin_headers,
            json={"email": "newmember@example.com", "role": "member", "expires_in_days": 7},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newmember@example.com"
        assert data["role"] == "member"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_invite_member_duplicate_active(self, client: AsyncClient, admin_headers: dict):
        """Creating a second active invite for same email returns 409."""
        await client.post(
            "/api/v1/admin/members/invite",
            headers=admin_headers,
            json={"email": "dupinvite@example.com", "role": "member", "expires_in_days": 7},
        )
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=admin_headers,
            json={"email": "dupinvite@example.com", "role": "member", "expires_in_days": 7},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_invite_expires_in_days_invalid(self, client: AsyncClient, admin_headers: dict):
        """Invitation with out-of-range expires_in_days is rejected."""
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=admin_headers,
            json={"email": "bad@example.com", "role": "member", "expires_in_days": 0},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_invitations(self, client: AsyncClient, admin_headers: dict):
        """Admin can list all invitations for the org."""
        response = await client.get("/api/v1/admin/member-invitations", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_revoke_invitation(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can revoke a pending invitation."""
        create_resp = await client.post(
            "/api/v1/admin/members/invite",
            headers=admin_headers,
            json={"email": "torevoke@example.com", "role": "member", "expires_in_days": 7},
        )
        assert create_resp.status_code == 201
        inv_id = create_resp.json()["id"]

        revoke_resp = await client.post(
            f"/api/v1/admin/member-invitations/{inv_id}/revoke",
            headers=admin_headers,
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["status"] == "revoked"

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_invitation(self, client: AsyncClient, admin_headers: dict):
        """Revoking a non-existent invitation returns 404."""
        response = await client.post(
            "/api/v1/admin/member-invitations/999999/revoke",
            headers=admin_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resend_invitation(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can resend a pending invitation, resetting expiry."""
        create_resp = await client.post(
            "/api/v1/admin/members/invite",
            headers=admin_headers,
            json={"email": "toresend@example.com", "role": "member", "expires_in_days": 7},
        )
        assert create_resp.status_code == 201
        inv_id = create_resp.json()["id"]

        resend_resp = await client.post(
            f"/api/v1/admin/member-invitations/{inv_id}/resend",
            headers=admin_headers,
            json={"expires_in_days": 14},
        )
        assert resend_resp.status_code == 200
        assert resend_resp.json()["status"] == "pending"


# ---------------------------------------------------------------------------
# Organization CRUD tests
# ---------------------------------------------------------------------------


class TestAdminOrganization:
    """Tests for org create/read/update and capability health."""

    @pytest.mark.asyncio
    async def test_create_organization(self, client: AsyncClient, auth_headers: dict):
        """Authenticated user can create a new organization."""
        response = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={"name": "New Org", "slug": "new-org-slug"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Org"
        assert data["slug"] == "new-org-slug"

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Duplicate slug returns 409."""
        await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={"name": "First Org", "slug": "dup-slug"},
        )
        response = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={"name": "Second Org", "slug": "dup-slug"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_get_organization(
        self, client: AsyncClient, admin_headers: dict, org: Organization
    ):
        """Admin can retrieve org details."""
        response = await client.get("/api/v1/admin/organization", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == org.name
        assert "member_count" in data

    @pytest.mark.asyncio
    async def test_get_organization_requires_admin(self, client: AsyncClient, member_headers: dict):
        """Non-admin gets 403 on org details."""
        response = await client.get("/api/v1/admin/organization", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_organization(
        self, client: AsyncClient, admin_headers: dict, org: Organization
    ):
        """Admin can update org name."""
        response = await client.patch(
            "/api/v1/admin/organization",
            headers=admin_headers,
            json={"name": "Updated Org Name"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "updated"

    @pytest.mark.asyncio
    async def test_capability_health(self, client: AsyncClient, admin_headers: dict):
        """Capability health endpoint returns structured runtime info."""
        response = await client.get("/api/v1/admin/capability-health", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "runtime" in data
        assert "workers" in data
        assert "enterprise" in data
        assert "discoverability" in data
        assert isinstance(data["discoverability"], list)

    @pytest.mark.asyncio
    async def test_capability_health_requires_admin(
        self, client: AsyncClient, member_headers: dict
    ):
        """Non-admin gets 403 on capability health."""
        response = await client.get("/api/v1/admin/capability-health", headers=member_headers)
        assert response.status_code == 403
