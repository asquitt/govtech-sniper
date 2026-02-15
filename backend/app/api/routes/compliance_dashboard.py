"""
Compliance dashboard routes.

Provides CMMC Level 2 readiness, NIST 800-53 overview,
data privacy practices, trust-center controls, and audit event summary.
"""

import csv
import io
import json
from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.audit import AuditEvent
from app.models.compliance_registry import (
    CheckpointEvidenceStatus,
    CheckpointSignoffStatus,
    ComplianceCheckpointEvidenceLink,
    ComplianceCheckpointSignoff,
    ComplianceEvidence,
)
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User
from app.schemas.compliance import (
    ComplianceCheckpointEvidenceCreate,
    ComplianceCheckpointEvidenceRead,
    ComplianceCheckpointEvidenceUpdate,
    ComplianceCheckpointSignoffRead,
    ComplianceCheckpointSignoffWrite,
    ComplianceReadinessCheckpoint,
    ComplianceReadinessCheckpointResponse,
    ComplianceReadinessResponse,
    DataPrivacyInfo,
    GovCloudDeploymentProfile,
    GovCloudMigrationPhase,
    SOC2ControlDomainStatus,
    SOC2Milestone,
    SOC2ReadinessResponse,
    TrustCenterEvidenceItem,
    TrustCenterPolicy,
    TrustCenterPolicyUpdate,
    TrustCenterProfile,
    TrustCenterRuntimeGuarantees,
)
from app.services.auth_service import UserAuth
from app.services.cmmc_checker import get_compliance_score, get_nist_overview
from app.services.compliance_readiness_service import (
    get_checkpoint_signoff,
    list_checkpoint_evidence_snapshots,
    overlay_registry_readiness,
)
from app.services.export_signing import signed_headers
from app.services.gemini_service.core import GeminiService

router = APIRouter(prefix="/compliance", tags=["Compliance"])

_TRUST_CENTER_POLICY_DEFAULTS: dict[str, Any] = {
    "allow_ai_requirement_analysis": True,
    "allow_ai_draft_generation": True,
    "require_human_review_for_submission": True,
    "share_anonymized_product_telemetry": False,
    "retain_prompt_logs_days": 0,
    "retain_output_logs_days": 30,
}


def _readiness_programs() -> list[dict[str, Any]]:
    return [
        {
            "id": "fedramp_moderate",
            "name": "FedRAMP Moderate",
            "status": "in_progress",
            "percent_complete": 72,
            "next_milestone": "Control implementation narrative finalization",
        },
        {
            "id": "cmmc_level_2",
            "name": "CMMC Level 2",
            "status": "in_progress",
            "percent_complete": 78,
            "next_milestone": "External assessor evidence packet review",
        },
        {
            "id": "govcloud_deployment",
            "name": "GovCloud Deployment",
            "status": "in_progress",
            "percent_complete": 64,
            "next_milestone": "Boundary migration and tenant hardening validation",
        },
        {
            "id": "soc2_type_ii",
            "name": "SOC 2 Type II",
            "status": "in_progress",
            "percent_complete": 68,
            "next_milestone": "External auditor kickoff and evidence lock package",
        },
        {
            "id": "salesforce_appexchange",
            "name": "Salesforce AppExchange Listing",
            "status": "ready_for_submission",
            "percent_complete": 90,
            "next_milestone": "Submit managed package and listing metadata",
        },
        {
            "id": "microsoft_appsource",
            "name": "Microsoft AppSource Listing",
            "status": "ready_for_submission",
            "percent_complete": 88,
            "next_milestone": "Submit add-in validation package and screenshots",
        },
    ]


def _readiness_checkpoints() -> list[ComplianceReadinessCheckpoint]:
    return [
        ComplianceReadinessCheckpoint(
            checkpoint_id="fedramp_boundary_package",
            program_id="fedramp_moderate",
            title="FedRAMP SSP boundary package freeze",
            status="in_progress",
            target_date=datetime(2026, 4, 18),
            owner="Security Program Manager",
            third_party_required=False,
            evidence_items_ready=18,
            evidence_items_total=27,
        ),
        ComplianceReadinessCheckpoint(
            checkpoint_id="fedramp_3pao_readiness",
            program_id="fedramp_moderate",
            title="3PAO readiness checkpoint and assessor onboarding",
            status="scheduled",
            target_date=datetime(2026, 5, 20),
            owner="Compliance Lead",
            third_party_required=True,
            evidence_items_ready=9,
            evidence_items_total=24,
        ),
        ComplianceReadinessCheckpoint(
            checkpoint_id="cmmc_scope_validation",
            program_id="cmmc_level_2",
            title="CMMC Level 2 scope and enclave validation",
            status="completed",
            target_date=datetime(2026, 3, 10),
            owner="Security Engineering Lead",
            third_party_required=False,
            evidence_items_ready=14,
            evidence_items_total=14,
        ),
        ComplianceReadinessCheckpoint(
            checkpoint_id="cmmc_assessor_dry_run",
            program_id="cmmc_level_2",
            title="Third-party assessor dry-run and POA&M review",
            status="in_progress",
            target_date=datetime(2026, 5, 12),
            owner="Compliance Lead",
            third_party_required=True,
            evidence_items_ready=22,
            evidence_items_total=31,
        ),
        ComplianceReadinessCheckpoint(
            checkpoint_id="govcloud_tenant_attestation",
            program_id="govcloud_deployment",
            title="GovCloud tenant hardening attestation pack",
            status="in_progress",
            target_date=datetime(2026, 4, 30),
            owner="Platform Operations Lead",
            third_party_required=False,
            evidence_items_ready=11,
            evidence_items_total=19,
        ),
    ]


