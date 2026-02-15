"""Integration tests for compliance dashboard and trust-center endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.compliance_registry import ComplianceEvidence, EvidenceType
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

    @pytest.mark.asyncio
    async def test_checkpoint_evidence_and_signoff_flow_updates_readiness_overlay(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        checkpoint_id = "fedramp_3pao_readiness"
        org = await _set_org_membership(
            db_session,
            user_id=test_user.id,
            role=OrgRole.OWNER,
        )

        evidence = ComplianceEvidence(
            user_id=test_user.id,
            organization_id=org.id,
            title="FedRAMP Boundary Screenshot",
            evidence_type=EvidenceType.SCREENSHOT,
            description="Boundary controls and enclave map",
        )
        db_session.add(evidence)
        await db_session.commit()
        await db_session.refresh(evidence)

        create_response = await client.post(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/evidence",
            headers=auth_headers,
            json={
                "evidence_id": evidence.id,
                "status": "submitted",
                "notes": "Initial submission",
            },
        )
        assert create_response.status_code == 201
        link_payload = create_response.json()
        assert link_payload["checkpoint_id"] == checkpoint_id
        assert link_payload["status"] == "submitted"
        link_id = link_payload["link_id"]

        list_response = await client.get(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/evidence",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        linked_items = list_response.json()
        assert linked_items
        assert linked_items[0]["link_id"] == link_id

        update_response = await client.patch(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/evidence/{link_id}",
            headers=auth_headers,
            json={"status": "accepted", "reviewer_notes": "Evidence accepted"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "accepted"
        assert update_response.json()["reviewer_notes"] == "Evidence accepted"

        signoff_before_response = await client.get(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/signoff",
            headers=auth_headers,
        )
        assert signoff_before_response.status_code == 200
        assert signoff_before_response.json()["status"] == "pending"

        signoff_update_response = await client.put(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/signoff",
            headers=auth_headers,
            json={
                "status": "approved",
                "assessor_name": "Accredited 3PAO",
                "assessor_org": "Independent Assessors LLC",
                "notes": "Ready for external review",
            },
        )
        assert signoff_update_response.status_code == 200
        signoff_payload = signoff_update_response.json()
        assert signoff_payload["status"] == "approved"
        assert signoff_payload["assessor_name"] == "Accredited 3PAO"
        assert signoff_payload["signed_by_user_id"] == test_user.id
        assert signoff_payload["signed_at"] is not None

        readiness_response = await client.get(
            "/api/v1/compliance/readiness-checkpoints",
            headers=auth_headers,
        )
        assert readiness_response.status_code == 200
        readiness_payload = readiness_response.json()
        checkpoint = next(
            item
            for item in readiness_payload["checkpoints"]
            if item["checkpoint_id"] == checkpoint_id
        )
        assert checkpoint["evidence_source"] == "registry"
        assert checkpoint["evidence_items_total"] >= 1
        assert checkpoint["evidence_items_ready"] >= 1
        assert checkpoint["evidence_last_updated_at"] is not None
        assert checkpoint["assessor_signoff_status"] == "approved"
        assert checkpoint["assessor_signoff_by"] == "Accredited 3PAO"
        assert checkpoint["assessor_signed_at"] is not None

        audit_events = (
            (
                await db_session.execute(
                    select(AuditEvent)
                    .where(
                        AuditEvent.user_id == test_user.id,
                        AuditEvent.action.in_(
                            [
                                "compliance.readiness_checkpoint.evidence_linked",
                                "compliance.readiness_checkpoint.evidence_updated",
                                "compliance.readiness_checkpoint.signoff_updated",
                            ]
                        ),
                    )
                    .order_by(AuditEvent.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        assert len(audit_events) >= 3

    @pytest.mark.asyncio
    async def test_viewer_cannot_modify_checkpoint_evidence_or_signoff(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        checkpoint_id = "fedramp_3pao_readiness"
        org = await _set_org_membership(
            db_session,
            user_id=test_user.id,
            role=OrgRole.VIEWER,
        )

        evidence = ComplianceEvidence(
            user_id=test_user.id,
            organization_id=org.id,
            title="Viewer evidence",
            evidence_type=EvidenceType.POLICY,
            description="Should not be writable by viewer for checkpoint flows",
        )
        db_session.add(evidence)
        await db_session.commit()
        await db_session.refresh(evidence)

        create_response = await client.post(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/evidence",
            headers=auth_headers,
            json={"evidence_id": evidence.id},
        )
        assert create_response.status_code == 403

        signoff_update_response = await client.put(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/signoff",
            headers=auth_headers,
            json={
                "status": "approved",
                "assessor_name": "Viewer Attempt",
            },
        )
        assert signoff_update_response.status_code == 403

        signoff_read_response = await client.get(
            f"/api/v1/compliance/readiness-checkpoints/{checkpoint_id}/signoff",
            headers=auth_headers,
        )
        assert signoff_read_response.status_code == 200
        assert signoff_read_response.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_trust_export_variants_support_signed_headers(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        json_response = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=json&signed=true",
            headers=auth_headers,
        )
        assert json_response.status_code == 200
        assert json_response.headers.get("x-trust-export-signature")
        assert json_response.json()["profile"]["runtime_guarantees"]["processing_mode"]

        csv_response = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=csv&signed=true",
            headers=auth_headers,
        )
        assert csv_response.status_code == 200
        assert "text/csv" in csv_response.headers.get("content-type", "")
        assert "attachment; filename=" in csv_response.headers.get("content-disposition", "")
        assert csv_response.headers.get("x-trust-export-signature")
        assert "section,key,value" in csv_response.text

        pdf_response = await client.get(
            "/api/v1/compliance/trust-center/evidence-export?format=pdf&signed=true",
            headers=auth_headers,
        )
        if pdf_response.status_code == 200:
            assert "application/pdf" in pdf_response.headers.get("content-type", "")
            assert pdf_response.headers.get("x-trust-export-signature")
            assert len(pdf_response.content) > 0
        else:
            assert pdf_response.status_code == 500
            assert "weasyprint" in pdf_response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_three_pao_package_signed_export_header(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get(
            "/api/v1/compliance/three-pao-package?signed=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers.get("x-trust-export-signature")

    @pytest.mark.asyncio
    async def test_trust_metrics_endpoint_reports_trust_and_step_up_rates(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        await _set_org_membership(
            db_session,
            user_id=test_user.id,
            role=OrgRole.OWNER,
        )
        db_session.add_all(
            [
                AuditEvent(
                    user_id=test_user.id,
                    entity_type="compliance",
                    action="compliance.trust_center.exported",
                    event_metadata={},
                ),
                AuditEvent(
                    user_id=test_user.id,
                    entity_type="compliance",
                    action="compliance.3pao_package.exported",
                    event_metadata={},
                ),
                AuditEvent(
                    user_id=test_user.id,
                    entity_type="compliance",
                    action="compliance.trust_center.export_failed",
                    event_metadata={"error": "missing dependency"},
                ),
                AuditEvent(
                    user_id=test_user.id,
                    entity_type="security",
                    action="security.step_up.challenge_succeeded",
                    event_metadata={"channel": "export"},
                ),
                AuditEvent(
                    user_id=test_user.id,
                    entity_type="security",
                    action="security.step_up.challenge_failed",
                    event_metadata={"channel": "export"},
                ),
            ]
        )
        await db_session.commit()

        response = await client.get("/api/v1/compliance/trust-metrics", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["window_days"] == 30
        assert payload["trust_export_successes_30d"] == 2
        assert payload["trust_export_failures_30d"] == 1
        assert payload["trust_export_success_rate_30d"] == pytest.approx(66.67, rel=1e-2)
        assert payload["step_up_challenge_successes_30d"] == 1
        assert payload["step_up_challenge_failures_30d"] == 1
        assert payload["step_up_challenge_success_rate_30d"] == pytest.approx(50.0, rel=1e-2)
        assert payload["checkpoint_evidence_completeness_rate"] is not None
        assert payload["checkpoint_signoff_completion_rate"] is not None
