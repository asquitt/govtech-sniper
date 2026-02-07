"""
Competitive Intelligence - Competitor tracking and bid match insights.
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
from app.models.capture import CaptureCompetitor
from app.schemas.capture import (
    CaptureCompetitorCreate,
    CaptureCompetitorUpdate,
    CaptureCompetitorRead,
)
from app.services.audit_service import log_audit_event

router = APIRouter()


@router.get("/competitors", response_model=List[CaptureCompetitorRead])
async def list_competitors(
    rfp_id: int = Query(..., ge=1),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[CaptureCompetitorRead]:
    result = await session.execute(
        select(CaptureCompetitor).where(
            CaptureCompetitor.rfp_id == rfp_id,
            CaptureCompetitor.user_id == current_user.id,
        )
    )
    competitors = result.scalars().all()
    return [CaptureCompetitorRead.model_validate(c) for c in competitors]


@router.post("/competitors", response_model=CaptureCompetitorRead)
async def create_competitor(
    payload: CaptureCompetitorCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureCompetitorRead:
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
    )
    if not rfp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFP not found")

    competitor = CaptureCompetitor(
        rfp_id=payload.rfp_id,
        user_id=current_user.id,
        name=payload.name,
        incumbent=payload.incumbent,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        notes=payload.notes,
    )
    session.add(competitor)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_competitor",
        entity_id=competitor.id,
        action="capture.competitor_created",
        metadata={"rfp_id": payload.rfp_id, "name": payload.name},
    )
    await session.commit()
    await session.refresh(competitor)

    return CaptureCompetitorRead.model_validate(competitor)


@router.patch("/competitors/{competitor_id}", response_model=CaptureCompetitorRead)
async def update_competitor(
    competitor_id: int,
    payload: CaptureCompetitorUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CaptureCompetitorRead:
    result = await session.execute(
        select(CaptureCompetitor).where(
            CaptureCompetitor.id == competitor_id,
            CaptureCompetitor.user_id == current_user.id,
        )
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(competitor, field, value)
    competitor.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_competitor",
        entity_id=competitor.id,
        action="capture.competitor_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(competitor)
    return CaptureCompetitorRead.model_validate(competitor)


@router.delete("/competitors/{competitor_id}")
async def delete_competitor(
    competitor_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(CaptureCompetitor).where(
            CaptureCompetitor.id == competitor_id,
            CaptureCompetitor.user_id == current_user.id,
        )
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="capture_competitor",
        entity_id=competitor.id,
        action="capture.competitor_deleted",
        metadata={"rfp_id": competitor.rfp_id},
    )
    await session.delete(competitor)
    await session.commit()
    return {"message": "Competitor deleted"}
