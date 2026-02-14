"""Data sharing, governance, and audit endpoints."""

import csv
from datetime import datetime, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import (
    STEP_UP_REQUIRED_HEADER,
    get_current_user,
    get_step_up_code,
    get_user_org_security_policy,
    verify_step_up_code,
)
from app.api.utils import get_or_404
from app.database import get_session
from app.models.collaboration import (
    ShareApprovalStatus,
    SharedDataPermission,
    SharedDataType,
    SharedWorkspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.models.rfp import RFP
from app.models.user import User
from app.schemas.collaboration import (
    ContractFeedCatalogItem,
    ContractFeedPresetItem,
    GovernanceAnomalyRead,
    ShareDataCreate,
    SharedDataRead,
    ShareGovernanceSummaryRead,
    ShareGovernanceTrendRead,
    SharePresetApplyResponse,
    SharePresetCreate,
)
from app.services.auth_service import UserAuth

from .constants import CONTRACT_FEED_CATALOG, CONTRACT_FEED_PRESETS
from .helpers import (
    _calculate_governance_anomalies,
    _calculate_governance_summary,
    _calculate_governance_trends,
    _enum_value,
    _require_member_role,
    _resolve_shared_data_label,
    _serialize_shared_data,
)

router = APIRouter()
_SENSITIVE_CLASSIFICATIONS = {"cui", "fci"}
_SENSITIVE_SHARE_TYPES = {
    SharedDataType.COMPLIANCE_MATRIX.value,
    SharedDataType.PROPOSAL_SECTION.value,
}


async def _workspace_has_sensitive_classification(
    workspace: SharedWorkspace,
    session: AsyncSession,
) -> bool:
    if not workspace.rfp_id:
        return False
    rfp = (
        await session.execute(select(RFP).where(RFP.id == workspace.rfp_id))
    ).scalar_one_or_none()
    return bool(rfp and (rfp.classification or "internal").lower() in _SENSITIVE_CLASSIFICATIONS)


async def _enforce_step_up(
    *,
    current_user: UserAuth,
    session: AsyncSession,
    request: Request,
    explicit_step_up_code: str | None,
    detail: str,
) -> None:
    supplied_code = get_step_up_code(request, explicit_step_up_code)
    if await verify_step_up_code(current_user.id, session, supplied_code):
        return
    raise HTTPException(
        status_code=403,
        detail=detail,
        headers={STEP_UP_REQUIRED_HEADER: "true"},
    )


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
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedDataRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    ws = await get_or_404(session, SharedWorkspace, workspace_id, "Workspace not found")
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

    org_policy = await get_user_org_security_policy(current_user.id, session)
    share_is_sensitive = (
        payload.data_type in _SENSITIVE_SHARE_TYPES
        or await _workspace_has_sensitive_classification(ws, session)
    )
    if share_is_sensitive and org_policy.get("require_step_up_for_sensitive_shares", True):
        await _enforce_step_up(
            current_user=current_user,
            session=session,
            request=request,
            explicit_step_up_code=payload.step_up_code,
            detail="Sensitive collaboration sharing requires step-up auth",
        )

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
    request: Request,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharePresetApplyResponse:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    ws = await get_or_404(session, SharedWorkspace, workspace_id, "Workspace not found")
    preset = CONTRACT_FEED_PRESETS.get(payload.preset_key)
    if not preset:
        raise HTTPException(404, "Preset not found")

    org_policy = await get_user_org_security_policy(current_user.id, session)
    if await _workspace_has_sensitive_classification(ws, session) and org_policy.get(
        "require_step_up_for_sensitive_shares", True
    ):
        await _enforce_step_up(
            current_user=current_user,
            session=session,
            request=request,
            explicit_step_up_code=payload.step_up_code,
            detail="Sensitive collaboration sharing requires step-up auth",
        )

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


@router.get("/workspaces/{workspace_id}/shared/audit-export")
async def export_shared_data_audit(
    workspace_id: int,
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    workspace = await get_or_404(session, SharedWorkspace, workspace_id, "Workspace not found")

    result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    permissions = result.scalars().all()
    org_policy = await get_user_org_security_policy(current_user.id, session)
    has_sensitive_shared_data = any(
        _enum_value(permission.data_type) in _SENSITIVE_SHARE_TYPES for permission in permissions
    )
    requires_export_step_up = org_policy.get("require_step_up_for_sensitive_exports", True) and (
        await _workspace_has_sensitive_classification(workspace, session)
        or has_sensitive_shared_data
    )
    if requires_export_step_up:
        await _enforce_step_up(
            current_user=current_user,
            session=session,
            request=request,
            explicit_step_up_code=None,
            detail="Sensitive collaboration export requires step-up auth",
        )

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
