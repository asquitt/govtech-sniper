"""
RFP Sniper - Admin role guard tests
===================================
Multi-user role guard coverage for org admin endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrganizationMember, OrgRole
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_org_user(
    db_session: AsyncSession,
    organization_id: int,
    email: str,
    role: OrgRole,
) -> tuple[User, dict[str, str]]:
    user = User(
        email=email,
        hashed_password=hash_password("TestPassword123!"),
        full_name=email.split("@")[0],
        company_name="GovTech Co",
        tier="professional",
        is_active=True,
        is_verified=True,
        organization_id=organization_id,
    )
    db_session.add(user)
    await db_session.flush()

    member = OrganizationMember(
        organization_id=organization_id,
        user_id=user.id,
        role=role,
        is_active=True,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)

    tokens = create_token_pair(user.id, user.email, str(user.tier))
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


async def _create_standalone_user(
    db_session: AsyncSession,
    email: str,
) -> tuple[User, dict[str, str]]:
    user = User(
        email=email,
        hashed_password=hash_password("TestPassword123!"),
        full_name=email.split("@")[0],
        company_name="GovTech Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    tokens = create_token_pair(user.id, user.email, str(user.tier))
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


class TestAdminRoles:
    @pytest.mark.asyncio
    async def test_owner_admin_member_guards_and_role_promotion(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        create_org = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={
                "name": "Role Guard Org",
                "slug": "role-guard-org",
                "domain": "roles.example.com",
            },
        )
        assert create_org.status_code == 200
        organization_id = create_org.json()["id"]

        _admin_user, admin_headers = await _create_org_user(
            db_session,
            organization_id=organization_id,
            email="org-admin@example.com",
            role=OrgRole.ADMIN,
        )
        member_user, member_headers = await _create_org_user(
            db_session,
            organization_id=organization_id,
            email="org-member@example.com",
            role=OrgRole.MEMBER,
        )

        member_blocked = await client.get("/api/v1/admin/members", headers=member_headers)
        assert member_blocked.status_code == 403

        admin_allowed = await client.get("/api/v1/admin/members", headers=admin_headers)
        assert admin_allowed.status_code == 200

        admin_cannot_promote = await client.patch(
            f"/api/v1/admin/members/{member_user.id}/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert admin_cannot_promote.status_code == 403

        owner_promotes = await client.patch(
            f"/api/v1/admin/members/{member_user.id}/role",
            headers=auth_headers,
            json={"role": "admin"},
        )
        assert owner_promotes.status_code == 200
        assert owner_promotes.json()["role"] == "admin"

        promoted_access = await client.get(
            "/api/v1/admin/capability-health",
            headers=member_headers,
        )
        assert promoted_access.status_code == 200

    @pytest.mark.asyncio
    async def test_org_member_invitation_activation_flow(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        create_org = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={
                "name": "Invite Flow Org",
                "slug": "invite-flow-org",
                "domain": "invite.example.com",
            },
        )
        assert create_org.status_code == 200

        invite_email = "invite-flow-member@example.com"
        invite = await client.post(
            "/api/v1/admin/members/invite",
            headers=auth_headers,
            json={
                "email": invite_email,
                "role": "member",
                "expires_in_days": 10,
            },
        )
        assert invite.status_code == 201
        invite_payload = invite.json()
        assert invite_payload["email"] == invite_email
        assert invite_payload["status"] == "pending"
        assert invite_payload["activation_ready"] is False

        invitations = await client.get(
            "/api/v1/admin/member-invitations",
            headers=auth_headers,
        )
        assert invitations.status_code == 200
        assert any(item["email"] == invite_email for item in invitations.json())

        activate_before_signup = await client.post(
            f"/api/v1/admin/member-invitations/{invite_payload['id']}/activate",
            headers=auth_headers,
        )
        assert activate_before_signup.status_code == 409

        _invited_user, _invited_headers = await _create_standalone_user(
            db_session,
            invite_email,
        )

        activate = await client.post(
            f"/api/v1/admin/member-invitations/{invite_payload['id']}/activate",
            headers=auth_headers,
        )
        assert activate.status_code == 200
        activate_payload = activate.json()
        assert activate_payload["status"] == "activated"
        assert activate_payload["accepted_user_id"] is not None

        members = await client.get("/api/v1/admin/members", headers=auth_headers)
        assert members.status_code == 200
        assert any(member["email"] == invite_email for member in members.json()["members"])

    @pytest.mark.asyncio
    async def test_org_member_invitation_revoke_and_resend_flow(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        create_org = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={
                "name": "Invite Ops Org",
                "slug": "invite-ops-org",
                "domain": "invite-ops.example.com",
            },
        )
        assert create_org.status_code == 200

        invite_email = "ops-member@example.com"
        invite = await client.post(
            "/api/v1/admin/members/invite",
            headers=auth_headers,
            json={
                "email": invite_email,
                "role": "member",
                "expires_in_days": 5,
            },
        )
        assert invite.status_code == 201
        invite_payload = invite.json()
        assert invite_payload["sla_state"] in {"healthy", "expiring"}
        assert invite_payload["invite_age_hours"] >= 0

        revoke = await client.post(
            f"/api/v1/admin/member-invitations/{invite_payload['id']}/revoke",
            headers=auth_headers,
        )
        assert revoke.status_code == 200
        assert revoke.json()["status"] == "revoked"
        assert revoke.json()["sla_state"] == "revoked"

        resend = await client.post(
            f"/api/v1/admin/member-invitations/{invite_payload['id']}/resend",
            headers=auth_headers,
            json={"expires_in_days": 9},
        )
        assert resend.status_code == 200
        resend_payload = resend.json()
        assert resend_payload["status"] == "pending"
        assert resend_payload["days_until_expiry"] >= 8
        assert resend_payload["sla_state"] in {"healthy", "expiring"}

    @pytest.mark.asyncio
    async def test_org_security_policy_flags_can_be_updated(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        create_org = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={
                "name": "Security Policy Org",
                "slug": "security-policy-org",
                "domain": "security-policy.example.com",
            },
        )
        assert create_org.status_code == 200

        initial = await client.get("/api/v1/admin/organization", headers=auth_headers)
        assert initial.status_code == 200
        initial_payload = initial.json()
        assert initial_payload["require_step_up_for_sensitive_exports"] is True
        assert initial_payload["require_step_up_for_sensitive_shares"] is True

        update = await client.patch(
            "/api/v1/admin/organization",
            headers=auth_headers,
            json={
                "require_step_up_for_sensitive_exports": False,
                "require_step_up_for_sensitive_shares": False,
            },
        )
        assert update.status_code == 200

        updated = await client.get("/api/v1/admin/organization", headers=auth_headers)
        assert updated.status_code == 200
        updated_payload = updated.json()
        assert updated_payload["require_step_up_for_sensitive_exports"] is False
        assert updated_payload["require_step_up_for_sensitive_shares"] is False
