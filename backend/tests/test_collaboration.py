"""
RFP Sniper - Collaboration Tests
================================
Integration coverage for workspace, invitation, and shared-data flows.
"""

from datetime import datetime, timedelta

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.collaboration import (
    SharedDataPermission,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceRole,
)
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_user_and_headers(
    db_session: AsyncSession,
    email: str,
    full_name: str,
) -> tuple[User, dict[str, str]]:
    user = User(
        email=email,
        hashed_password=hash_password("TestPassword123!"),
        full_name=full_name,
        company_name="Test Company",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    tokens = create_token_pair(user.id, user.email, str(user.tier))
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


async def _configure_org_security_policy(
    db_session: AsyncSession,
    user_id: int,
    *,
    require_exports_step_up: bool = True,
    require_shares_step_up: bool = True,
) -> None:
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    org = None
    if user.organization_id:
        org = (
            await db_session.execute(
                select(Organization).where(Organization.id == user.organization_id)
            )
        ).scalar_one_or_none()
    if not org:
        org = Organization(
            name=f"Collab Security Org {user_id}",
            slug=f"collab-security-org-{user_id}",
            settings={},
        )
        db_session.add(org)
        await db_session.flush()
        user.organization_id = org.id
        db_session.add(user)

    settings_payload = dict(org.settings) if isinstance(org.settings, dict) else {}
    settings_payload["require_step_up_for_sensitive_exports"] = require_exports_step_up
    settings_payload["require_step_up_for_sensitive_shares"] = require_shares_step_up
    org.settings = settings_payload
    db_session.add(org)

    membership = (
        await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not membership:
        db_session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=user_id,
                role=OrgRole.OWNER,
                is_active=True,
            )
        )
    await db_session.commit()


async def _enable_mfa_for_user(
    db_session: AsyncSession,
    user_id: int,
) -> str:
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    secret = pyotp.random_base32()
    user.mfa_enabled = True
    user.mfa_secret = secret
    db_session.add(user)
    await db_session.commit()
    return secret


