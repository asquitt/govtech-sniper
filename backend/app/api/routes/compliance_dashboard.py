"""
Compliance dashboard routes.

Provides CMMC Level 2 readiness, NIST 800-53 overview,
data privacy practices, trust-center controls, and audit event summary.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.audit import AuditEvent
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User
from app.schemas.compliance import (
    ComplianceReadinessResponse,
    DataPrivacyInfo,
    TrustCenterEvidenceItem,
    TrustCenterPolicy,
    TrustCenterPolicyUpdate,
    TrustCenterProfile,
    TrustCenterRuntimeGuarantees,
)
from app.services.auth_service import UserAuth
from app.services.cmmc_checker import get_compliance_score, get_nist_overview
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


@router.get("/readiness", response_model=ComplianceReadinessResponse)
async def readiness_status(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Marketplace and certification readiness tracker."""
    return {
        "programs": [
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
        ],
        "last_updated": datetime.utcnow().isoformat(),
    }


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


@router.get("/trust-center/evidence-export")
async def export_trust_center_evidence(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Download trust-center policy/runtime evidence bundle as JSON."""
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
    filename = f"trust_center_evidence_{datetime.utcnow().strftime('%Y%m%d')}.json"

    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance",
            entity_id=org.id if org else None,
            action="compliance.trust_center.exported",
            event_metadata={
                "organization_id": org.id if org else None,
                "can_manage_policy": can_manage_policy,
            },
        )
    )
    await session.commit()

    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
