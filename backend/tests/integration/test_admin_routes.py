"""
Admin Routes Integration Tests
================================
Tests for organization management, members, analytics, and integrations.
All endpoints require admin role via _require_org_admin.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import (
    Organization,
    OrganizationMember,
    OrgRole,
)
from app.models.user import User

# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture
async def test_org(db_session: AsyncSession, test_user: User) -> Organization:
    org = Organization(
        name="Test Org",
        slug="test-org",
        domain="example.com",
        billing_email="billing@example.com",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    test_user.organization_id = org.id
    db_session.add(test_user)

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=test_user.id,
        role=OrgRole.OWNER,
        is_active=True,
    )
    db_session.add(membership)
    await db_session.commit()
    return org


# =============================================================================
# POST /admin/organizations — create org
# =============================================================================


class TestCreateOrganization:
    @pytest.mark.asyncio
    async def test_create_org_success(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/admin/organizations",
            json={"name": "New Org", "slug": "new-org"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Org"
        assert data["slug"] == "new-org"

    @pytest.mark.asyncio
    async def test_create_org_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/admin/organizations",
            json={"name": "Org", "slug": "org"},
        )
        assert resp.status_code == 401


# =============================================================================
# GET /admin/organization — get current org
# =============================================================================


class TestGetOrganization:
    @pytest.mark.asyncio
    async def test_get_org_success(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.get("/api/v1/admin/organization", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Org"

    @pytest.mark.asyncio
    async def test_get_org_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/organization")
        assert resp.status_code == 401


# =============================================================================
# PATCH /admin/organization — update org
# =============================================================================


class TestUpdateOrganization:
    @pytest.mark.asyncio
    async def test_update_org_name(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.patch(
            "/api/v1/admin/organization",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


# =============================================================================
# POST /admin/members/invite — invite member
# =============================================================================


class TestInviteMember:
    @pytest.mark.asyncio
    async def test_invite_member_success(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.post(
            "/api/v1/admin/members/invite",
            json={"email": "newmember@example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_invite_member_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/admin/members/invite",
            json={"email": "someone@example.com"},
        )
        assert resp.status_code == 401


# =============================================================================
# GET /admin/members — list members
# =============================================================================


class TestListMembers:
    @pytest.mark.asyncio
    async def test_list_members_returns_owner(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.get("/api/v1/admin/members", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["members"]) >= 1


# =============================================================================
# GET /admin/usage — usage analytics
# =============================================================================


class TestUsageAnalytics:
    @pytest.mark.asyncio
    async def test_usage_analytics_returns_counts(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.get("/api/v1/admin/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "members" in data
        assert "period_days" in data

    @pytest.mark.asyncio
    async def test_usage_analytics_custom_days(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.get("/api/v1/admin/usage?days=7", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["period_days"] == 7


# =============================================================================
# GET /admin/audit — audit log
# =============================================================================


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_audit_log_returns_list(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.get("/api/v1/admin/audit", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_audit_log_pagination(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        resp = await client.get("/api/v1/admin/audit?limit=5&offset=0", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["limit"] == 5
