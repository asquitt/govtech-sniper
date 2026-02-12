"""
RFP Sniper - Collaboration Routes
====================================
Shared workspaces, invitations, member management, and data sharing.
"""

import csv
import secrets
from datetime import datetime, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.collaboration import (
    ComplianceDigestChannel,
    ComplianceDigestFrequency,
    GovernanceAnomalySeverity,
    ShareApprovalStatus,
    SharedDataPermission,
    SharedDataType,
    SharedWorkspace,
    WorkspaceComplianceDigestSchedule,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceRole,
)
from app.models.rfp import RFP
from app.models.user import User
from app.schemas.collaboration import (
    ComplianceDigestPreviewRead,
    ComplianceDigestScheduleRead,
    ComplianceDigestScheduleUpdate,
    ContractFeedCatalogItem,
    ContractFeedPresetItem,
    GovernanceAnomalyRead,
    InvitationCreate,
    InvitationRead,
    MemberRead,
    MemberRoleUpdate,
    PortalView,
    ShareDataCreate,
    SharedDataRead,
    ShareGovernanceSummaryRead,
    ShareGovernanceTrendPointRead,
    ShareGovernanceTrendRead,
    SharePresetApplyResponse,
    SharePresetCreate,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/collaboration", tags=["Collaboration"])


CONTRACT_FEED_CATALOG: dict[int, ContractFeedCatalogItem] = {
    1001: ContractFeedCatalogItem(
        id=1001,
        name="SAM.gov Federal Opportunities",
        source="sam.gov",
        description="Federal solicitations and notices from SAM.gov.",
    ),
    1002: ContractFeedCatalogItem(
        id=1002,
        name="GSA eBuy RFQs",
        source="gsa-ebuy",
        description="Task-order RFQs available through GSA eBuy contract vehicles.",
    ),
    1003: ContractFeedCatalogItem(
        id=1003,
        name="NASA SEWP V",
        source="sewp",
        description="IT procurement opportunities from NASA SEWP V.",
    ),
    1004: ContractFeedCatalogItem(
        id=1004,
        name="FPDS Awards Feed",
        source="fpds",
        description="Federal contract awards and modifications from FPDS.",
    ),
    1005: ContractFeedCatalogItem(
        id=1005,
        name="USAspending Awards & Spending",
        source="usaspending",
        description="Agency spending and award intelligence from USAspending.",
    ),
}

CONTRACT_FEED_PRESETS: dict[str, ContractFeedPresetItem] = {
    "federal_core": ContractFeedPresetItem(
        key="federal_core",
        name="Federal Core",
        description="Core federal opportunity feeds for active capture teams.",
        feed_ids=[1001, 1002, 1003],
    ),
    "awards_intel": ContractFeedPresetItem(
        key="awards_intel",
        name="Awards Intelligence",
        description="Award and spending intelligence feeds for partner strategy.",
        feed_ids=[1004, 1005],
    ),
    "full_spectrum": ContractFeedPresetItem(
        key="full_spectrum",
        name="Full Spectrum",
        description="All available contract feeds for broad collaboration access.",
        feed_ids=[1001, 1002, 1003, 1004, 1005],
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_workspace_or_404(
    workspace_id: int,
    session: AsyncSession,
) -> SharedWorkspace:
    ws = await session.get(SharedWorkspace, workspace_id)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws


async def _require_member_role(
    workspace_id: int,
    user_id: int,
    min_role: WorkspaceRole,
    session: AsyncSession,
) -> None:
    """Check the user is the owner or has at least `min_role`."""
    ws = await _get_workspace_or_404(workspace_id, session)
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


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------


@router.get("/workspaces", response_model=list[WorkspaceRead])
async def list_workspaces(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[WorkspaceRead]:
    """List workspaces the user owns or is a member of."""
    # Owned
    owned_q = select(SharedWorkspace).where(SharedWorkspace.owner_id == current_user.id)
    owned = (await session.execute(owned_q)).scalars().all()

    # Member
    member_q = (
        select(SharedWorkspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == SharedWorkspace.id)
        .where(WorkspaceMember.user_id == current_user.id)
    )
    membered = (await session.execute(member_q)).scalars().all()

    seen: set[int] = set()
    results: list[WorkspaceRead] = []
    for ws in [*owned, *membered]:
        if ws.id in seen:
            continue
        seen.add(ws.id)
        count = await _member_count(ws.id, session)
        results.append(
            WorkspaceRead(
                id=ws.id,
                owner_id=ws.owner_id,
                rfp_id=ws.rfp_id,
                name=ws.name,
                description=ws.description,
                member_count=count,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
            )
        )
    return results


@router.post("/workspaces", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceRead:
    ws = SharedWorkspace(
        owner_id=current_user.id,
        name=payload.name,
        rfp_id=payload.rfp_id,
        description=payload.description,
    )
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    return WorkspaceRead(
        id=ws.id,
        owner_id=ws.owner_id,
        rfp_id=ws.rfp_id,
        name=ws.name,
        description=ws.description,
        member_count=0,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceRead:
    ws = await _get_workspace_or_404(workspace_id, session)
    if ws.owner_id != current_user.id:
        raise HTTPException(403, "Only the workspace owner can update it")

    if payload.name is not None:
        ws.name = payload.name
    if payload.description is not None:
        ws.description = payload.description
    ws.updated_at = datetime.utcnow()
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    count = await _member_count(ws.id, session)
    return WorkspaceRead(
        id=ws.id,
        owner_id=ws.owner_id,
        rfp_id=ws.rfp_id,
        name=ws.name,
        description=ws.description,
        member_count=count,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    ws = await _get_workspace_or_404(workspace_id, session)
    if ws.owner_id != current_user.id:
        raise HTTPException(403, "Only the workspace owner can delete it")
    await session.delete(ws)
    await session.commit()


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post("/workspaces/{workspace_id}/invite", response_model=InvitationRead, status_code=201)
async def invite_to_workspace(
    workspace_id: int,
    payload: InvitationCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvitationRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)

    token = secrets.token_urlsafe(32)
    invite = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=payload.email,
        role=WorkspaceRole(payload.role),
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return InvitationRead(
        id=invite.id,
        workspace_id=invite.workspace_id,
        email=invite.email,
        role=invite.role.value if hasattr(invite.role, "value") else invite.role,
        accept_token=invite.token,
        is_accepted=invite.is_accepted,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.get("/workspaces/{workspace_id}/invitations", response_model=list[InvitationRead])
async def list_invitations(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InvitationRead]:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    result = await session.execute(
        select(WorkspaceInvitation).where(WorkspaceInvitation.workspace_id == workspace_id)
    )
    invites = result.scalars().all()
    return [
        InvitationRead(
            id=i.id,
            workspace_id=i.workspace_id,
            email=i.email,
            role=i.role.value if hasattr(i.role, "value") else i.role,
            accept_token=i.token,
            is_accepted=i.is_accepted,
            expires_at=i.expires_at,
            created_at=i.created_at,
        )
        for i in invites
    ]


@router.post("/invitations/accept", response_model=MemberRead)
async def accept_invitation(
    token: str = Query(...),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MemberRead:
    result = await session.execute(
        select(WorkspaceInvitation).where(WorkspaceInvitation.token == token)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(404, "Invitation not found")
    if invite.is_accepted:
        raise HTTPException(400, "Invitation already accepted")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invitation has expired")
    if invite.email.lower().strip() != current_user.email.lower().strip():
        raise HTTPException(403, "Invitation email does not match authenticated user")

    workspace = await _get_workspace_or_404(invite.workspace_id, session)
    if workspace.owner_id == current_user.id:
        raise HTTPException(400, "Workspace owner already has access")

    membership_result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == invite.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    if membership_result.scalars().first():
        raise HTTPException(400, "User is already a workspace member")

    # Mark accepted
    invite.is_accepted = True
    invite.accepted_user_id = current_user.id

    # Create membership
    member = WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=current_user.id,
        role=invite.role,
    )
    session.add(invite)
    session.add(member)
    await session.commit()
    await session.refresh(member)

    # Fetch user info
    user = await session.get(User, current_user.id)
    return MemberRead(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role.value if hasattr(member.role, "value") else member.role,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        created_at=member.created_at,
    )


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/members", response_model=list[MemberRead])
async def list_members(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MemberRead]:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    result = await session.execute(
        select(WorkspaceMember, User)
        .outerjoin(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    rows = result.all()
    return [
        MemberRead(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role.value if hasattr(m.role, "value") else m.role,
            user_email=u.email if u else None,
            user_name=u.full_name if u else None,
            created_at=m.created_at,
        )
        for m, u in rows
    ]


@router.patch("/workspaces/{workspace_id}/members/{member_id}/role", response_model=MemberRead)
async def update_member_role(
    workspace_id: int,
    member_id: int,
    payload: MemberRoleUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MemberRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)

    try:
        new_role = WorkspaceRole(payload.role)
    except ValueError as exc:
        raise HTTPException(400, "Invalid workspace role") from exc

    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Member not found")

    member.role = new_role
    session.add(member)
    await session.commit()
    await session.refresh(member)

    user = await session.get(User, member.user_id)
    return MemberRead(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role.value if hasattr(member.role, "value") else member.role,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        created_at=member.created_at,
    )


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=204)
async def remove_member(
    workspace_id: int,
    member_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Member not found")
    await session.delete(member)
    await session.commit()


# ---------------------------------------------------------------------------
# Data sharing
# ---------------------------------------------------------------------------


@router.get("/contract-feeds/catalog", response_model=list[ContractFeedCatalogItem])
async def list_contract_feed_catalog(
    current_user: UserAuth = Depends(get_current_user),
) -> list[ContractFeedCatalogItem]:
    # Authenticated-only for now; catalog is used by collaboration workspaces.
    _ = current_user.id
    return list(CONTRACT_FEED_CATALOG.values())


@router.get("/contract-feeds/presets", response_model=list[ContractFeedPresetItem])
async def list_contract_feed_presets(
    current_user: UserAuth = Depends(get_current_user),
) -> list[ContractFeedPresetItem]:
    _ = current_user.id
    return list(CONTRACT_FEED_PRESETS.values())


@router.post("/workspaces/{workspace_id}/share", response_model=SharedDataRead, status_code=201)
async def share_data(
    workspace_id: int,
    payload: ShareDataCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedDataRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    ws = await _get_workspace_or_404(workspace_id, session)
    if (
        payload.data_type == SharedDataType.CONTRACT_FEED.value
        and payload.entity_id not in CONTRACT_FEED_CATALOG
    ):
        raise HTTPException(400, "Unknown contract feed")
    if payload.expires_at and payload.expires_at <= datetime.utcnow():
        raise HTTPException(400, "Expiration must be in the future")
    if payload.partner_user_id is not None:
        if payload.partner_user_id == ws.owner_id:
            pass
        else:
            member_result = await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == payload.partner_user_id,
                )
            )
            if not member_result.scalars().first():
                raise HTTPException(400, "Partner user must be a workspace member")
    now = datetime.utcnow()
    approval_status = (
        ShareApprovalStatus.PENDING if payload.requires_approval else ShareApprovalStatus.APPROVED
    )

    perm = SharedDataPermission(
        workspace_id=workspace_id,
        data_type=payload.data_type,
        entity_id=payload.entity_id,
        requires_approval=payload.requires_approval,
        approval_status=approval_status,
        approved_by_user_id=None if payload.requires_approval else current_user.id,
        approved_at=None if payload.requires_approval else now,
        expires_at=payload.expires_at,
        partner_user_id=payload.partner_user_id,
    )
    session.add(perm)
    await session.commit()
    await session.refresh(perm)
    return _serialize_shared_data(perm)


@router.post(
    "/workspaces/{workspace_id}/share/preset",
    response_model=SharePresetApplyResponse,
)
async def apply_contract_feed_preset(
    workspace_id: int,
    payload: SharePresetCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharePresetApplyResponse:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    preset = CONTRACT_FEED_PRESETS.get(payload.preset_key)
    if not preset:
        raise HTTPException(404, "Preset not found")

    existing_result = await session.execute(
        select(SharedDataPermission).where(
            SharedDataPermission.workspace_id == workspace_id,
            SharedDataPermission.data_type == SharedDataType.CONTRACT_FEED,
        )
    )
    existing_feed_ids = {item.entity_id for item in existing_result.scalars().all()}

    applied_count = 0
    for feed_id in preset.feed_ids:
        if feed_id in existing_feed_ids:
            continue
        session.add(
            SharedDataPermission(
                workspace_id=workspace_id,
                data_type=SharedDataType.CONTRACT_FEED,
                entity_id=feed_id,
                requires_approval=False,
                approval_status=ShareApprovalStatus.APPROVED,
                approved_by_user_id=current_user.id,
                approved_at=datetime.utcnow(),
            )
        )
        applied_count += 1

    await session.commit()

    shared_result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    shared_items = [_serialize_shared_data(item) for item in shared_result.scalars().all()]
    return SharePresetApplyResponse(
        preset_key=preset.key,
        applied_count=applied_count,
        shared_items=shared_items,
    )


@router.get("/workspaces/{workspace_id}/shared", response_model=list[SharedDataRead])
async def list_shared_data(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SharedDataRead]:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    perms = result.scalars().all()
    return [_serialize_shared_data(p) for p in perms]


@router.get(
    "/workspaces/{workspace_id}/shared/governance-summary",
    response_model=ShareGovernanceSummaryRead,
)
async def get_shared_data_governance_summary(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ShareGovernanceSummaryRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    permissions = result.scalars().all()
    return _calculate_governance_summary(workspace_id, permissions)


@router.get(
    "/workspaces/{workspace_id}/shared/governance-trends",
    response_model=ShareGovernanceTrendRead,
)
async def get_shared_data_governance_trends(
    workspace_id: int,
    days: int = Query(30, ge=7, le=90),
    sla_hours: int = Query(24, ge=1, le=168),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ShareGovernanceTrendRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    permissions = result.scalars().all()
    return _calculate_governance_trends(
        workspace_id,
        permissions,
        days=days,
        sla_hours=sla_hours,
    )


@router.get(
    "/workspaces/{workspace_id}/shared/governance-anomalies",
    response_model=list[GovernanceAnomalyRead],
)
async def get_shared_data_governance_anomalies(
    workspace_id: int,
    days: int = Query(30, ge=7, le=90),
    sla_hours: int = Query(24, ge=1, le=168),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[GovernanceAnomalyRead]:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    permissions = result.scalars().all()
    summary = _calculate_governance_summary(workspace_id, permissions)
    trends = _calculate_governance_trends(
        workspace_id,
        permissions,
        days=days,
        sla_hours=sla_hours,
    )
    return _calculate_governance_anomalies(summary, trends)


@router.get(
    "/workspaces/{workspace_id}/compliance-digest-schedule",
    response_model=ComplianceDigestScheduleRead,
)
async def get_workspace_compliance_digest_schedule(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceDigestScheduleRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    schedule = (
        await session.execute(
            select(WorkspaceComplianceDigestSchedule).where(
                WorkspaceComplianceDigestSchedule.workspace_id == workspace_id,
                WorkspaceComplianceDigestSchedule.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not schedule:
        schedule = WorkspaceComplianceDigestSchedule(
            workspace_id=workspace_id,
            user_id=current_user.id,
            frequency=ComplianceDigestFrequency.WEEKLY,
            day_of_week=1,
            hour_utc=13,
            minute_utc=0,
            channel=ComplianceDigestChannel.IN_APP,
            anomalies_only=False,
            is_enabled=True,
        )
        session.add(schedule)
        await session.commit()
        await session.refresh(schedule)
    return _serialize_digest_schedule(schedule)


@router.patch(
    "/workspaces/{workspace_id}/compliance-digest-schedule",
    response_model=ComplianceDigestScheduleRead,
)
async def update_workspace_compliance_digest_schedule(
    workspace_id: int,
    payload: ComplianceDigestScheduleUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceDigestScheduleRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    if payload.day_of_week is not None and not (0 <= payload.day_of_week <= 6):
        raise HTTPException(400, "day_of_week must be between 0 and 6")
    if payload.hour_utc < 0 or payload.hour_utc > 23:
        raise HTTPException(400, "hour_utc must be between 0 and 23")
    if payload.minute_utc < 0 or payload.minute_utc > 59:
        raise HTTPException(400, "minute_utc must be between 0 and 59")

    schedule = (
        await session.execute(
            select(WorkspaceComplianceDigestSchedule).where(
                WorkspaceComplianceDigestSchedule.workspace_id == workspace_id,
                WorkspaceComplianceDigestSchedule.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not schedule:
        schedule = WorkspaceComplianceDigestSchedule(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

    schedule.frequency = _parse_compliance_frequency(payload.frequency)
    schedule.day_of_week = payload.day_of_week
    schedule.hour_utc = payload.hour_utc
    schedule.minute_utc = payload.minute_utc
    schedule.channel = _parse_compliance_channel(payload.channel)
    schedule.anomalies_only = payload.anomalies_only
    schedule.is_enabled = payload.is_enabled
    schedule.updated_at = datetime.utcnow()
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)
    return _serialize_digest_schedule(schedule)


@router.get(
    "/workspaces/{workspace_id}/compliance-digest-preview",
    response_model=ComplianceDigestPreviewRead,
)
async def get_workspace_compliance_digest_preview(
    workspace_id: int,
    days: int = Query(30, ge=7, le=90),
    sla_hours: int = Query(24, ge=1, le=168),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceDigestPreviewRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    permissions = (
        (
            await session.execute(
                select(SharedDataPermission).where(
                    SharedDataPermission.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    )
    summary = _calculate_governance_summary(workspace_id, permissions)
    trends = _calculate_governance_trends(
        workspace_id,
        permissions,
        days=days,
        sla_hours=sla_hours,
    )
    anomalies = _calculate_governance_anomalies(summary, trends)
    schedule = await get_workspace_compliance_digest_schedule(
        workspace_id=workspace_id,
        current_user=current_user,
        session=session,
    )
    if schedule.anomalies_only:
        anomalies = [item for item in anomalies if item.code != "healthy"]

    return ComplianceDigestPreviewRead(
        workspace_id=workspace_id,
        generated_at=datetime.utcnow(),
        summary=summary,
        trends=trends,
        anomalies=anomalies,
        schedule=schedule,
    )


@router.post(
    "/workspaces/{workspace_id}/compliance-digest-send",
    response_model=ComplianceDigestPreviewRead,
)
async def send_workspace_compliance_digest(
    workspace_id: int,
    days: int = Query(30, ge=7, le=90),
    sla_hours: int = Query(24, ge=1, le=168),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceDigestPreviewRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    schedule_row = (
        await session.execute(
            select(WorkspaceComplianceDigestSchedule).where(
                WorkspaceComplianceDigestSchedule.workspace_id == workspace_id,
                WorkspaceComplianceDigestSchedule.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not schedule_row:
        schedule = await get_workspace_compliance_digest_schedule(
            workspace_id=workspace_id,
            current_user=current_user,
            session=session,
        )
        schedule_row = (
            await session.execute(
                select(WorkspaceComplianceDigestSchedule).where(
                    WorkspaceComplianceDigestSchedule.workspace_id == workspace_id,
                    WorkspaceComplianceDigestSchedule.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if not schedule_row:
            raise HTTPException(500, "Unable to create compliance digest schedule")
        _ = schedule
    if not schedule_row.is_enabled:
        raise HTTPException(400, "Compliance digest schedule is disabled")

    schedule_row.last_sent_at = datetime.utcnow()
    schedule_row.updated_at = datetime.utcnow()
    session.add(schedule_row)
    await session.commit()
    await session.refresh(schedule_row)

    permissions = (
        (
            await session.execute(
                select(SharedDataPermission).where(
                    SharedDataPermission.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    )
    summary = _calculate_governance_summary(workspace_id, permissions)
    trends = _calculate_governance_trends(
        workspace_id,
        permissions,
        days=days,
        sla_hours=sla_hours,
    )
    anomalies = _calculate_governance_anomalies(summary, trends)
    if schedule_row.anomalies_only:
        anomalies = [item for item in anomalies if item.code != "healthy"]

    return ComplianceDigestPreviewRead(
        workspace_id=workspace_id,
        generated_at=datetime.utcnow(),
        summary=summary,
        trends=trends,
        anomalies=anomalies,
        schedule=_serialize_digest_schedule(schedule_row),
    )


@router.get("/workspaces/{workspace_id}/shared/audit-export")
async def export_shared_data_audit(
    workspace_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    workspace = await _get_workspace_or_404(workspace_id, session)

    result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    permissions = result.scalars().all()

    now = datetime.utcnow()
    window_start = now - timedelta(days=days)

    user_ids = {
        user_id
        for permission in permissions
        for user_id in (permission.approved_by_user_id, permission.partner_user_id)
        if user_id is not None
    }
    users_by_id: dict[int, User] = {}
    if user_ids:
        users_result = await session.execute(select(User).where(User.id.in_(user_ids)))
        users_by_id = {user.id: user for user in users_result.scalars().all()}

    events: list[dict[str, str | int | bool | None]] = []

    def _add_event(
        permission: SharedDataPermission,
        event_type: str,
        event_time: datetime | None,
        actor_user_id: int | None = None,
    ) -> None:
        if event_time is None or event_time < window_start:
            return

        data_type = _enum_value(permission.data_type)
        partner_user = (
            users_by_id.get(permission.partner_user_id) if permission.partner_user_id else None
        )
        actor_user = users_by_id.get(actor_user_id) if actor_user_id else None
        events.append(
            {
                "workspace_id": workspace_id,
                "workspace_name": workspace.name,
                "share_id": permission.id,
                "event_type": event_type,
                "event_timestamp": event_time.isoformat(),
                "data_type": data_type,
                "entity_id": permission.entity_id,
                "label": _resolve_shared_data_label(data_type, permission.entity_id)
                or f"Entity #{permission.entity_id}",
                "approval_status": _enum_value(permission.approval_status),
                "requires_approval": permission.requires_approval,
                "actor_user_id": actor_user_id,
                "actor_email": actor_user.email if actor_user else None,
                "partner_user_id": permission.partner_user_id,
                "partner_email": partner_user.email if partner_user else None,
                "expires_at": permission.expires_at.isoformat() if permission.expires_at else None,
                "is_expired": bool(permission.expires_at and permission.expires_at <= now),
            }
        )

    for permission in permissions:
        _add_event(permission, "shared", permission.created_at)
        if permission.approved_at:
            _add_event(
                permission,
                "approved",
                permission.approved_at,
                actor_user_id=permission.approved_by_user_id,
            )
        if permission.expires_at and permission.expires_at <= now:
            _add_event(permission, "expired", permission.expires_at)

    events.sort(key=lambda item: str(item["event_timestamp"]), reverse=True)

    output = StringIO()
    headers = [
        "workspace_id",
        "workspace_name",
        "share_id",
        "event_type",
        "event_timestamp",
        "data_type",
        "entity_id",
        "label",
        "approval_status",
        "requires_approval",
        "actor_user_id",
        "actor_email",
        "partner_user_id",
        "partner_email",
        "expires_at",
        "is_expired",
    ]
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(events)

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="workspace_{workspace_id}_share_audit_{now.strftime("%Y%m%d")}.csv"'
    )
    return response


@router.post("/workspaces/{workspace_id}/shared/{perm_id}/approve", response_model=SharedDataRead)
async def approve_shared_data(
    workspace_id: int,
    perm_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedDataRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    result = await session.execute(
        select(SharedDataPermission).where(
            SharedDataPermission.id == perm_id,
            SharedDataPermission.workspace_id == workspace_id,
        )
    )
    permission = result.scalar_one_or_none()
    if not permission:
        raise HTTPException(404, "Permission not found")
    if permission.approval_status == ShareApprovalStatus.REVOKED:
        raise HTTPException(400, "Revoked shares cannot be approved")
    if permission.approval_status != ShareApprovalStatus.APPROVED:
        permission.approval_status = ShareApprovalStatus.APPROVED
        permission.approved_by_user_id = current_user.id
        permission.approved_at = datetime.utcnow()
        session.add(permission)
        await session.commit()
        await session.refresh(permission)
    return _serialize_shared_data(permission)


@router.delete("/workspaces/{workspace_id}/shared/{perm_id}", status_code=204)
async def unshare_data(
    workspace_id: int,
    perm_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    result = await session.execute(
        select(SharedDataPermission).where(
            SharedDataPermission.id == perm_id,
            SharedDataPermission.workspace_id == workspace_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(404, "Permission not found")
    await session.delete(perm)
    await session.commit()


# ---------------------------------------------------------------------------
# Partner Portal (read-only view)
# ---------------------------------------------------------------------------


@router.get("/portal/{workspace_id}", response_model=PortalView)
async def partner_portal(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PortalView:
    """Read-only portal view for workspace members."""
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    ws = await _get_workspace_or_404(workspace_id, session)

    # RFP title
    rfp_title = None
    if ws.rfp_id:
        rfp = await session.get(RFP, ws.rfp_id)
        if rfp:
            rfp_title = rfp.title

    # Shared items
    perms_result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    shared_items = [
        _serialize_shared_data(p)
        for p in perms_result.scalars().all()
        if _is_portal_visible_shared_item(
            p,
            user_id=current_user.id,
            owner_id=ws.owner_id,
        )
    ]

    # Members
    members_result = await session.execute(
        select(WorkspaceMember, User)
        .outerjoin(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    members = [
        MemberRead(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role.value if hasattr(m.role, "value") else m.role,
            user_email=u.email if u else None,
            user_name=u.full_name if u else None,
            created_at=m.created_at,
        )
        for m, u in members_result.all()
    ]

    return PortalView(
        workspace_name=ws.name,
        workspace_description=ws.description,
        rfp_title=rfp_title,
        shared_items=shared_items,
        members=members,
    )


# ---------------------------------------------------------------------------
# Real-Time Presence & Section Locking (REST fallback)
# ---------------------------------------------------------------------------


@router.get("/proposals/{proposal_id}/presence")
async def get_document_presence(
    proposal_id: int,
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Get who is currently viewing/editing a proposal."""
    from app.api.routes.websocket import manager

    users = manager.get_presence(proposal_id)
    locks = [lock for lock in manager.section_locks.values()]
    return {
        "proposal_id": proposal_id,
        "users": users,
        "locks": locks,
    }


@router.post("/sections/{section_id}/lock")
async def lock_section(
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Request a lock on a proposal section for editing."""
    from app.api.routes.websocket import manager

    # Look up user name
    user = await session.get(User, current_user.id)
    user_name = user.full_name if user and user.full_name else f"User {current_user.id}"

    lock = manager.lock_section(section_id, current_user.id, user_name)
    if not lock:
        existing = manager.get_lock(section_id)
        raise HTTPException(
            409,
            detail={
                "message": "Section is already locked",
                "held_by": existing,
            },
        )
    return lock


@router.delete("/sections/{section_id}/lock", status_code=204)
async def unlock_section(
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
) -> None:
    """Release a lock on a proposal section."""
    from app.api.routes.websocket import manager

    success = manager.unlock_section(section_id, current_user.id)
    if not success:
        raise HTTPException(403, "You do not hold this lock")
