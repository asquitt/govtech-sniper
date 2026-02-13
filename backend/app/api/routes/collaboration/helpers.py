"""Collaboration helper functions."""

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.utils import get_or_404
from app.models.collaboration import (
    ComplianceDigestChannel,
    ComplianceDigestFrequency,
    GovernanceAnomalySeverity,
    ShareApprovalStatus,
    SharedDataPermission,
    SharedDataType,
    SharedWorkspace,
    WorkspaceComplianceDigestSchedule,
    WorkspaceMember,
    WorkspaceRole,
)
from app.schemas.collaboration import (
    ComplianceDigestScheduleRead,
    GovernanceAnomalyRead,
    SharedDataRead,
    ShareGovernanceSummaryRead,
    ShareGovernanceTrendPointRead,
    ShareGovernanceTrendRead,
)

from .constants import CONTRACT_FEED_CATALOG


async def _require_member_role(
    workspace_id: int,
    user_id: int,
    min_role: WorkspaceRole,
    session: AsyncSession,
) -> None:
    """Check the user is the owner or has at least `min_role`."""
    ws = await get_or_404(session, SharedWorkspace, workspace_id, "Workspace not found")
    if ws.owner_id == user_id:
        return  # Owner always has full access

    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalars().first()
    if not member:
        raise HTTPException(403, "Not a member of this workspace")

    role_order = {WorkspaceRole.VIEWER: 0, WorkspaceRole.CONTRIBUTOR: 1, WorkspaceRole.ADMIN: 2}
    if role_order.get(WorkspaceRole(member.role), 0) < role_order.get(min_role, 0):
        raise HTTPException(403, "Insufficient permissions")


async def _member_count(workspace_id: int, session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace_id)
    )
    return result.scalar_one()


def _resolve_shared_data_label(data_type: str, entity_id: int) -> str | None:
    if data_type == SharedDataType.CONTRACT_FEED.value:
        catalog_item = CONTRACT_FEED_CATALOG.get(entity_id)
        return catalog_item.name if catalog_item else f"Contract Feed #{entity_id}"
    return None


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _serialize_shared_data(permission: SharedDataPermission) -> SharedDataRead:
    data_type = _enum_value(permission.data_type)
    approval_status = _enum_value(permission.approval_status)
    return SharedDataRead(
        id=permission.id,
        workspace_id=permission.workspace_id,
        data_type=data_type,
        entity_id=permission.entity_id,
        label=_resolve_shared_data_label(data_type, permission.entity_id),
        requires_approval=permission.requires_approval,
        approval_status=approval_status,
        approved_by_user_id=permission.approved_by_user_id,
        approved_at=permission.approved_at,
        expires_at=permission.expires_at,
        partner_user_id=permission.partner_user_id,
        created_at=permission.created_at,
    )


def _is_portal_visible_shared_item(
    permission: SharedDataPermission,
    *,
    user_id: int,
    owner_id: int,
) -> bool:
    if _enum_value(permission.approval_status) != ShareApprovalStatus.APPROVED.value:
        return False
    if permission.expires_at and permission.expires_at <= datetime.utcnow():
        return False
    return not (
        permission.partner_user_id and user_id not in (permission.partner_user_id, owner_id)
    )