class TestCollaboration:
    @pytest.mark.asyncio
    async def test_workspace_invitation_and_shared_data_flow(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        create_workspace = await client.post(
            "/api/v1/collaboration/workspaces",
            headers=auth_headers,
            json={
                "name": "Capture Workspace",
                "description": "Shared artifacts for teaming",
                "rfp_id": test_rfp.id,
            },
        )
        assert create_workspace.status_code == 201
        workspace = create_workspace.json()
        workspace_id = workspace["id"]

        list_workspaces = await client.get(
            "/api/v1/collaboration/workspaces",
            headers=auth_headers,
        )
        assert list_workspaces.status_code == 200
        assert any(item["id"] == workspace_id for item in list_workspaces.json())

        contract_feed_catalog = await client.get(
            "/api/v1/collaboration/contract-feeds/catalog",
            headers=auth_headers,
        )
        assert contract_feed_catalog.status_code == 200
        catalog_items = contract_feed_catalog.json()
        assert len(catalog_items) >= 1
        contract_feed_id = catalog_items[0]["id"]
        contract_feed_name = catalog_items[0]["name"]

        presets_response = await client.get(
            "/api/v1/collaboration/contract-feeds/presets",
            headers=auth_headers,
        )
        assert presets_response.status_code == 200
        presets = presets_response.json()
        assert len(presets) >= 1
        preset_key = presets[0]["key"]

        invite = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invite",
            headers=auth_headers,
            json={"email": "partner@example.com", "role": "viewer"},
        )
        assert invite.status_code == 201
        assert invite.json()["email"] == "partner@example.com"
        assert invite.json()["accept_token"]

        invitations = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invitations",
            headers=auth_headers,
        )
        assert invitations.status_code == 200
        assert len(invitations.json()) == 1
        assert invitations.json()[0]["accept_token"]

        share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={"data_type": "rfp_summary", "entity_id": test_rfp.id},
        )
        assert share.status_code == 201
        shared_item = share.json()
        assert shared_item["entity_id"] == test_rfp.id

        contract_feed_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={"data_type": "contract_feed", "entity_id": contract_feed_id},
        )
        assert contract_feed_share.status_code == 201
        assert contract_feed_share.json()["label"] == contract_feed_name

        invalid_contract_feed_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={"data_type": "contract_feed", "entity_id": 999999},
        )
        assert invalid_contract_feed_share.status_code == 400
        assert invalid_contract_feed_share.json()["detail"] == "Unknown contract feed"

        shared = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared",
            headers=auth_headers,
        )
        assert shared.status_code == 200
        shared_payload = shared.json()
        assert len(shared_payload) == 2
        contract_feed_item = next(
            item for item in shared_payload if item["data_type"] == "contract_feed"
        )
        assert contract_feed_item["label"] == contract_feed_name

        apply_preset = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share/preset",
            headers=auth_headers,
            json={"preset_key": preset_key},
        )
        assert apply_preset.status_code == 200
        assert apply_preset.json()["preset_key"] == preset_key
        assert apply_preset.json()["applied_count"] >= 0

        apply_preset_again = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share/preset",
            headers=auth_headers,
            json={"preset_key": preset_key},
        )
        assert apply_preset_again.status_code == 200
        assert apply_preset_again.json()["applied_count"] == 0

        missing_preset = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share/preset",
            headers=auth_headers,
            json={"preset_key": "missing-preset"},
        )
        assert missing_preset.status_code == 404

        portal = await client.get(
            f"/api/v1/collaboration/portal/{workspace_id}",
            headers=auth_headers,
        )
        assert portal.status_code == 200
        portal_payload = portal.json()
        assert portal_payload["workspace_name"] == "Capture Workspace"
        assert portal_payload["rfp_title"] == test_rfp.title
        portal_contract_feed = next(
            item for item in portal_payload["shared_items"] if item["data_type"] == "contract_feed"
        )
        assert portal_contract_feed["label"] == contract_feed_name

        unshare = await client.delete(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/{shared_item['id']}",
            headers=auth_headers,
        )
        assert unshare.status_code == 204

        invited_email = "workspace-admin@example.com"
        invite_member = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invite",
            headers=auth_headers,
            json={"email": invited_email, "role": "viewer"},
        )
        assert invite_member.status_code == 201

        invited_user, invited_headers = await _create_user_and_headers(
            db_session,
            email=invited_email,
            full_name="Invited Reviewer",
        )

        invite_record = (
            await db_session.execute(
                select(WorkspaceInvitation).where(
                    WorkspaceInvitation.workspace_id == workspace_id,
                    WorkspaceInvitation.email == invited_email,
                )
            )
        ).scalar_one()
        accept = await client.post(
            f"/api/v1/collaboration/invitations/accept?token={invite_record.token}",
            headers=invited_headers,
        )
        assert accept.status_code == 200

        viewer_invite_attempt = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invite",
            headers=invited_headers,
            json={"email": "blocked@example.com", "role": "viewer"},
        )
        assert viewer_invite_attempt.status_code == 403

        members = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/members",
            headers=auth_headers,
        )
        assert members.status_code == 200
        target_member = next(item for item in members.json() if item["user_id"] == invited_user.id)

        promote = await client.patch(
            f"/api/v1/collaboration/workspaces/{workspace_id}/members/{target_member['id']}/role",
            headers=auth_headers,
            json={"role": "admin"},
        )
        assert promote.status_code == 200
        assert promote.json()["role"] == "admin"

        admin_invite_attempt = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invite",
            headers=invited_headers,
            json={"email": "allowed-after-promotion@example.com", "role": "viewer"},
        )
        assert admin_invite_attempt.status_code == 201

    @pytest.mark.asyncio
    async def test_sensitive_share_and_audit_export_require_step_up(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _configure_org_security_policy(
            db_session,
            user.id,
            require_exports_step_up=True,
            require_shares_step_up=True,
        )
        mfa_secret = await _enable_mfa_for_user(db_session, user.id)

        test_rfp.classification = "cui"
        db_session.add(test_rfp)
        await db_session.commit()

        create_workspace = await client.post(
            "/api/v1/collaboration/workspaces",
            headers=auth_headers,
            json={"name": "Sensitive Workspace", "rfp_id": test_rfp.id},
        )
        assert create_workspace.status_code == 201
        workspace_id = create_workspace.json()["id"]

        blocked_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={
                "data_type": "compliance_matrix",
                "entity_id": 4001,
            },
        )
        assert blocked_share.status_code == 403
        assert blocked_share.headers.get("x-step-up-required") == "true"

        allowed_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={
                "data_type": "compliance_matrix",
                "entity_id": 4001,
                "step_up_code": pyotp.TOTP(mfa_secret).now(),
            },
        )
        assert allowed_share.status_code == 201

        blocked_export = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/audit-export",
            headers=auth_headers,
        )
        assert blocked_export.status_code == 403
        assert blocked_export.headers.get("x-step-up-required") == "true"

        allowed_export = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/audit-export",
            headers={**auth_headers, "X-Step-Up-Code": pyotp.TOTP(mfa_secret).now()},
        )
        assert allowed_export.status_code == 200
        assert "text/csv" in allowed_export.headers["content-type"]

    @pytest.mark.asyncio
    async def test_invitation_acceptance_requires_matching_email(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        create_workspace = await client.post(
            "/api/v1/collaboration/workspaces",
            headers=auth_headers,
            json={"name": "Security Workspace"},
        )
        assert create_workspace.status_code == 201
        workspace_id = create_workspace.json()["id"]

        invited_email = "invitee@example.com"
        invite_response = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invite",
            headers=auth_headers,
            json={"email": invited_email, "role": "viewer"},
        )
        assert invite_response.status_code == 201
        invitation_token = invite_response.json()["accept_token"]
        assert invitation_token

        _, wrong_headers = await _create_user_and_headers(
            db_session,
            email="different-user@example.com",
            full_name="Wrong Invitee",
        )
        mismatched_accept = await client.post(
            f"/api/v1/collaboration/invitations/accept?token={invitation_token}",
            headers=wrong_headers,
        )
        assert mismatched_accept.status_code == 403
        assert "does not match" in mismatched_accept.json()["detail"]

        _, invited_headers = await _create_user_and_headers(
            db_session,
            email=invited_email,
            full_name="Correct Invitee",
        )
        matched_accept = await client.post(
            f"/api/v1/collaboration/invitations/accept?token={invitation_token}",
            headers=invited_headers,
        )
        assert matched_accept.status_code == 200

    @pytest.mark.asyncio
    async def test_shared_data_governance_approval_scope_and_expiry(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        create_workspace = await client.post(
            "/api/v1/collaboration/workspaces",
            headers=auth_headers,
            json={"name": "Governance Workspace"},
        )
        assert create_workspace.status_code == 201
        workspace_id = create_workspace.json()["id"]

        partner_one_email = "partner-one@example.com"
        partner_two_email = "partner-two@example.com"

        invite_partner_one = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invite",
            headers=auth_headers,
            json={"email": partner_one_email, "role": "viewer"},
        )
        assert invite_partner_one.status_code == 201
        invite_partner_two = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/invite",
            headers=auth_headers,
            json={"email": partner_two_email, "role": "viewer"},
        )
        assert invite_partner_two.status_code == 201

        partner_one_user, partner_one_headers = await _create_user_and_headers(
            db_session,
            email=partner_one_email,
            full_name="Partner One",
        )
        partner_two_user, partner_two_headers = await _create_user_and_headers(
            db_session,
            email=partner_two_email,
            full_name="Partner Two",
        )

        invite_rows = (
            (
                await db_session.execute(
                    select(WorkspaceInvitation).where(
                        WorkspaceInvitation.workspace_id == workspace_id,
                        WorkspaceInvitation.email.in_([partner_one_email, partner_two_email]),
                    )
                )
            )
            .scalars()
            .all()
        )
        token_by_email = {row.email: row.token for row in invite_rows}

        accept_one = await client.post(
            f"/api/v1/collaboration/invitations/accept?token={token_by_email[partner_one_email]}",
            headers=partner_one_headers,
        )
        assert accept_one.status_code == 200
        accept_two = await client.post(
            f"/api/v1/collaboration/invitations/accept?token={token_by_email[partner_two_email]}",
            headers=partner_two_headers,
        )
        assert accept_two.status_code == 200

        duplicate_membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=partner_one_user.id,
            role=WorkspaceRole.VIEWER,
        )
        db_session.add(duplicate_membership)
        await db_session.commit()

        invalid_scope_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={
                "data_type": "rfp_summary",
                "entity_id": 901,
                "partner_user_id": 999_999,
            },
        )
        assert invalid_scope_share.status_code == 400

        expired_share_attempt = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={
                "data_type": "rfp_summary",
                "entity_id": 902,
                "expires_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            },
        )
        assert expired_share_attempt.status_code == 400

        pending_scoped_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={
                "data_type": "rfp_summary",
                "entity_id": 903,
                "requires_approval": True,
                "partner_user_id": partner_one_user.id,
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            },
        )
        assert pending_scoped_share.status_code == 201
        pending_payload = pending_scoped_share.json()
        assert pending_payload["approval_status"] == "pending"
        assert pending_payload["requires_approval"] is True
        assert pending_payload["partner_user_id"] == partner_one_user.id
        governance_pending = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/governance-summary",
            headers=auth_headers,
        )
        assert governance_pending.status_code == 200
        governance_pending_payload = governance_pending.json()
        assert governance_pending_payload["workspace_id"] == workspace_id
        assert governance_pending_payload["total_shared_items"] == 1
        assert governance_pending_payload["pending_approval_count"] == 1
        assert governance_pending_payload["scoped_share_count"] == 1
        assert governance_pending_payload["global_share_count"] == 0

        partner_one_pre_approval_portal = await client.get(
            f"/api/v1/collaboration/portal/{workspace_id}",
            headers=partner_one_headers,
        )
        assert partner_one_pre_approval_portal.status_code == 200
        assert pending_payload["id"] not in {
            item["id"] for item in partner_one_pre_approval_portal.json()["shared_items"]
        }

        unauthorized_approval = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/{pending_payload['id']}/approve",
            headers=partner_one_headers,
        )
        assert unauthorized_approval.status_code == 403

        approved_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/{pending_payload['id']}/approve",
            headers=auth_headers,
        )
        assert approved_share.status_code == 200
        assert approved_share.json()["approval_status"] == "approved"
        assert approved_share.json()["approved_by_user_id"] is not None
        governance_approved = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/governance-summary",
            headers=auth_headers,
        )
        assert governance_approved.status_code == 200
        governance_approved_payload = governance_approved.json()
        assert governance_approved_payload["pending_approval_count"] == 0
        assert governance_approved_payload["approved_count"] == 1

        partner_one_post_approval_portal = await client.get(
            f"/api/v1/collaboration/portal/{workspace_id}",
            headers=partner_one_headers,
        )
        assert partner_one_post_approval_portal.status_code == 200
        assert pending_payload["id"] in {
            item["id"] for item in partner_one_post_approval_portal.json()["shared_items"]
        }

        partner_two_portal = await client.get(
            f"/api/v1/collaboration/portal/{workspace_id}",
            headers=partner_two_headers,
        )
        assert partner_two_portal.status_code == 200
        assert pending_payload["id"] not in {
            item["id"] for item in partner_two_portal.json()["shared_items"]
        }

        expiring_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={
                "data_type": "forecast",
                "entity_id": 904,
                "expires_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            },
        )
        assert expiring_share.status_code == 201
        expiring_id = expiring_share.json()["id"]

        permission = await db_session.get(SharedDataPermission, expiring_id)
        assert permission is not None
        permission.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db_session.add(permission)
        await db_session.commit()

        partner_one_expired_portal = await client.get(
            f"/api/v1/collaboration/portal/{workspace_id}",
            headers=partner_one_headers,
        )
        assert partner_one_expired_portal.status_code == 200
        assert expiring_id not in {
            item["id"] for item in partner_one_expired_portal.json()["shared_items"]
        }
        governance_expired = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/governance-summary",
            headers=auth_headers,
        )
        assert governance_expired.status_code == 200
        governance_expired_payload = governance_expired.json()
        assert governance_expired_payload["total_shared_items"] == 2
        assert governance_expired_payload["expired_count"] == 1

        governance_trends = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/governance-trends",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert governance_trends.status_code == 200
        governance_trends_payload = governance_trends.json()
        assert governance_trends_payload["workspace_id"] == workspace_id
        assert governance_trends_payload["days"] == 30
        assert governance_trends_payload["sla_hours"] == 24
        assert len(governance_trends_payload["points"]) == 30
        assert governance_trends_payload["sla_approval_rate"] >= 0

        partner_export_attempt = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/audit-export",
            headers=partner_one_headers,
        )
        assert partner_export_attempt.status_code == 403

        audit_export = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/audit-export",
            headers=auth_headers,
            params={"days": 30},
        )
        assert audit_export.status_code == 200
        assert "text/csv" in audit_export.headers["content-type"]
        assert audit_export.headers.get("content-disposition")
        assert "share_id,event_type" in audit_export.text
        assert str(pending_payload["id"]) in audit_export.text
        assert "approved" in audit_export.text

    @pytest.mark.asyncio
    async def test_governance_anomalies_and_compliance_digest_schedule(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        workspace_response = await client.post(
            "/api/v1/collaboration/workspaces",
            headers=auth_headers,
            json={"name": "Digest Workspace"},
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]
        viewer_user, _ = await _create_user_and_headers(
            db_session,
            email=f"digest-viewer-{workspace_id}@example.com",
            full_name="Digest Viewer",
        )
        contributor_user, _ = await _create_user_and_headers(
            db_session,
            email=f"digest-contributor-{workspace_id}@example.com",
            full_name="Digest Contributor",
        )
        admin_user, _ = await _create_user_and_headers(
            db_session,
            email=f"digest-admin-{workspace_id}@example.com",
            full_name="Digest Admin",
        )
        db_session.add(
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=viewer_user.id,
                role=WorkspaceRole.VIEWER,
            )
        )
        # Regression coverage: invitation accept can create duplicate membership rows in dev-mode flows.
        db_session.add(
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=viewer_user.id,
                role=WorkspaceRole.VIEWER,
            )
        )
        db_session.add(
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=contributor_user.id,
                role=WorkspaceRole.CONTRIBUTOR,
            )
        )
        db_session.add(
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=admin_user.id,
                role=WorkspaceRole.ADMIN,
            )
        )
        await db_session.commit()

        pending_share = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/share",
            headers=auth_headers,
            json={
                "data_type": "rfp_summary",
                "entity_id": 1201,
                "requires_approval": True,
            },
        )
        assert pending_share.status_code == 201
        share_id = pending_share.json()["id"]

        share_row = await db_session.get(SharedDataPermission, share_id)
        assert share_row is not None
        share_row.created_at = datetime.utcnow() - timedelta(days=3)
        db_session.add(share_row)
        await db_session.commit()

        anomalies = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/shared/governance-anomalies",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert anomalies.status_code == 200
        anomaly_codes = {item["code"] for item in anomalies.json()}
        assert "pending_approvals" in anomaly_codes
        assert "overdue_pending" in anomaly_codes

        schedule = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule",
            headers=auth_headers,
        )
        assert schedule.status_code == 200
        assert schedule.json()["frequency"] == "weekly"
        assert schedule.json()["recipient_role"] == "all"
        assert schedule.json()["is_enabled"] is True

        default_preview = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-preview",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert default_preview.status_code == 200
        assert default_preview.json()["recipient_role"] == "all"
        assert default_preview.json()["recipient_count"] == 4
        assert default_preview.json()["delivery_summary"]["total_attempts"] == 0
        assert default_preview.json()["delivery_summary"]["success_count"] == 0

        update_schedule = await client.patch(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 2,
                "hour_utc": 15,
                "minute_utc": 30,
                "channel": "in_app",
                "recipient_role": "viewer",
                "anomalies_only": True,
                "is_enabled": True,
            },
        )
        assert update_schedule.status_code == 200
        assert update_schedule.json()["anomalies_only"] is True
        assert update_schedule.json()["recipient_role"] == "viewer"

        viewer_preview = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-preview",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert viewer_preview.status_code == 200
        viewer_preview_payload = viewer_preview.json()
        assert viewer_preview_payload["workspace_id"] == workspace_id
        assert viewer_preview_payload["recipient_role"] == "viewer"
        assert viewer_preview_payload["recipient_count"] == 1
        assert viewer_preview_payload["schedule"]["anomalies_only"] is True
        assert len(viewer_preview_payload["anomalies"]) >= 1
        assert all(item["code"] != "healthy" for item in viewer_preview_payload["anomalies"])

        admin_schedule = await client.patch(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 2,
                "hour_utc": 15,
                "minute_utc": 30,
                "channel": "in_app",
                "recipient_role": "admin",
                "anomalies_only": False,
                "is_enabled": True,
            },
        )
        assert admin_schedule.status_code == 200
        assert admin_schedule.json()["recipient_role"] == "admin"

        admin_preview = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-preview",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert admin_preview.status_code == 200
        admin_preview_payload = admin_preview.json()
        assert admin_preview_payload["recipient_role"] == "admin"
        assert admin_preview_payload["recipient_count"] == 2
        assert admin_preview_payload["schedule"]["anomalies_only"] is False

        invalid_schedule = await client.patch(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 2,
                "hour_utc": 15,
                "minute_utc": 30,
                "channel": "in_app",
                "recipient_role": "unknown",
                "anomalies_only": False,
                "is_enabled": True,
            },
        )
        assert invalid_schedule.status_code == 400
        assert invalid_schedule.json()["detail"] == "Invalid digest recipient role"

        send_digest = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-send",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert send_digest.status_code == 200
        send_payload = send_digest.json()
        assert send_payload["recipient_role"] == "admin"
        assert send_payload["recipient_count"] == 2
        assert send_payload["schedule"]["last_sent_at"] is not None
        assert send_payload["delivery_summary"]["total_attempts"] == 1
        assert send_payload["delivery_summary"]["success_count"] == 1
        assert send_payload["delivery_summary"]["failed_count"] == 0
        assert send_payload["delivery_summary"]["last_status"] == "success"

        initial_delivery_log = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-deliveries",
            headers=auth_headers,
            params={"limit": 10},
        )
        assert initial_delivery_log.status_code == 200
        initial_delivery_payload = initial_delivery_log.json()
        assert initial_delivery_payload["summary"]["total_attempts"] == 1
        assert initial_delivery_payload["summary"]["success_count"] == 1
        assert initial_delivery_payload["items"][0]["status"] == "success"
        assert initial_delivery_payload["items"][0]["attempt_number"] == 1
        assert initial_delivery_payload["items"][0]["retry_of_delivery_id"] is None

        contributor_memberships = (
            (
                await db_session.execute(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.user_id == contributor_user.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        for membership in contributor_memberships:
            await db_session.delete(membership)
        await db_session.commit()

        contributor_schedule = await client.patch(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 2,
                "hour_utc": 15,
                "minute_utc": 30,
                "channel": "in_app",
                "recipient_role": "contributor",
                "anomalies_only": False,
                "is_enabled": True,
            },
        )
        assert contributor_schedule.status_code == 200
        assert contributor_schedule.json()["recipient_role"] == "contributor"

        failed_send = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-send",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert failed_send.status_code == 400
        assert failed_send.json()["detail"] == "No recipients found for configured digest role"

        failed_delivery_log = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-deliveries",
            headers=auth_headers,
            params={"limit": 10},
        )
        assert failed_delivery_log.status_code == 200
        failed_delivery_payload = failed_delivery_log.json()
        assert failed_delivery_payload["summary"]["total_attempts"] == 2
        assert failed_delivery_payload["summary"]["success_count"] == 1
        assert failed_delivery_payload["summary"]["failed_count"] == 1
        assert failed_delivery_payload["summary"]["last_status"] == "failed"
        assert (
            failed_delivery_payload["summary"]["last_failure_reason"]
            == "No recipients found for configured digest role"
        )
        assert failed_delivery_payload["items"][0]["status"] == "failed"
        assert failed_delivery_payload["items"][0]["attempt_number"] == 1
        assert failed_delivery_payload["items"][0]["retry_of_delivery_id"] is None
        failed_delivery_id = failed_delivery_payload["items"][0]["id"]

        admin_retry_schedule = await client.patch(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 2,
                "hour_utc": 15,
                "minute_utc": 30,
                "channel": "in_app",
                "recipient_role": "admin",
                "anomalies_only": False,
                "is_enabled": True,
            },
        )
        assert admin_retry_schedule.status_code == 200
        assert admin_retry_schedule.json()["recipient_role"] == "admin"

        retry_send = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-send",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert retry_send.status_code == 200
        retry_send_payload = retry_send.json()
        assert retry_send_payload["delivery_summary"]["total_attempts"] == 3
        assert retry_send_payload["delivery_summary"]["success_count"] == 2
        assert retry_send_payload["delivery_summary"]["failed_count"] == 1
        assert retry_send_payload["delivery_summary"]["retry_attempt_count"] == 1
        assert retry_send_payload["delivery_summary"]["last_status"] == "success"

        retry_delivery_log = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-deliveries",
            headers=auth_headers,
            params={"limit": 10},
        )
        assert retry_delivery_log.status_code == 200
        retry_delivery_payload = retry_delivery_log.json()
        assert retry_delivery_payload["summary"]["total_attempts"] == 3
        assert retry_delivery_payload["summary"]["retry_attempt_count"] == 1
        assert retry_delivery_payload["items"][0]["status"] == "success"
        assert retry_delivery_payload["items"][0]["attempt_number"] == 2
        assert retry_delivery_payload["items"][0]["retry_of_delivery_id"] == failed_delivery_id
