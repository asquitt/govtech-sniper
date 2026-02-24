"""
Tests for admin/members routes - Organization member management.
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import (
    InvitationStatus,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrgRole,
)
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    org = Organization(
        name="Test Corp",
        slug="test-corp",
        domain="testcorp.com",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def org_owner(db_session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="owner@testcorp.com",
        hashed_password=hash_password("Password123!"),
        full_name="Org Owner",
        company_name="Test Corp",
        tier="professional",
        is_active=True,
        is_verified=True,
        organization_id=test_org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    member = OrganizationMember(
        organization_id=test_org.id,
        user_id=user.id,
        role=OrgRole.OWNER,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def owner_headers(org_owner: User) -> dict:
    tokens = create_token_pair(org_owner.id, org_owner.email, org_owner.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def org_admin(db_session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="admin@testcorp.com",
        hashed_password=hash_password("Password123!"),
        full_name="Org Admin",
        company_name="Test Corp",
        tier="professional",
        is_active=True,
        is_verified=True,
        organization_id=test_org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    member = OrganizationMember(
        organization_id=test_org.id,
        user_id=user.id,
        role=OrgRole.ADMIN,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def admin_headers(org_admin: User) -> dict:
    tokens = create_token_pair(org_admin.id, org_admin.email, org_admin.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def org_member(db_session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="member@testcorp.com",
        hashed_password=hash_password("Password123!"),
        full_name="Org Member",
        company_name="Test Corp",
        tier="professional",
        is_active=True,
        is_verified=True,
        organization_id=test_org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    member = OrganizationMember(
        organization_id=test_org.id,
        user_id=user.id,
        role=OrgRole.MEMBER,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_invitation(
    db_session: AsyncSession, test_org: Organization, org_owner: User
) -> OrganizationInvitation:
    invitation = OrganizationInvitation(
        organization_id=test_org.id,
        invited_by_user_id=org_owner.id,
        email="newuser@testcorp.com",
        role=OrgRole.MEMBER,
        token="test-token-abc123",
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(invitation)
    await db_session.commit()
    await db_session.refresh(invitation)
    return invitation


class TestInviteMember:
    """Tests for POST /api/v1/admin/members/invite."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/admin/members/invite",
            json={"email": "new@testcorp.com"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_returns_403(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=auth_headers,
            json={"email": "new@testcorp.com"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invite_member_success(
        self, client: AsyncClient, owner_headers: dict, test_org: Organization, org_owner: User
    ):
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=owner_headers,
            json={"email": "invited@testcorp.com", "role": "member", "expires_in_days": 7},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "invited@testcorp.com"
        assert data["role"] == "member"
        assert data["status"] == "pending"
        assert data["activation_ready"] is False

    @pytest.mark.asyncio
    async def test_invite_existing_active_member_returns_409(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        org_member: User,
    ):
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=owner_headers,
            json={"email": org_member.email},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_invite_duplicate_pending_returns_409(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        test_invitation: OrganizationInvitation,
    ):
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=owner_headers,
            json={"email": "newuser@testcorp.com"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_admin_cannot_invite_admin(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_org: Organization,
        org_admin: User,
    ):
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=admin_headers,
            json={"email": "newadmin@testcorp.com", "role": "admin"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_owner_can_invite_admin(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=owner_headers,
            json={"email": "newadmin@testcorp.com", "role": "admin"},
        )
        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_invalid_expires_days_returns_400(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.post(
            "/api/v1/admin/members/invite",
            headers=owner_headers,
            json={"email": "new@testcorp.com", "expires_in_days": 0},
        )
        assert response.status_code == 400


class TestListInvitations:
    """Tests for GET /api/v1/admin/member-invitations."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/member-invitations")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_invitations_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        test_invitation: OrganizationInvitation,
    ):
        response = await client.get(
            "/api/v1/admin/member-invitations",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestActivateInvitation:
    """Tests for POST /api/v1/admin/member-invitations/{invitation_id}/activate."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_invitation: OrganizationInvitation
    ):
        response = await client.post(
            f"/api/v1/admin/member-invitations/{test_invitation.id}/activate",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_activate_invitation_user_not_registered_returns_409(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        test_invitation: OrganizationInvitation,
    ):
        response = await client.post(
            f"/api/v1/admin/member-invitations/{test_invitation.id}/activate",
            headers=owner_headers,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_activate_invitation_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        test_invitation: OrganizationInvitation,
    ):
        # Register the invited user
        invited_user = User(
            email="newuser@testcorp.com",
            hashed_password=hash_password("Password123!"),
            full_name="New User",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(invited_user)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/admin/member-invitations/{test_invitation.id}/activate",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "activated"

    @pytest.mark.asyncio
    async def test_activate_nonexistent_invitation_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.post(
            "/api/v1/admin/member-invitations/99999/activate",
            headers=owner_headers,
        )
        assert response.status_code == 404


class TestRevokeInvitation:
    """Tests for POST /api/v1/admin/member-invitations/{invitation_id}/revoke."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_invitation: OrganizationInvitation
    ):
        response = await client.post(
            f"/api/v1/admin/member-invitations/{test_invitation.id}/revoke",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_invitation_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        test_invitation: OrganizationInvitation,
    ):
        response = await client.post(
            f"/api/v1/admin/member-invitations/{test_invitation.id}/revoke",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "revoked"

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_returns_404(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.post(
            "/api/v1/admin/member-invitations/99999/revoke",
            headers=owner_headers,
        )
        assert response.status_code == 404


class TestListMembers:
    """Tests for GET /api/v1/admin/members."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/members")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_members_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        org_member: User,
    ):
        response = await client.get(
            "/api/v1/admin/members",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert data["total"] >= 2


class TestUpdateMemberRole:
    """Tests for PATCH /api/v1/admin/members/{user_id}/role."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, org_member: User):
        response = await client.patch(
            f"/api/v1/admin/members/{org_member.id}/role",
            json={"role": "viewer"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_role_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        org_member: User,
    ):
        response = await client.patch(
            f"/api/v1/admin/members/{org_member.id}/role",
            headers=owner_headers,
            json={"role": "viewer"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_cannot_change_own_role(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.patch(
            f"/api/v1/admin/members/{org_owner.id}/role",
            headers=owner_headers,
            json={"role": "member"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_cannot_promote_to_admin(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_org: Organization,
        org_admin: User,
        org_member: User,
    ):
        response = await client.patch(
            f"/api/v1/admin/members/{org_member.id}/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_member_not_found(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.patch(
            "/api/v1/admin/members/99999/role",
            headers=owner_headers,
            json={"role": "member"},
        )
        assert response.status_code == 404


class TestDeactivateMember:
    """Tests for POST /api/v1/admin/members/{user_id}/deactivate."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, org_member: User):
        response = await client.post(
            f"/api/v1/admin/members/{org_member.id}/deactivate",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deactivate_member_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        org_member: User,
    ):
        response = await client.post(
            f"/api/v1/admin/members/{org_member.id}/deactivate",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deactivated"

    @pytest.mark.asyncio
    async def test_cannot_deactivate_self(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.post(
            f"/api/v1/admin/members/{org_owner.id}/deactivate",
            headers=owner_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_cannot_deactivate_admin(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_org: Organization,
        org_admin: User,
        org_owner: User,
    ):
        response = await client.post(
            f"/api/v1/admin/members/{org_owner.id}/deactivate",
            headers=admin_headers,
        )
        assert response.status_code == 403


class TestReactivateMember:
    """Tests for POST /api/v1/admin/members/{user_id}/reactivate."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, org_member: User):
        response = await client.post(
            f"/api/v1/admin/members/{org_member.id}/reactivate",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reactivate_member_success(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
        org_member: User,
    ):
        # First deactivate
        await client.post(
            f"/api/v1/admin/members/{org_member.id}/deactivate",
            headers=owner_headers,
        )
        # Then reactivate
        response = await client.post(
            f"/api/v1/admin/members/{org_member.id}/reactivate",
            headers=owner_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reactivated"

    @pytest.mark.asyncio
    async def test_reactivate_not_found(
        self,
        client: AsyncClient,
        owner_headers: dict,
        test_org: Organization,
        org_owner: User,
    ):
        response = await client.post(
            "/api/v1/admin/members/99999/reactivate",
            headers=owner_headers,
        )
        assert response.status_code == 404
