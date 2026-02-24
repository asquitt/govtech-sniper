"""
Integration tests for admin/analytics.py routes:
  - GET /api/v1/admin/usage
  - GET /api/v1/admin/audit
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    organization = Organization(
        name="Analytics Org",
        slug="analytics-org",
        domain="analyticsorg.com",
        billing_email="billing@analyticsorg.com",
    )
    db_session.add(organization)
    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        email="analytics-admin@test.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Analytics Admin",
        company_name="Analytics Org",
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
        email="analytics-member@test.com",
        hashed_password=hash_password("MemberPass123!"),
        full_name="Regular Member",
        company_name="Analytics Org",
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
# GET /api/v1/admin/usage
# ---------------------------------------------------------------------------


class TestGetUsageAnalytics:
    """GET /api/v1/admin/usage"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/usage")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.get("/api/v1/admin/usage", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_usage_data(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/usage", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert "proposals" in data
        assert "rfps" in data
        assert "audit_events" in data
        assert "active_users" in data
        assert "by_action" in data
        assert data["period_days"] == 30

    @pytest.mark.asyncio
    async def test_custom_days_param(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/usage?days=7", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["period_days"] == 7

    @pytest.mark.asyncio
    async def test_days_too_small_rejected(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/usage?days=1", headers=admin_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_days_too_large_rejected(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/usage?days=100", headers=admin_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_with_activity(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user: User,
    ):
        """Usage analytics counts RFPs and proposals created by org members."""
        rfp = RFP(
            user_id=admin_user.id,
            title="Analytics Test RFP",
            solicitation_number="AA-ANALYTICS-001",
            agency="Department of Test",
            status="new",
        )
        db_session.add(rfp)
        await db_session.flush()

        proposal = Proposal(
            user_id=admin_user.id,
            rfp_id=rfp.id,
            title="Analytics Test Proposal",
            status="draft",
        )
        db_session.add(proposal)

        audit = AuditEvent(
            user_id=admin_user.id,
            entity_type="rfp",
            entity_id=rfp.id,
            action="rfp.created",
            event_metadata={},
        )
        db_session.add(audit)
        await db_session.commit()

        response = await client.get("/api/v1/admin/usage", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["rfps"] >= 1
        assert data["proposals"] >= 1
        assert data["audit_events"] >= 1


# ---------------------------------------------------------------------------
# GET /api/v1/admin/audit
# ---------------------------------------------------------------------------


class TestGetOrgAuditLog:
    """GET /api/v1/admin/audit"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/audit")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, member_headers: dict):
        response = await client.get("/api/v1/admin/audit", headers=member_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_empty_events(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/audit", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)
        assert "total" in data

    @pytest.mark.asyncio
    async def test_pagination(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/audit?limit=10&offset=0", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_filter_by_action(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/audit?action=rfp.created", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_entity_type(self, client: AsyncClient, admin_headers: dict):
        response = await client.get("/api/v1/admin/audit?entity_type=rfp", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_with_audit_events(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user: User,
    ):
        event = AuditEvent(
            user_id=admin_user.id,
            entity_type="test",
            entity_id=1,
            action="test.action",
            event_metadata={"key": "value"},
        )
        db_session.add(event)
        await db_session.commit()

        response = await client.get("/api/v1/admin/audit", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["events"][0]["action"] == "test.action"
        assert data["events"][0]["user_email"] is not None
