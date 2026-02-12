"""
RFP Sniper - Collaboration Tests
================================
Integration coverage for workspace, invitation, and shared-data flows.
"""

from datetime import datetime, timedelta

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
        assert schedule.json()["is_enabled"] is True

        update_schedule = await client.patch(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "day_of_week": 2,
                "hour_utc": 15,
                "minute_utc": 30,
                "channel": "in_app",
                "anomalies_only": True,
                "is_enabled": True,
            },
        )
        assert update_schedule.status_code == 200
        assert update_schedule.json()["anomalies_only"] is True

        preview = await client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-preview",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert preview.status_code == 200
        preview_payload = preview.json()
        assert preview_payload["workspace_id"] == workspace_id
        assert preview_payload["schedule"]["anomalies_only"] is True
        assert len(preview_payload["anomalies"]) >= 1
        assert all(item["code"] != "healthy" for item in preview_payload["anomalies"])

        send_digest = await client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/compliance-digest-send",
            headers=auth_headers,
            params={"days": 30, "sla_hours": 24},
        )
        assert send_digest.status_code == 200
        send_payload = send_digest.json()
        assert send_payload["schedule"]["last_sent_at"] is not None
