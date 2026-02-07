"""
Capture timeline (Gantt) routes.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.capture import CapturePlan, CaptureActivity
from app.models.rfp import RFP
from app.schemas.capture_activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityRead,
    GanttPlanRow,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/capture/timeline", tags=["Capture Timeline"])


@router.get("/{plan_id}/activities", response_model=List[ActivityRead])
async def list_activities(
    plan_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[ActivityRead]:
    plan_result = await session.execute(
        select(CapturePlan).where(
            CapturePlan.id == plan_id,
            CapturePlan.owner_id == current_user.id,
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Capture plan not found")

    result = await session.execute(
        select(CaptureActivity)
        .where(CaptureActivity.capture_plan_id == plan_id)
        .order_by(CaptureActivity.sort_order)
    )
    activities = result.scalars().all()
    return [ActivityRead.model_validate(a) for a in activities]


@router.post("/{plan_id}/activities", response_model=ActivityRead)
async def create_activity(
    plan_id: int,
    payload: ActivityCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ActivityRead:
    plan_result = await session.execute(
        select(CapturePlan).where(
            CapturePlan.id == plan_id,
            CapturePlan.owner_id == current_user.id,
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Capture plan not found")

    activity = CaptureActivity(
        capture_plan_id=plan_id,
        title=payload.title,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_milestone=payload.is_milestone,
        status=payload.status,
        sort_order=payload.sort_order,
        depends_on_id=payload.depends_on_id,
    )
    session.add(activity)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_activity",
        entity_id=activity.id,
        action="capture.activity_created",
        metadata={"plan_id": plan_id},
    )
    await session.commit()
    await session.refresh(activity)

    return ActivityRead.model_validate(activity)


@router.patch("/{plan_id}/activities/{activity_id}", response_model=ActivityRead)
async def update_activity(
    plan_id: int,
    activity_id: int,
    payload: ActivityUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ActivityRead:
    plan_result = await session.execute(
        select(CapturePlan).where(
            CapturePlan.id == plan_id,
            CapturePlan.owner_id == current_user.id,
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Capture plan not found")

    result = await session.execute(
        select(CaptureActivity).where(
            CaptureActivity.id == activity_id,
            CaptureActivity.capture_plan_id == plan_id,
        )
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)
    activity.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_activity",
        entity_id=activity.id,
        action="capture.activity_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(activity)

    return ActivityRead.model_validate(activity)


@router.delete("/{plan_id}/activities/{activity_id}")
async def delete_activity(
    plan_id: int,
    activity_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    plan_result = await session.execute(
        select(CapturePlan).where(
            CapturePlan.id == plan_id,
            CapturePlan.owner_id == current_user.id,
        )
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Capture plan not found")

    result = await session.execute(
        select(CaptureActivity).where(
            CaptureActivity.id == activity_id,
            CaptureActivity.capture_plan_id == plan_id,
        )
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_activity",
        entity_id=activity.id,
        action="capture.activity_deleted",
        metadata={"plan_id": plan_id},
    )
    await session.delete(activity)
    await session.commit()

    return {"message": "Activity deleted"}


@router.get("/overview", response_model=List[GanttPlanRow])
async def get_timeline_overview(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[GanttPlanRow]:
    """All capture plans with their activities for the Gantt overview."""
    plans_result = await session.execute(
        select(CapturePlan, RFP)
        .join(RFP, RFP.id == CapturePlan.rfp_id)
        .where(CapturePlan.owner_id == current_user.id)
        .order_by(RFP.response_deadline.asc().nullslast())
    )
    plans = plans_result.all()

    rows: List[GanttPlanRow] = []
    for plan, rfp in plans:
        activities_result = await session.execute(
            select(CaptureActivity)
            .where(CaptureActivity.capture_plan_id == plan.id)
            .order_by(CaptureActivity.sort_order)
        )
        activities = activities_result.scalars().all()

        stage_value = plan.stage.value if hasattr(plan.stage, "value") else str(plan.stage)
        rows.append(
            GanttPlanRow(
                plan_id=plan.id,
                rfp_id=rfp.id,
                rfp_title=rfp.title,
                agency=rfp.agency,
                stage=stage_value,
                response_deadline=rfp.response_deadline,
                activities=[ActivityRead.model_validate(a) for a in activities],
            )
        )

    return rows
