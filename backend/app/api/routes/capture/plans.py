"""
Capture Plans - CRUD and stage management.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.rfp import RFP
from app.models.capture import CapturePlan
from app.schemas.capture import (
    CapturePlanCreate,
    CapturePlanUpdate,
    CapturePlanRead,
    CapturePlanListItem,
    CapturePlanListResponse,
    CaptureMatchInsight,
)
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


@router.post("/plans", response_model=CapturePlanRead)
async def create_capture_plan(
    payload: CapturePlanCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanRead:
    # Ensure RFP ownership
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
    )
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    existing_result = await session.execute(
        select(CapturePlan).where(CapturePlan.rfp_id == payload.rfp_id)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Capture plan already exists")

    plan = CapturePlan(
        rfp_id=payload.rfp_id,
        owner_id=current_user.id,
        stage=payload.stage,
        bid_decision=payload.bid_decision,
        win_probability=payload.win_probability,
        notes=payload.notes,
    )
    session.add(plan)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_plan",
        entity_id=plan.id,
        action="capture.plan_created",
        metadata={"rfp_id": plan.rfp_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="capture.plan_created",
        payload={"rfp_id": plan.rfp_id, "plan_id": plan.id},
    )
    await session.commit()
    await session.refresh(plan)

    return CapturePlanRead.model_validate(plan)


@router.get("/plans", response_model=CapturePlanListResponse)
async def list_capture_plans(
    include_rfp: bool = Query(False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanListResponse:
    result = await session.execute(
        select(CapturePlan).where(CapturePlan.owner_id == current_user.id)
    )
    plans = result.scalars().all()

    items: List[CapturePlanListItem] = []
    if include_rfp:
        rfp_result = await session.execute(
            select(RFP).where(RFP.user_id == current_user.id)
        )
        rfps = {rfp.id: rfp for rfp in rfp_result.scalars().all()}
        for plan in plans:
            rfp = rfps.get(plan.rfp_id)
            items.append(
                CapturePlanListItem(
                    **CapturePlanRead.model_validate(plan).model_dump(),
                    rfp_title=rfp.title if rfp else "Unknown",
                    rfp_agency=rfp.agency if rfp else None,
                    rfp_status=rfp.status.value if rfp else None,
                )
            )
    else:
        items = [
            CapturePlanListItem(
                **CapturePlanRead.model_validate(plan).model_dump(),
                rfp_title="",
                rfp_agency=None,
                rfp_status=None,
            )
            for plan in plans
        ]

    return CapturePlanListResponse(plans=items, total=len(items))


@router.get("/plans/{plan_id}/match-insight", response_model=CaptureMatchInsight)
async def get_match_insight(
    plan_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureMatchInsight:
    result = await session.execute(
        select(CapturePlan).where(
            CapturePlan.id == plan_id,
            CapturePlan.owner_id == current_user.id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Capture plan not found")

    rfp_result = await session.execute(
        select(RFP).where(RFP.id == plan.rfp_id, RFP.user_id == current_user.id)
    )
    rfp = rfp_result.scalar_one_or_none()

    factors = []
    if plan.win_probability is not None:
        factors.append({"factor": "win_probability", "value": plan.win_probability})
    if rfp and rfp.is_qualified is not None:
        factors.append({"factor": "qualified", "value": rfp.is_qualified})
    if rfp and rfp.response_deadline:
        days_left = (rfp.response_deadline - datetime.utcnow()).days
        factors.append({"factor": "deadline_days", "value": days_left})

    summary = (
        f"Bid decision is {plan.bid_decision.value} with win probability "
        f"{plan.win_probability if plan.win_probability is not None else 'N/A'}%."
    )

    return CaptureMatchInsight(
        plan_id=plan.id,
        rfp_id=plan.rfp_id,
        summary=summary,
        factors=factors,
    )


@router.get("/plans/{rfp_id}", response_model=CapturePlanRead)
async def get_capture_plan(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanRead:
    result = await session.execute(
        select(CapturePlan)
        .where(CapturePlan.rfp_id == rfp_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Capture plan not found")

    # Ensure ownership via RFP
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    return CapturePlanRead.model_validate(plan)


@router.patch("/plans/{plan_id}", response_model=CapturePlanRead)
async def update_capture_plan(
    plan_id: int,
    payload: CapturePlanUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapturePlanRead:
    result = await session.execute(
        select(CapturePlan).where(CapturePlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Capture plan not found")

    # Ensure ownership via RFP
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == plan.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    plan.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_plan",
        entity_id=plan.id,
        action="capture.plan_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="capture.plan_updated",
        payload={"plan_id": plan.id, "updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(plan)

    return CapturePlanRead.model_validate(plan)
