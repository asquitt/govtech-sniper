"""
Admin routes - Usage analytics + audit log.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.models.audit import AuditEvent
from app.models.organization import OrganizationMember
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User

from .helpers import _require_org_admin

router = APIRouter()


@router.get("/usage")
async def get_usage_analytics(
    days: int = Query(default=30, ge=7, le=90),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Organization usage analytics for the admin dashboard."""
    org, _ = await _require_org_admin(current_user, session)
    since = datetime.utcnow() - timedelta(days=days)

    # Get all org user IDs
    org_user_ids_result = await session.execute(
        select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )
    org_user_ids = list(org_user_ids_result.scalars().all())

    if not org_user_ids:
        return {
            "members": 0,
            "proposals": 0,
            "rfps": 0,
            "audit_events": 0,
            "active_users": 0,
            "by_action": [],
        }

    # Count proposals created in period
    proposals_count = (
        await session.execute(
            select(func.count()).where(
                Proposal.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                Proposal.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Count RFPs uploaded in period
    rfps_count = (
        await session.execute(
            select(func.count()).where(
                RFP.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                RFP.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Audit events count in period
    audit_count = (
        await session.execute(
            select(func.count()).where(
                AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                AuditEvent.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Active users (users with at least 1 audit event in period)
    active_users = (
        await session.execute(
            select(func.count(func.distinct(AuditEvent.user_id))).where(
                AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                AuditEvent.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Audit events by action type
    by_action_result = await session.execute(
        select(AuditEvent.action, func.count())
        .where(
            AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
            AuditEvent.created_at >= since,
        )
        .group_by(AuditEvent.action)
        .order_by(func.count().desc())
        .limit(10)
    )
    by_action = [{"action": action, "count": count} for action, count in by_action_result.all()]

    return {
        "members": len(org_user_ids),
        "proposals": proposals_count,
        "rfps": rfps_count,
        "audit_events": audit_count,
        "active_users": active_users,
        "by_action": by_action,
        "period_days": days,
    }


@router.get("/audit")
async def get_org_audit_log(
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """View audit log for the entire organization."""
    org, _ = await _require_org_admin(current_user, session)

    # Get org user IDs
    org_user_ids_result = await session.execute(
        select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == org.id,
        )
    )
    org_user_ids = list(org_user_ids_result.scalars().all())

    query = select(AuditEvent).where(
        AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
    )
    if action:
        query = query.where(AuditEvent.action == action)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)

    query = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)  # type: ignore[union-attr]
    events = (await session.execute(query)).scalars().all()

    # Resolve user emails
    user_map: dict[int, str] = {}
    if events:
        user_ids = {e.user_id for e in events if e.user_id}
        if user_ids:
            users = (
                (
                    await session.execute(select(User).where(User.id.in_(user_ids)))  # type: ignore[attr-defined]
                )
                .scalars()
                .all()
            )
            user_map = {u.id: u.email for u in users}

    return {
        "events": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "user_email": user_map.get(e.user_id, "unknown") if e.user_id else None,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "action": e.action,
                "metadata": e.event_metadata,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events),
        "offset": offset,
        "limit": limit,
    }