def _build_govcloud_profile(now: datetime) -> GovCloudDeploymentProfile:
    return GovCloudDeploymentProfile(
        program_id="govcloud_deployment",
        provider="AWS GovCloud (US)",
        status="in_progress",
        target_regions=["us-gov-west-1", "us-gov-east-1"],
        boundary_services=[
            "Amazon EKS (GovCloud)",
            "Amazon RDS PostgreSQL",
            "Amazon S3 (SSE-KMS)",
            "AWS KMS",
            "AWS WAF + Shield Advanced",
            "AWS IAM Identity Center",
        ],
        identity_federation_status="in_progress",
        network_isolation_status="validated_in_preprod",
        data_residency_status="us_government_regions_only",
        migration_phases=[
            GovCloudMigrationPhase(
                phase_id="landing_zone",
                title="Landing zone and account boundary setup",
                status="completed",
                target_date=datetime(2026, 2, 28),
                owner="Platform Operations Lead",
                exit_criteria=[
                    "Dedicated GovCloud org/account hierarchy provisioned",
                    "Baseline SCP guardrails and KMS boundaries enforced",
                ],
            ),
            GovCloudMigrationPhase(
                phase_id="identity_cutover",
                title="SSO federation and privileged access cutover",
                status="in_progress",
                target_date=datetime(2026, 4, 12),
                owner="Identity & Access Lead",
                exit_criteria=[
                    "IdP federation mapped to GovCloud IAM Identity Center",
                    "Privileged sessions covered by break-glass controls and audit logging",
                ],
            ),
            GovCloudMigrationPhase(
                phase_id="workload_migration",
                title="Production workload migration and boundary validation",
                status="scheduled",
                target_date=datetime(2026, 5, 30),
                owner="SRE Manager",
                exit_criteria=[
                    "Core API and worker services running in GovCloud",
                    "Cross-region DR replication validated",
                    "Latency/SLO baselines within 5% of commercial cloud baseline",
                ],
            ),
        ],
        updated_at=now,
    )


def _build_soc2_readiness(now: datetime) -> SOC2ReadinessResponse:
    observation_window_start = datetime(now.year, 3, 1)
    observation_window_end = datetime(now.year, 8, 31)
    if now.month >= 9:
        observation_window_start = datetime(now.year + 1, 3, 1)
        observation_window_end = datetime(now.year + 1, 8, 31)

    domains = [
        SOC2ControlDomainStatus(
            domain_id="CC1",
            domain_name="Control Environment",
            controls_total=18,
            controls_ready=13,
            percent_complete=72,
            owner="Security Program Manager",
        ),
        SOC2ControlDomainStatus(
            domain_id="CC6",
            domain_name="Logical and Physical Access",
            controls_total=16,
            controls_ready=11,
            percent_complete=69,
            owner="Identity & Access Lead",
        ),
        SOC2ControlDomainStatus(
            domain_id="CC7",
            domain_name="System Operations",
            controls_total=14,
            controls_ready=10,
            percent_complete=71,
            owner="Platform Operations Lead",
        ),
        SOC2ControlDomainStatus(
            domain_id="A1",
            domain_name="Availability",
            controls_total=9,
            controls_ready=6,
            percent_complete=67,
            owner="SRE Manager",
        ),
    ]

    milestones = [
        SOC2Milestone(
            milestone_id="scope_freeze",
            title="Audit scope and system boundary freeze",
            status="completed",
            due_date=datetime(2026, 3, 15),
            owner="Compliance Lead",
            evidence_ready=True,
            notes="Boundary narrative and asset inventory finalized.",
        ),
        SOC2Milestone(
            milestone_id="control_walkthroughs",
            title="Control owner walkthroughs and evidence mapping",
            status="in_progress",
            due_date=datetime(2026, 4, 20),
            owner="Security Program Manager",
            evidence_ready=False,
            notes="Residual gap remains on privileged access review evidence.",
        ),
        SOC2Milestone(
            milestone_id="auditor_kickoff",
            title="External auditor kickoff and PBC package lock",
            status="scheduled",
            due_date=datetime(2026, 5, 5),
            owner="Compliance Lead",
            evidence_ready=False,
            notes="Awaiting final access-review exports and vendor risk attestations.",
        ),
        SOC2Milestone(
            milestone_id="observation_window_complete",
            title="Type II observation window close",
            status="scheduled",
            due_date=observation_window_end,
            owner="Security Program Manager",
            evidence_ready=False,
            notes="Observation evidence collection in progress across all trust criteria.",
        ),
    ]

    overall = round(sum(domain.percent_complete for domain in domains) / max(len(domains), 1))
    return SOC2ReadinessResponse(
        program_id="soc2_type_ii",
        name="SOC 2 Type II",
        status="in_progress",
        audit_firm_status="engagement_letter_signed",
        observation_window_start=observation_window_start,
        observation_window_end=observation_window_end,
        overall_percent_complete=overall,
        domains=domains,
        milestones=milestones,
        updated_at=now,
    )


