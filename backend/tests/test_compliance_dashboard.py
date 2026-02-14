"""Integration tests for compliance dashboard and trust-center endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User


async def _set_org_membership(
    db_session: AsyncSession,
    *,
    user_id: int,
    role: OrgRole,
) -> Organization:
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()

    org = Organization(name="Trust Org", slug=f"trust-org-{user_id}")
    db_session.add(org)
    await db_session.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user_id,
        role=role,
        is_active=True,
    )
    db_session.add(member)

    user.organization_id = org.id
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(org)
    return org


class TestComplianceDashboard:
    @pytest.mark.asyncio
    async def test_readiness_endpoint_returns_programs(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/compliance/readiness", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["programs"]
        ids = {item["id"] for item in payload["programs"]}
        assert {
            "fedramp_moderate",
            "cmmc_level_2",
            "govcloud_deployment",
            "soc2_type_ii",
            "salesforce_appexchange",
            "microsoft_appsource",
        }.issubset(ids)

    @pytest.mark.asyncio
    async def test_soc2_readiness_endpoint_contract(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/compliance/soc2-readiness", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["program_id"] == "soc2_type_ii"
        assert payload["status"] == "in_progress"
        assert payload["audit_firm_status"] == "engagement_letter_signed"
        assert payload["overall_percent_complete"] >= 0
        assert payload["domains"]
        assert payload["milestones"]
        assert payload["milestones"][0]["evidence_ready"] in (True, False)

    @pytest.mark.asyncio
    async def test_readiness_checkpoints_endpoint_contract(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get(
            "/api/v1/compliance/readiness-checkpoints", headers=auth_headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["checkpoints"]
        checkpoint = payload["checkpoints"][0]
        assert checkpoint["program_id"] in {
            "fedramp_moderate",
            "cmmc_level_2",
            "govcloud_deployment",
        }
        assert checkpoint["evidence_items_total"] >= checkpoint["evidence_items_ready"]
        assert checkpoint["status"] in {"scheduled", "in_progress", "completed", "blocked"}

    @pytest.mark.asyncio
    async def test_govcloud_profile_endpoint_contract(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/compliance/govcloud-profile", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["program_id"] == "govcloud_deployment"
        assert payload["provider"] in {"AWS GovCloud (US)", "Azure Government"}
        assert payload["target_regions"]
        assert payload["migration_phases"]
        assert payload["migration_phases"][0]["exit_criteria"]

    @pytest.mark.asyncio
    async def test_trust_center_defaults_for_user_without_org(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/compliance/trust-center", headers=auth_headers)
        assert response.status_code == 200

        payload = response.json()
        assert payload["organization_id"] is None
        assert payload["can_manage_policy"] is False
        assert payload["policy"]["require_human_review_for_submission"] is True
        assert payload["runtime_guarantees"]["processing_mode"] == "ephemeral_no_training"

    @pytest.mark.asyncio
    async def test_trust_center_evidence_export_returns_attachment_and_audit_event(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        response = await client.get(
            "/api/v1/compliance/trust-center/evidence-export",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "attachment; filename=" in response.headers.get("content-disposition", "")
        payload = response.json()
        assert "profile" in payload
        assert (
            payload["profile"]["runtime_guarantees"]["processing_mode"] == "ephemeral_no_training"
        )

        audit_event = (
            await db_session.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.user_id == test_user.id,
                    AuditEvent.action == "compliance.trust_center.exported",
                )
                .order_by(AuditEvent.created_at.desc())
            )
        ).scalar_one_or_none()
        assert audit_event is not None

    @pytest.mark.asyncio
    async def test_three_pao_package_export_returns_attachment_and_audit_event(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        response = await client.get(
            "/api/v1/compliance/three-pao-package",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "attachment; filename=" in response.headers.get("content-disposition", "")
        payload = response.json()
        assert payload["readiness_programs"]
        assert payload["three_pao_focus_checkpoints"]
        assert payload["govcloud_profile"]["program_id"] == "govcloud_deployment"
        assert payload["soc2_profile"]["program_id"] == "soc2_type_ii"
        assert payload["checkpoint_summary"]["third_party_required"] >= 1

        audit_event = (
            await db_session.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.user_id == test_user.id,
                    AuditEvent.action == "compliance.3pao_package.exported",
                )
                .order_by(AuditEvent.created_at.desc())
            )
        ).scalar_one_or_none()
        assert audit_event is not None

    @pytest.mark.asyncio
    async def test_owner_can_update_trust_center_policy(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        org = await _set_org_membership(
            db_session,
            user_id=test_user.id,
            role=OrgRole.OWNER,
        )

        response = await client.patch(
            "/api/v1/compliance/trust-center",
            headers=auth_headers,
            json={
                "allow_ai_requirement_analysis": False,
                "allow_ai_draft_generation": True,
                "require_human_review_for_submission": True,
                "share_anonymized_product_telemetry": True,
                "retain_prompt_logs_days": 2,
                "retain_output_logs_days": 45,
            },
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["organization_id"] == org.id
        assert payload["can_manage_policy"] is True
        assert payload["policy"]["allow_ai_requirement_analysis"] is False
        assert payload["policy"]["share_anonymized_product_telemetry"] is True
        assert payload["policy"]["retain_prompt_logs_days"] == 2
        assert payload["policy"]["retain_output_logs_days"] == 45

        refreshed_org = (
            await db_session.execute(select(Organization).where(Organization.id == org.id))
        ).scalar_one()
        assert refreshed_org.settings["allow_ai_requirement_analysis"] is False
        assert refreshed_org.settings["retain_output_logs_days"] == 45

        audit_event = (
            await db_session.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.user_id == test_user.id,
                    AuditEvent.action == "compliance.trust_policy.updated",
                )
                .order_by(AuditEvent.created_at.desc())
            )
        ).scalar_one_or_none()
        assert audit_event is not None
        assert audit_event.event_metadata.get("organization_id") == org.id

    @pytest.mark.asyncio
    async def test_non_admin_cannot_update_trust_center_policy(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        await _set_org_membership(
            db_session,
            user_id=test_user.id,
            role=OrgRole.VIEWER,
        )

        response = await client.patch(
            "/api/v1/compliance/trust-center",
            headers=auth_headers,
            json={"retain_prompt_logs_days": 1},
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()
