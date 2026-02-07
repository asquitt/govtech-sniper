"""
Gate Reviews - Bid decision gate review management.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.rfp import RFP
from app.models.capture import GateReview
from app.schemas.capture import GateReviewCreate, GateReviewRead
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


@router.post("/gate-reviews", response_model=GateReviewRead)
async def create_gate_review(
    payload: GateReviewCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GateReviewRead:
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    review = GateReview(
        rfp_id=payload.rfp_id,
        reviewer_id=current_user.id,
        stage=payload.stage,
        decision=payload.decision,
        notes=payload.notes,
    )
    session.add(review)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="gate_review",
        entity_id=review.id,
        action="capture.gate_review_created",
        metadata={"rfp_id": review.rfp_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="capture.gate_review_created",
        payload={"rfp_id": review.rfp_id, "review_id": review.id},
    )
    await session.commit()
    await session.refresh(review)

    return GateReviewRead.model_validate(review)


@router.get("/gate-reviews", response_model=List[GateReviewRead])
async def list_gate_reviews(
    rfp_id: int = Query(...),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[GateReviewRead]:
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    result = await session.execute(
        select(GateReview).where(GateReview.rfp_id == rfp_id)
    )
    reviews = result.scalars().all()
    return [GateReviewRead.model_validate(r) for r in reviews]