def _trust_center_policy_from_settings(settings_payload: Any) -> TrustCenterPolicy:
    settings_obj = settings_payload if isinstance(settings_payload, dict) else {}
    values: dict[str, Any] = {}
    for key, default in _TRUST_CENTER_POLICY_DEFAULTS.items():
        raw_value = settings_obj.get(key, default)
        if isinstance(default, bool):
            values[key] = bool(raw_value)
        else:
            values[key] = int(raw_value)
    return TrustCenterPolicy(**values)


def _merge_trust_center_policy_settings(
    current_settings: Any,
    updates: TrustCenterPolicyUpdate,
) -> dict[str, Any]:
    settings_obj: dict[str, Any] = (
        dict(current_settings) if isinstance(current_settings, dict) else {}
    )
    merged = _trust_center_policy_from_settings(settings_obj).model_dump()
    for key, value in updates.model_dump(exclude_none=True, exclude_unset=True).items():
        merged[key] = value
    settings_obj.update(merged)
    return settings_obj


def _runtime_guarantees() -> TrustCenterRuntimeGuarantees:
    runtime = GeminiService.privacy_runtime_guarantees()
    return TrustCenterRuntimeGuarantees(
        model_provider="Google Gemini API",
        processing_mode=str(runtime["processing_mode"]),
        provider_training_allowed=bool(runtime["provider_training_allowed"]),
        provider_retention_hours=int(runtime["provider_retention_hours"]),
        no_training_enforced=bool(runtime["no_training_enforced"]),
    )


def _build_trust_center_evidence(
    policy: TrustCenterPolicy,
    runtime: TrustCenterRuntimeGuarantees,
) -> list[TrustCenterEvidenceItem]:
    return [
        TrustCenterEvidenceItem(
            control="Data isolation boundary",
            status="enforced",
            detail="Customer proposal data remains logically isolated per tenant boundary.",
        ),
        TrustCenterEvidenceItem(
            control="Provider model training",
            status="enforced" if runtime.no_training_enforced else "warning",
            detail=(
                "Gemini processing runs in ephemeral no-training mode."
                if runtime.no_training_enforced
                else "Runtime policy drift detected. Provider training protections are not fully enforced."
            ),
        ),
        TrustCenterEvidenceItem(
            control="Submission human review gate",
            status="enforced" if policy.require_human_review_for_submission else "configured",
            detail=(
                "Human review confirmation is required before final submission workflows."
                if policy.require_human_review_for_submission
                else "Human review gate is disabled by org policy."
            ),
        ),
        TrustCenterEvidenceItem(
            control="Prompt log retention",
            status="enforced" if policy.retain_prompt_logs_days == 0 else "configured",
            detail=(
                "Prompt logs are disabled for retention."
                if policy.retain_prompt_logs_days == 0
                else f"Prompt logs retained for {policy.retain_prompt_logs_days} day(s)."
            ),
        ),
    ]