def _calculate_governance_summary(
    workspace_id: int,
    permissions: list[SharedDataPermission],
) -> ShareGovernanceSummaryRead:
    now = datetime.utcnow()
    next_week = now + timedelta(days=7)

    pending_approval_count = 0
    approved_count = 0
    revoked_count = 0
    expired_count = 0
    expiring_7d_count = 0
    scoped_share_count = 0
    global_share_count = 0

    for permission in permissions:
        status = _enum_value(permission.approval_status)
        if status == ShareApprovalStatus.PENDING.value:
            pending_approval_count += 1
        elif status == ShareApprovalStatus.APPROVED.value:
            approved_count += 1
        elif status == ShareApprovalStatus.REVOKED.value:
            revoked_count += 1

        if permission.partner_user_id is None:
            global_share_count += 1
        else:
            scoped_share_count += 1

        if permission.expires_at is None:
            continue
        if permission.expires_at <= now:
            expired_count += 1
            continue
        if permission.expires_at <= next_week:
            expiring_7d_count += 1

    return ShareGovernanceSummaryRead(
        workspace_id=workspace_id,
        total_shared_items=len(permissions),
        pending_approval_count=pending_approval_count,
        approved_count=approved_count,
        revoked_count=revoked_count,
        expired_count=expired_count,
        expiring_7d_count=expiring_7d_count,
        scoped_share_count=scoped_share_count,
        global_share_count=global_share_count,
    )


