"""
Compliance Dashboard - Trust Center & Overview Routes
=====================================================
Trust center profile, policy management, evidence export,
NIST/CMMC overview, data privacy, audit summary, and trust metrics.
"""

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
from app.models.organization import OrgRole
from app.schemas.compliance import (
    DataPrivacyInfo,
    TrustCenterPolicyUpdate,
    TrustCenterProfile,
)
from app.services.auth_service import UserAuth
from app.services.cmmc_checker import get_compliance_score, get_nist_overview
from app.services.compliance_readiness_service import overlay_registry_readiness
from app.services.export_signing import signed_headers

from .helpers import (
    build_trust_center_csv_payload,
    build_trust_center_pdf_payload,
    build_trust_center_profile,
    current_user_with_org,
    merge_trust_center_policy_settings,
    readiness_checkpoints,
    runtime_guarantees,
)

router = APIRouter()


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
    runtime = runtime_guarantees()
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
    _user, org, member = await current_user_with_org(current_user, session)
    can_manage_policy = bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))
    return build_trust_center_profile(
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

    _user, org, member = await current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(
            status_code=403,
            detail="Organization admin access required to update trust-center policy",
        )
    if member.role not in (OrgRole.OWNER, OrgRole.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    org.settings = merge_trust_center_policy_settings(org.settings, payload)
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

    return build_trust_center_profile(
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
    _user, org, member = await current_user_with_org(current_user, session)
    can_manage_policy = bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))
    profile = build_trust_center_profile(
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
            csv_bytes = build_trust_center_csv_payload(payload)
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
                    string=build_trust_center_pdf_payload(payload).decode("utf-8")
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
    _user, org, _member = await current_user_with_org(current_user, session)
    checkpoints = await overlay_registry_readiness(
        session,
        organization_id=org.id if org else None,
        checkpoints=readiness_checkpoints(),
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
        "trust_ci_pass_rate_30d": None,
    }


@router.get("/audit-summary")
async def audit_summary(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Recent audit events and compliance score for the current user."""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    total_q = (
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.user_id == current_user.id,
        )
    )
    total_events = (await session.execute(total_q)).scalar() or 0

    recent_q = (
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.user_id == current_user.id,
            AuditEvent.created_at >= thirty_days_ago,
        )
    )
    events_last_30 = (await session.execute(recent_q)).scalar() or 0

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

    cmmc = get_compliance_score()

    return {
        "total_events": total_events,
        "events_last_30_days": events_last_30,
        "by_type": by_type,
        "compliance_score": cmmc["score_percentage"],
    }