async def _current_user_with_org(
    current_user: UserAuth,
    session: AsyncSession,
) -> tuple[User, Organization | None, OrganizationMember | None]:
    user = (
        await session.execute(select(User).where(User.id == current_user.id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user not found")

    if not user.organization_id:
        return user, None, None

    org = (
        await session.execute(select(Organization).where(Organization.id == user.organization_id))
    ).scalar_one_or_none()
    if not org:
        return user, None, None

    member = (
        await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    return user, org, member


def _build_trust_center_profile(
    *,
    organization: Organization | None,
    can_manage_policy: bool,
) -> TrustCenterProfile:
    policy = _trust_center_policy_from_settings(organization.settings if organization else None)
    runtime = _runtime_guarantees()
    return TrustCenterProfile(
        organization_id=organization.id if organization else None,
        organization_name=organization.name if organization else None,
        can_manage_policy=can_manage_policy,
        policy=policy,
        runtime_guarantees=runtime,
        evidence=_build_trust_center_evidence(policy, runtime),
        updated_at=organization.updated_at if organization else datetime.utcnow(),
    )


def _is_org_admin(member: OrganizationMember | None) -> bool:
    return bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))


def _checkpoint_exists(checkpoint_id: str) -> bool:
    return any(checkpoint.checkpoint_id == checkpoint_id for checkpoint in _readiness_checkpoints())


def _serialize_checkpoint_evidence(
    snapshot,
    *,
    checkpoint_id: str,
) -> ComplianceCheckpointEvidenceRead:
    link = snapshot.link
    evidence = snapshot.evidence
    return ComplianceCheckpointEvidenceRead(
        link_id=link.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
        evidence_id=evidence.id,  # type: ignore[arg-type]
        title=evidence.title,
        evidence_type=evidence.evidence_type.value,
        description=evidence.description,
        file_path=evidence.file_path,
        url=evidence.url,
        collected_at=evidence.collected_at,
        expires_at=evidence.expires_at,
        status=link.status.value,  # type: ignore[arg-type]
        notes=link.notes,
        reviewer_user_id=link.reviewer_user_id,
        reviewer_notes=link.reviewer_notes,
        reviewed_at=link.reviewed_at,
        linked_at=link.created_at,
    )


def _build_trust_center_csv_payload(payload: dict[str, Any]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "key", "value"])
    writer.writerow(["meta", "generated_at", payload["generated_at"]])
    writer.writerow(["meta", "generated_by_user_id", payload["generated_by_user_id"]])
    writer.writerow(["profile", "organization_id", payload["profile"].get("organization_id")])
    writer.writerow(["profile", "organization_name", payload["profile"].get("organization_name")])
    writer.writerow(
        [
            "runtime",
            "processing_mode",
            payload["profile"]["runtime_guarantees"].get("processing_mode"),
        ]
    )
    writer.writerow(
        [
            "runtime",
            "no_training_enforced",
            payload["profile"]["runtime_guarantees"].get("no_training_enforced"),
        ]
    )
    for evidence in payload["profile"].get("evidence", []):
        writer.writerow(
            [
                "evidence",
                evidence.get("control"),
                f"{evidence.get('status')}|{evidence.get('detail')}",
            ]
        )
    return output.getvalue().encode("utf-8")


def _build_trust_center_pdf_payload(payload: dict[str, Any]) -> bytes:
    profile = payload["profile"]
    evidence_lines = "".join(
        [
            (
                f"<li><strong>{item.get('control')}:</strong> "
                f"{item.get('status')} - {item.get('detail')}</li>"
            )
            for item in profile.get("evidence", [])
        ]
    )
    html_doc = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8" />
        <style>
          body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 24px; }}
          h1 {{ font-size: 20px; margin-bottom: 8px; }}
          h2 {{ font-size: 14px; margin-top: 18px; }}
          ul {{ margin: 0; padding-left: 18px; }}
          li {{ margin-bottom: 6px; }}
          .meta {{ color: #555; font-size: 11px; }}
        </style>
      </head>
      <body>
        <h1>Trust Center Evidence Export</h1>
        <p class="meta">Generated at: {payload["generated_at"]}</p>
        <p class="meta">Organization: {profile.get("organization_name") or "N/A"}</p>
        <h2>Runtime Guarantees</h2>
        <ul>
          <li>Provider: {profile["runtime_guarantees"].get("model_provider")}</li>
          <li>Processing mode: {profile["runtime_guarantees"].get("processing_mode")}</li>
          <li>No training enforced: {profile["runtime_guarantees"].get("no_training_enforced")}</li>
        </ul>
        <h2>Evidence Controls</h2>
        <ul>{evidence_lines}</ul>
      </body>
    </html>
    """
    return html_doc.encode("utf-8")


@router.get("/readiness", response_model=ComplianceReadinessResponse)
async def readiness_status(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Marketplace and certification readiness tracker."""
    now = datetime.utcnow()
    return {
        "programs": _readiness_programs(),
        "last_updated": now.isoformat(),
    }


@router.get(
    "/readiness-checkpoints",
    response_model=ComplianceReadinessCheckpointResponse,
)
async def readiness_checkpoints(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceReadinessCheckpointResponse:
    """Execution checkpoints across FedRAMP/CMMC/GovCloud readiness tracks."""
    _user, org, _member = await _current_user_with_org(current_user, session)
    checkpoints = await overlay_registry_readiness(
        session,
        organization_id=org.id if org else None,
        checkpoints=_readiness_checkpoints(),
    )
    return ComplianceReadinessCheckpointResponse(
        checkpoints=checkpoints,
        generated_at=datetime.utcnow(),
    )


@router.get(
    "/readiness-checkpoints/{checkpoint_id}/evidence",
    response_model=list[ComplianceCheckpointEvidenceRead],
)
async def checkpoint_evidence_list(
    checkpoint_id: str,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ComplianceCheckpointEvidenceRead]:
    """List evidence linked to a readiness checkpoint for the current organization."""
    _user, org, member = await _current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not _checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    snapshots = await list_checkpoint_evidence_snapshots(
        session,
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
    )
    return [
        _serialize_checkpoint_evidence(snapshot, checkpoint_id=checkpoint_id)
        for snapshot in snapshots
    ]


@router.post(
    "/readiness-checkpoints/{checkpoint_id}/evidence",
    response_model=ComplianceCheckpointEvidenceRead,
    status_code=201,
)
async def checkpoint_evidence_create(
    checkpoint_id: str,
    payload: ComplianceCheckpointEvidenceCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointEvidenceRead:
    """Link an evidence artifact to a readiness checkpoint (org admin only)."""
    _user, org, member = await _current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not _is_org_admin(member):
        raise HTTPException(403, "Admin access required")
    if not _checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    evidence = (
        await session.execute(
            select(ComplianceEvidence).where(
                ComplianceEvidence.id == payload.evidence_id,
                ComplianceEvidence.organization_id == org.id,
            )
        )
    ).scalar_one_or_none()
    if not evidence:
        raise HTTPException(404, "Evidence not found in organization scope")

    link = ComplianceCheckpointEvidenceLink(
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
        evidence_id=payload.evidence_id,
        status=CheckpointEvidenceStatus(payload.status or CheckpointEvidenceStatus.SUBMITTED.value),
        notes=payload.notes,
        linked_by_user_id=current_user.id,
    )
    session.add(link)
    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance_checkpoint",
            entity_id=org.id,
            action="compliance.readiness_checkpoint.evidence_linked",
            event_metadata={
                "organization_id": org.id,
                "checkpoint_id": checkpoint_id,
                "evidence_id": payload.evidence_id,
                "status": link.status.value,
            },
        )
    )
    await session.commit()
    await session.refresh(link)

    return ComplianceCheckpointEvidenceRead(
        link_id=link.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
        evidence_id=evidence.id,  # type: ignore[arg-type]
        title=evidence.title,
        evidence_type=evidence.evidence_type.value,
        description=evidence.description,
        file_path=evidence.file_path,
        url=evidence.url,
        collected_at=evidence.collected_at,
        expires_at=evidence.expires_at,
        status=link.status.value,  # type: ignore[arg-type]
        notes=link.notes,
        reviewer_user_id=link.reviewer_user_id,
        reviewer_notes=link.reviewer_notes,
        reviewed_at=link.reviewed_at,
        linked_at=link.created_at,
    )


@router.patch(
    "/readiness-checkpoints/{checkpoint_id}/evidence/{link_id}",
    response_model=ComplianceCheckpointEvidenceRead,
)
async def checkpoint_evidence_update(
    checkpoint_id: str,
    link_id: int,
    payload: ComplianceCheckpointEvidenceUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointEvidenceRead:
    """Review/update checkpoint evidence status (org admin only)."""
    _user, org, member = await _current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not _is_org_admin(member):
        raise HTTPException(403, "Admin access required")
    if not _checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    link = (
        await session.execute(
            select(ComplianceCheckpointEvidenceLink).where(
                ComplianceCheckpointEvidenceLink.id == link_id,
                ComplianceCheckpointEvidenceLink.organization_id == org.id,
                ComplianceCheckpointEvidenceLink.checkpoint_id == checkpoint_id,
            )
        )
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Checkpoint evidence link not found")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "status" in updates:
        link.status = CheckpointEvidenceStatus(updates["status"])
    if "reviewer_notes" in updates:
        link.reviewer_notes = updates["reviewer_notes"]
    link.reviewer_user_id = current_user.id
    link.reviewed_at = datetime.utcnow()
    link.updated_at = datetime.utcnow()
    session.add(link)
    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance_checkpoint",
            entity_id=org.id,
            action="compliance.readiness_checkpoint.evidence_updated",
            event_metadata={
                "organization_id": org.id,
                "checkpoint_id": checkpoint_id,
                "link_id": link_id,
                "updates": updates,
            },
        )
    )
    await session.commit()

    evidence = (
        await session.execute(
            select(ComplianceEvidence).where(ComplianceEvidence.id == link.evidence_id)
        )
    ).scalar_one_or_none()
    if not evidence:
        raise HTTPException(404, "Linked evidence not found")

    return ComplianceCheckpointEvidenceRead(
        link_id=link.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
        evidence_id=evidence.id,  # type: ignore[arg-type]
        title=evidence.title,
        evidence_type=evidence.evidence_type.value,
        description=evidence.description,
        file_path=evidence.file_path,
        url=evidence.url,
        collected_at=evidence.collected_at,
        expires_at=evidence.expires_at,
        status=link.status.value,  # type: ignore[arg-type]
        notes=link.notes,
        reviewer_user_id=link.reviewer_user_id,
        reviewer_notes=link.reviewer_notes,
        reviewed_at=link.reviewed_at,
        linked_at=link.created_at,
    )


@router.get(
    "/readiness-checkpoints/{checkpoint_id}/signoff",
    response_model=ComplianceCheckpointSignoffRead,
)
async def checkpoint_signoff_get(
    checkpoint_id: str,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointSignoffRead:
    """Read assessor sign-off status for a checkpoint."""
    _user, org, member = await _current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not _checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    signoff = await get_checkpoint_signoff(
        session,
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
    )
    if not signoff:
        return ComplianceCheckpointSignoffRead(
            checkpoint_id=checkpoint_id,
            status=CheckpointSignoffStatus.PENDING.value,  # type: ignore[arg-type]
            assessor_name="Pending assessor assignment",
            assessor_org=None,
            notes=None,
            signed_by_user_id=None,
            signed_at=None,
            updated_at=datetime.utcnow(),
        )
    return ComplianceCheckpointSignoffRead(
        checkpoint_id=checkpoint_id,
        status=signoff.status.value,  # type: ignore[arg-type]
        assessor_name=signoff.assessor_name,
        assessor_org=signoff.assessor_org,
        notes=signoff.notes,
        signed_by_user_id=signoff.signed_by_user_id,
        signed_at=signoff.signed_at,
        updated_at=signoff.updated_at,
    )


@router.put(
    "/readiness-checkpoints/{checkpoint_id}/signoff",
    response_model=ComplianceCheckpointSignoffRead,
)
async def checkpoint_signoff_upsert(
    checkpoint_id: str,
    payload: ComplianceCheckpointSignoffWrite,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointSignoffRead:
    """Create/update checkpoint assessor sign-off (org admin only)."""
    _user, org, member = await _current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not _is_org_admin(member):
        raise HTTPException(403, "Admin access required")
    if not _checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    signoff = await get_checkpoint_signoff(
        session,
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
    )
    if not signoff:
        signoff = ComplianceCheckpointSignoff(
            organization_id=org.id,  # type: ignore[arg-type]
            checkpoint_id=checkpoint_id,
            status=CheckpointSignoffStatus(payload.status),
            assessor_name=payload.assessor_name,
            assessor_org=payload.assessor_org,
            notes=payload.notes,
            signed_by_user_id=current_user.id,
            signed_at=datetime.utcnow()
            if payload.status != CheckpointSignoffStatus.PENDING.value
            else None,
        )
    else:
        signoff.status = CheckpointSignoffStatus(payload.status)
        signoff.assessor_name = payload.assessor_name
        signoff.assessor_org = payload.assessor_org
        signoff.notes = payload.notes
        signoff.signed_by_user_id = current_user.id
        signoff.signed_at = (
            datetime.utcnow() if payload.status != CheckpointSignoffStatus.PENDING.value else None
        )
        signoff.updated_at = datetime.utcnow()

    session.add(signoff)
    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance_checkpoint",
            entity_id=org.id,
            action="compliance.readiness_checkpoint.signoff_updated",
            event_metadata={
                "organization_id": org.id,
                "checkpoint_id": checkpoint_id,
                "status": payload.status,
                "assessor_name": payload.assessor_name,
            },
        )
    )
    await session.commit()
    await session.refresh(signoff)

    return ComplianceCheckpointSignoffRead(
        checkpoint_id=checkpoint_id,
        status=signoff.status.value,  # type: ignore[arg-type]
        assessor_name=signoff.assessor_name,
        assessor_org=signoff.assessor_org,
        notes=signoff.notes,
        signed_by_user_id=signoff.signed_by_user_id,
        signed_at=signoff.signed_at,
        updated_at=signoff.updated_at,
    )


@router.get("/govcloud-profile", response_model=GovCloudDeploymentProfile)
async def govcloud_profile(
    current_user: UserAuth = Depends(get_current_user),
) -> GovCloudDeploymentProfile:
    """GovCloud deployment execution profile with phase-level readiness."""
    return _build_govcloud_profile(datetime.utcnow())


@router.get("/soc2-readiness", response_model=SOC2ReadinessResponse)
async def soc2_readiness(
    current_user: UserAuth = Depends(get_current_user),
) -> SOC2ReadinessResponse:
    """SOC 2 Type II execution tracker with milestone and domain-level posture."""
    return _build_soc2_readiness(datetime.utcnow())


@router.get("/three-pao-package")
async def export_three_pao_package(
    signed: bool = Query(False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Download readiness package for 3PAO onboarding and audit planning."""
    _user, org, member = await _current_user_with_org(current_user, session)
    can_manage_policy = bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))
    now = datetime.utcnow()
    try:
        trust_profile = _build_trust_center_profile(
            organization=org,
            can_manage_policy=can_manage_policy,
        )
        readiness_programs = _readiness_programs()
        checkpoints = await overlay_registry_readiness(
            session,
            organization_id=org.id if org else None,
            checkpoints=_readiness_checkpoints(),
        )
        third_party_checkpoints = [
            checkpoint for checkpoint in checkpoints if checkpoint.third_party_required
        ]
        soc2_profile = _build_soc2_readiness(now)
        govcloud = _build_govcloud_profile(now)

        payload = {
            "generated_at": now.isoformat(),
            "generated_by_user_id": current_user.id,
            "organization_id": org.id if org else None,
            "readiness_programs": readiness_programs,
            "checkpoint_summary": {
                "total": len(checkpoints),
                "third_party_required": len(third_party_checkpoints),
                "evidence_items_ready": sum(c.evidence_items_ready for c in checkpoints),
                "evidence_items_total": sum(c.evidence_items_total for c in checkpoints),
            },
            "checkpoints": [checkpoint.model_dump(mode="json") for checkpoint in checkpoints],
            "three_pao_focus_checkpoints": [
                checkpoint.model_dump(mode="json") for checkpoint in third_party_checkpoints
            ],
            "govcloud_profile": govcloud.model_dump(mode="json"),
            "soc2_profile": soc2_profile.model_dump(mode="json"),
            "trust_center": trust_profile.model_dump(mode="json"),
            "controls_in_scope": [
                "FedRAMP Moderate baseline deltas",
                "CMMC Level 2 practice evidence map",
                "GovCloud boundary and identity controls",
                "SOC 2 Type II trust criteria execution status",
            ],
        }
    except Exception as exc:
        session.add(
            AuditEvent(
                user_id=current_user.id,
                entity_type="compliance",
                entity_id=org.id if org else None,
                action="compliance.3pao_package.export_failed",
                event_metadata={
                    "organization_id": org.id if org else None,
                    "signed": signed,
                    "error": str(exc),
                },
            )
        )
        await session.commit()
        raise
    filename = f"three_pao_readiness_package_{now.strftime('%Y%m%d')}.json"

    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance",
            entity_id=org.id if org else None,
            action="compliance.3pao_package.exported",
            event_metadata={
                "organization_id": org.id if org else None,
                "third_party_checkpoints": len(third_party_checkpoints),
                "signed": signed,
            },
        )
    )
    await session.commit()

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    headers.update(
        signed_headers(
            json.dumps(payload, sort_keys=True).encode("utf-8"),
            enabled=signed,
        )
    )
    return JSONResponse(content=payload, headers=headers)


@router.get("/overview")
async def nist_overview(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """NIST 800-53 Rev 5 control family coverage summary."""
    return get_nist_overview()


@router.get("/cmmc-status")
async def cmmc_status(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """CMMC Level 2 readiness score with per-domain breakdown."""
    return get_compliance_score()


@router.get("/data-privacy", response_model=DataPrivacyInfo)
async def data_privacy(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Data handling practices summary."""
    runtime = _runtime_guarantees()
    training_clause = (
        "Gemini requests run with no-training enforcement and ephemeral processing"
        if runtime.no_training_enforced
        else "Gemini runtime policy requires remediation to restore no-training enforcement"
    )

    return {
        "data_handling": [
            "All proposal data stored in encrypted PostgreSQL databases",
            "File uploads scanned and stored in isolated object storage",
            "User data processed only for proposal generation purposes",
            "No data sold or shared with third-party advertisers",
            training_clause,
        ],
        "encryption": [
            "TLS 1.3 for all data in transit",
            "AES-256 encryption for data at rest",
            "Database connections encrypted via SSL",
            "API keys and secrets stored in encrypted vault",
        ],
        "access_controls": [
            "Role-based access control (RBAC) on all endpoints",
            "JWT-based authentication with refresh token rotation",
            "Session timeout after 30 minutes of inactivity",
            "Audit logging of all access events",
        ],
        "data_retention": [
            "Active proposal data retained for account lifetime",
            "Deleted proposals purged after 30-day grace period",
            "Audit logs retained for 7 years per NIST guidelines",
            "User accounts deletable upon request within 30 days",
            (
                "AI provider request retention declared at "
                f"{runtime.provider_retention_hours} hour(s)"
            ),
        ],
        "certifications": [
            "SOC 2 Type II (in progress)",
            "FedRAMP Ready (planned)",
            "CMMC Level 2 self-assessment (in progress)",
        ],
    }


@router.get("/trust-center", response_model=TrustCenterProfile)
async def trust_center_profile(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TrustCenterProfile:
    """Effective trust-center guarantees and editable policy controls."""
    _user, org, member = await _current_user_with_org(current_user, session)
    can_manage_policy = bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))
    return _build_trust_center_profile(
        organization=org,
        can_manage_policy=can_manage_policy,
    )


@router.patch("/trust-center", response_model=TrustCenterProfile)
async def update_trust_center_policy(
    payload: TrustCenterPolicyUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TrustCenterProfile:
    """Update org trust-center policy controls (owner/admin only)."""
    changes = payload.model_dump(exclude_none=True, exclude_unset=True)
    if not changes:
        return await trust_center_profile(
            current_user=current_user,
            session=session,
        )

    _user, org, member = await _current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(
            status_code=403,
            detail="Organization admin access required to update trust-center policy",
        )
    if member.role not in (OrgRole.OWNER, OrgRole.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    org.settings = _merge_trust_center_policy_settings(org.settings, payload)
    org.updated_at = datetime.utcnow()
    session.add(org)
    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="organization",
            entity_id=org.id,
            action="compliance.trust_policy.updated",
            event_metadata={
                "changes": changes,
                "organization_id": org.id,
            },
        )
    )
    await session.commit()
    await session.refresh(org)

    return _build_trust_center_profile(
        organization=org,
        can_manage_policy=True,
    )


@router.get("/trust-center/evidence-export", response_model=None)
async def export_trust_center_evidence(
    format: Literal["json", "csv", "pdf"] = Query("json"),
    signed: bool = Query(False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse | StreamingResponse:
    """Download trust-center policy/runtime evidence bundle."""
    _user, org, member = await _current_user_with_org(current_user, session)
    can_manage_policy = bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))
    profile = _build_trust_center_profile(
        organization=org,
        can_manage_policy=can_manage_policy,
    )

    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by_user_id": current_user.id,
        "profile": profile.model_dump(mode="json"),
    }
    filename_base = f"trust_center_evidence_{datetime.utcnow().strftime('%Y%m%d')}"
    try:
        if format == "csv":
            csv_bytes = _build_trust_center_csv_payload(payload)
            session.add(
                AuditEvent(
                    user_id=current_user.id,
                    entity_type="compliance",
                    entity_id=org.id if org else None,
                    action="compliance.trust_center.exported",
                    event_metadata={
                        "organization_id": org.id if org else None,
                        "can_manage_policy": can_manage_policy,
                        "format": format,
                        "signed": signed,
                    },
                )
            )
            await session.commit()
            headers = {
                "Content-Disposition": f'attachment; filename="{filename_base}.csv"',
            }
            headers.update(signed_headers(csv_bytes, enabled=signed))
            return StreamingResponse(
                io.BytesIO(csv_bytes),
                media_type="text/csv",
                headers=headers,
            )

        if format == "pdf":
            try:
                from weasyprint import HTML

                pdf_bytes = HTML(
                    string=_build_trust_center_pdf_payload(payload).decode("utf-8")
                ).write_pdf()
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "PDF export requires WeasyPrint runtime dependencies. "
                        "Install weasyprint and system libraries."
                    ),
                ) from exc
            session.add(
                AuditEvent(
                    user_id=current_user.id,
                    entity_type="compliance",
                    entity_id=org.id if org else None,
                    action="compliance.trust_center.exported",
                    event_metadata={
                        "organization_id": org.id if org else None,
                        "can_manage_policy": can_manage_policy,
                        "format": format,
                        "signed": signed,
                    },
                )
            )
            await session.commit()
            headers = {
                "Content-Disposition": f'attachment; filename="{filename_base}.pdf"',
            }
            headers.update(signed_headers(pdf_bytes, enabled=signed))
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers=headers,
            )

        serialized_json = json.dumps(payload, sort_keys=True).encode("utf-8")
        session.add(
            AuditEvent(
                user_id=current_user.id,
                entity_type="compliance",
                entity_id=org.id if org else None,
                action="compliance.trust_center.exported",
                event_metadata={
                    "organization_id": org.id if org else None,
                    "can_manage_policy": can_manage_policy,
                    "format": format,
                    "signed": signed,
                },
            )
        )
        await session.commit()
        headers = {
            "Content-Disposition": f'attachment; filename="{filename_base}.json"',
        }
        headers.update(signed_headers(serialized_json, enabled=signed))
        return JSONResponse(content=payload, headers=headers)
    except Exception as exc:
        session.add(
            AuditEvent(
                user_id=current_user.id,
                entity_type="compliance",
                entity_id=org.id if org else None,
                action="compliance.trust_center.export_failed",
                event_metadata={
                    "organization_id": org.id if org else None,
                    "can_manage_policy": can_manage_policy,
                    "format": format,
                    "signed": signed,
                    "error": str(exc),
                },
            )
        )
        await session.commit()
        raise


