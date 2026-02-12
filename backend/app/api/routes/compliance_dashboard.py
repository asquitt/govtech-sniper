"""
Compliance dashboard routes.

Provides CMMC Level 2 readiness, NIST 800-53 overview,
data privacy practices, and audit event summary.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.audit import AuditEvent
from app.services.auth_service import UserAuth
from app.services.cmmc_checker import get_compliance_score, get_nist_overview

router = APIRouter(prefix="/compliance", tags=["Compliance"])


@router.get("/readiness")
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


@router.get("/data-privacy")
async def data_privacy(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Data handling practices summary."""
    return {
        "data_handling": [
            "All proposal data stored in encrypted PostgreSQL databases",
            "File uploads scanned and stored in isolated object storage",
            "User data processed only for proposal generation purposes",
            "No data sold or shared with third-party advertisers",
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
        ],
        "certifications": [
            "SOC 2 Type II (in progress)",
            "FedRAMP Ready (planned)",
            "CMMC Level 2 self-assessment (in progress)",
        ],
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
