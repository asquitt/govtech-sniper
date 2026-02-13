"""Compliance digest scheduling and preview endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.collaboration import (
    ComplianceDigestChannel,
    ComplianceDigestFrequency,
    SharedDataPermission,
    WorkspaceComplianceDigestSchedule,
    WorkspaceRole,
)
from app.schemas.collaboration import (
    ComplianceDigestPreviewRead,
    ComplianceDigestScheduleRead,
    ComplianceDigestScheduleUpdate,
)
from app.services.auth_service import UserAuth

from .helpers import (
    _calculate_governance_anomalies,
    _calculate_governance_summary,
    _calculate_governance_trends,
    _parse_compliance_channel,
    _parse_compliance_frequency,
    _require_member_role,
    _serialize_digest_schedule,
)

router = APIRouter()


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
