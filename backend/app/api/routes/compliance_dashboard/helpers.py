"""
Compliance Dashboard - Shared Helpers
=====================================
Constants, data builders, and utility functions shared across compliance sub-modules.
"""

import csv
import io
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User
from app.schemas.compliance import (
    ComplianceCheckpointEvidenceRead,
    ComplianceReadinessCheckpoint,
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
from app.services.gemini_service.core import GeminiService

_TRUST_CENTER_POLICY_DEFAULTS: dict[str, Any] = {
    "allow_ai_requirement_analysis": True,
    "allow_ai_draft_generation": True,
    "require_human_review_for_submission": True,
    "share_anonymized_product_telemetry": False,
    "retain_prompt_logs_days": 0,
    "retain_output_logs_days": 30,
}


def readiness_programs() -> list[dict[str, Any]]:
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


def readiness_checkpoints() -> list[ComplianceReadinessCheckpoint]:
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


def build_govcloud_profile(now: datetime) -> GovCloudDeploymentProfile:
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


def build_soc2_readiness(now: datetime) -> SOC2ReadinessResponse:
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


def trust_center_policy_from_settings(settings_payload: Any) -> TrustCenterPolicy:
    settings_obj = settings_payload if isinstance(settings_payload, dict) else {}
    values: dict[str, Any] = {}
    for key, default in _TRUST_CENTER_POLICY_DEFAULTS.items():
        raw_value = settings_obj.get(key, default)
        if isinstance(default, bool):
            values[key] = bool(raw_value)
        else:
            values[key] = int(raw_value)
    return TrustCenterPolicy(**values)


def merge_trust_center_policy_settings(
    current_settings: Any,
    updates: TrustCenterPolicyUpdate,
) -> dict[str, Any]:
    settings_obj: dict[str, Any] = (
        dict(current_settings) if isinstance(current_settings, dict) else {}
    )
    merged = trust_center_policy_from_settings(settings_obj).model_dump()
    for key, value in updates.model_dump(exclude_none=True, exclude_unset=True).items():
        merged[key] = value
    settings_obj.update(merged)
    return settings_obj


def runtime_guarantees() -> TrustCenterRuntimeGuarantees:
    runtime = GeminiService.privacy_runtime_guarantees()
    return TrustCenterRuntimeGuarantees(
        model_provider="Google Gemini API",
        processing_mode=str(runtime["processing_mode"]),
        provider_training_allowed=bool(runtime["provider_training_allowed"]),
        provider_retention_hours=int(runtime["provider_retention_hours"]),
        no_training_enforced=bool(runtime["no_training_enforced"]),
    )


def build_trust_center_evidence(
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


async def current_user_with_org(
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


def build_trust_center_profile(
    *,
    organization: Organization | None,
    can_manage_policy: bool,
) -> TrustCenterProfile:
    policy = trust_center_policy_from_settings(organization.settings if organization else None)
    runtime = runtime_guarantees()
    return TrustCenterProfile(
        organization_id=organization.id if organization else None,
        organization_name=organization.name if organization else None,
        can_manage_policy=can_manage_policy,
        policy=policy,
        runtime_guarantees=runtime,
        evidence=build_trust_center_evidence(policy, runtime),
        updated_at=organization.updated_at if organization else datetime.utcnow(),
    )


def is_org_admin(member: OrganizationMember | None) -> bool:
    return bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))


def checkpoint_exists(checkpoint_id: str) -> bool:
    return any(checkpoint.checkpoint_id == checkpoint_id for checkpoint in readiness_checkpoints())


def serialize_checkpoint_evidence(
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


def build_trust_center_csv_payload(payload: dict[str, Any]) -> bytes:
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


def build_trust_center_pdf_payload(payload: dict[str, Any]) -> bytes:
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