@router.get("/trust-metrics")
async def trust_metrics(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Operational trust metrics for enterprise readiness and rollout telemetry."""
    _user, org, _member = await _current_user_with_org(current_user, session)
    checkpoints = await overlay_registry_readiness(
        session,
        organization_id=org.id if org else None,
        checkpoints=_readiness_checkpoints(),
    )
    total_evidence_items = sum(checkpoint.evidence_items_total for checkpoint in checkpoints)
    ready_evidence_items = sum(checkpoint.evidence_items_ready for checkpoint in checkpoints)
    checkpoint_count = len(checkpoints)
    approved_signoffs = sum(
        1 for checkpoint in checkpoints if checkpoint.assessor_signoff_status == "approved"
    )

    metrics_window_start = datetime.utcnow() - timedelta(days=30)
    action_counts = {
        row[0]: row[1]
        for row in (
            await session.execute(
                select(AuditEvent.action, func.count())
                .where(
                    AuditEvent.user_id == current_user.id,
                    AuditEvent.created_at >= metrics_window_start,
                    AuditEvent.action.in_(
                        [
                            "compliance.trust_center.exported",
                            "compliance.3pao_package.exported",
                            "compliance.trust_center.export_failed",
                            "compliance.3pao_package.export_failed",
                            "security.step_up.challenge_succeeded",
                            "security.step_up.challenge_failed",
                        ]
                    ),
                )
                .group_by(AuditEvent.action)
            )
        ).all()
    }
    export_successes = int(action_counts.get("compliance.trust_center.exported", 0)) + int(
        action_counts.get("compliance.3pao_package.exported", 0)
    )
    export_failures = int(action_counts.get("compliance.trust_center.export_failed", 0)) + int(
        action_counts.get("compliance.3pao_package.export_failed", 0)
    )
    step_up_successes = int(action_counts.get("security.step_up.challenge_succeeded", 0))
    step_up_failures = int(action_counts.get("security.step_up.challenge_failed", 0))

    def _rate(successes: int, failures: int) -> float | None:
        total = successes + failures
        if total <= 0:
            return None
        return round((successes / total) * 100, 2)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "window_days": 30,
        "checkpoint_evidence_completeness_rate": (
            round((ready_evidence_items / total_evidence_items) * 100, 2)
            if total_evidence_items > 0
            else None
        ),
        "checkpoint_signoff_completion_rate": (
            round((approved_signoffs / checkpoint_count) * 100, 2) if checkpoint_count > 0 else None
        ),
        "trust_export_success_rate_30d": _rate(export_successes, export_failures),
        "trust_export_successes_30d": export_successes,
        "trust_export_failures_30d": export_failures,
        "step_up_challenge_success_rate_30d": _rate(step_up_successes, step_up_failures),
        "step_up_challenge_successes_30d": step_up_successes,
        "step_up_challenge_failures_30d": step_up_failures,
        # CI telemetry is tracked in pipeline systems and surfaced as null until connected.
        "trust_ci_pass_rate_30d": None,
    }


@router.get("/audit-summary")
async def audit_summary(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Recent audit events and compliance score for the current user."""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Total events for user
    total_q = (
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.user_id == current_user.id,
        )
    )
    total_events = (await session.execute(total_q)).scalar() or 0

    # Events in last 30 days
    recent_q = (
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.user_id == current_user.id,
            AuditEvent.created_at >= thirty_days_ago,
        )
    )
    events_last_30 = (await session.execute(recent_q)).scalar() or 0

    # Breakdown by action (last 30 days)
    by_type_q = (
        select(AuditEvent.action, func.count())
        .where(
            AuditEvent.user_id == current_user.id,
            AuditEvent.created_at >= thirty_days_ago,
        )
        .group_by(AuditEvent.action)
    )
    by_type_result = await session.execute(by_type_q)
    by_type = {row[0]: row[1] for row in by_type_result.all()}

    # Compliance score from CMMC checker
    cmmc = get_compliance_score()

    return {
        "total_events": total_events,
        "events_last_30_days": events_last_30,
        "by_type": by_type,
        "compliance_score": cmmc["score_percentage"],
    }