def _calculate_governance_trends(
    workspace_id: int,
    permissions: list[SharedDataPermission],
    *,
    days: int,
    sla_hours: int,
) -> ShareGovernanceTrendRead:
    now = datetime.utcnow()
    window_start = (now - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    sla_cutoff = now - timedelta(hours=sla_hours)

    day_buckets: dict[str, dict[str, float | int | list[float]]] = {}
    for offset in range(days):
        day = (window_start + timedelta(days=offset)).date().isoformat()
        day_buckets[day] = {
            "shared_count": 0,
            "approvals_completed_count": 0,
            "approved_within_sla_count": 0,
            "approved_after_sla_count": 0,
            "approval_durations": [],
        }

    overdue_pending_count = 0
    total_within_sla = 0
    total_after_sla = 0

    for permission in permissions:
        status = _enum_value(permission.approval_status)
        created_day = permission.created_at.date().isoformat()
        if created_day in day_buckets:
            day_buckets[created_day]["shared_count"] += 1

        if status == ShareApprovalStatus.PENDING.value and permission.created_at <= sla_cutoff:
            overdue_pending_count += 1

        if status != ShareApprovalStatus.APPROVED.value or not permission.approved_at:
            continue

        approved_day = permission.approved_at.date().isoformat()
        if approved_day not in day_buckets:
            continue

        approval_hours = max(
            (permission.approved_at - permission.created_at).total_seconds() / 3600,
            0.0,
        )
        day_buckets[approved_day]["approvals_completed_count"] += 1
        day_buckets[approved_day]["approval_durations"].append(approval_hours)

        if approval_hours <= sla_hours:
            day_buckets[approved_day]["approved_within_sla_count"] += 1
            total_within_sla += 1
        else:
            day_buckets[approved_day]["approved_after_sla_count"] += 1
            total_after_sla += 1

    total_approved = total_within_sla + total_after_sla
    sla_approval_rate = (
        round((total_within_sla / total_approved) * 100, 2) if total_approved else 0.0
    )

    points: list[ShareGovernanceTrendPointRead] = []
    for day, bucket in day_buckets.items():
        approval_durations = bucket["approval_durations"]
        average_approval_hours = (
            round(sum(approval_durations) / len(approval_durations), 2)
            if approval_durations
            else None
        )
        points.append(
            ShareGovernanceTrendPointRead(
                date=day,
                shared_count=int(bucket["shared_count"]),
                approvals_completed_count=int(bucket["approvals_completed_count"]),
                approved_within_sla_count=int(bucket["approved_within_sla_count"]),
                approved_after_sla_count=int(bucket["approved_after_sla_count"]),
                average_approval_hours=average_approval_hours,
            )
        )

    return ShareGovernanceTrendRead(
        workspace_id=workspace_id,
        days=days,
        sla_hours=sla_hours,
        overdue_pending_count=overdue_pending_count,
        sla_approval_rate=sla_approval_rate,
        points=points,
    )


def _calculate_governance_anomalies(
    summary: ShareGovernanceSummaryRead,
    trends: ShareGovernanceTrendRead,
) -> list[GovernanceAnomalyRead]:
    anomalies: list[GovernanceAnomalyRead] = []

    if summary.pending_approval_count > 0:
        anomalies.append(
            GovernanceAnomalyRead(
                code="pending_approvals",
                severity=GovernanceAnomalySeverity.WARNING.value,
                title="Pending approvals awaiting release",
                description="Shared artifacts are waiting for governance approval.",
                metric_value=float(summary.pending_approval_count),
                threshold=0.0,
                recommendation="Review pending shares and approve/revoke as appropriate.",
            )
        )

    if trends.overdue_pending_count > 0:
        anomalies.append(
            GovernanceAnomalyRead(
                code="overdue_pending",
                severity=GovernanceAnomalySeverity.CRITICAL.value,
                title="Pending approvals exceeded SLA",
                description="At least one shared artifact is pending beyond approval SLA.",
                metric_value=float(trends.overdue_pending_count),
                threshold=0.0,
                recommendation="Escalate to workspace admins and clear overdue approvals.",
            )
        )

    if summary.expired_count > 0:
        anomalies.append(
            GovernanceAnomalyRead(
                code="expired_shares",
                severity=GovernanceAnomalySeverity.CRITICAL.value,
                title="Expired shared artifacts detected",
                description="One or more shared items have passed expiration windows.",
                metric_value=float(summary.expired_count),
                threshold=0.0,
                recommendation="Remove expired artifacts and refresh if still required.",
            )
        )

    if summary.expiring_7d_count > 0:
        anomalies.append(
            GovernanceAnomalyRead(
                code="expiring_soon",
                severity=GovernanceAnomalySeverity.WARNING.value,
                title="Shares expiring within 7 days",
                description="Upcoming expirations may disrupt partner access continuity.",
                metric_value=float(summary.expiring_7d_count),
                threshold=0.0,
                recommendation="Renew or replace expiring shared artifacts proactively.",
            )
        )

    if trends.sla_approval_rate < 80:
        anomalies.append(
            GovernanceAnomalyRead(
                code="low_sla_rate",
                severity=GovernanceAnomalySeverity.WARNING.value,
                title="SLA approval rate below target",
                description="Approval performance is below the 80% within-SLA target.",
                metric_value=float(trends.sla_approval_rate),
                threshold=80.0,
                recommendation="Tune approval ownership and reminders for faster turnaround.",
            )
        )

    if not anomalies:
        anomalies.append(
            GovernanceAnomalyRead(
                code="healthy",
                severity=GovernanceAnomalySeverity.INFO.value,
                title="No governance anomalies detected",
                description="Current workspace sharing posture is within configured thresholds.",
                metric_value=0.0,
                threshold=0.0,
                recommendation="Continue monitoring weekly compliance digest metrics.",
            )
        )

    return anomalies


def _serialize_digest_schedule(
    schedule: WorkspaceComplianceDigestSchedule,
) -> ComplianceDigestScheduleRead:
    return ComplianceDigestScheduleRead(
        workspace_id=schedule.workspace_id,
        user_id=schedule.user_id,
        frequency=_enum_value(schedule.frequency),
        day_of_week=schedule.day_of_week,
        hour_utc=schedule.hour_utc,
        minute_utc=schedule.minute_utc,
        channel=_enum_value(schedule.channel),
        anomalies_only=schedule.anomalies_only,
        is_enabled=schedule.is_enabled,
        last_sent_at=schedule.last_sent_at,
    )


def _parse_compliance_frequency(value: str) -> ComplianceDigestFrequency:
    try:
        return ComplianceDigestFrequency(value)
    except ValueError as exc:
        raise HTTPException(400, "Invalid digest frequency") from exc


def _parse_compliance_channel(value: str) -> ComplianceDigestChannel:
    try:
        return ComplianceDigestChannel(value)
    except ValueError as exc:
        raise HTTPException(400, "Invalid digest channel") from exc
