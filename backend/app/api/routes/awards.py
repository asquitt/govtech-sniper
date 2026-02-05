"""
RFP Sniper - Award Intelligence Routes
======================================
CRUD for award intelligence records.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.award import AwardRecord
from app.models.rfp import RFP
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/awards", tags=["Awards"])


class AwardCreate(BaseModel):
    rfp_id: Optional[int] = None
    notice_id: Optional[str] = None
    solicitation_number: Optional[str] = None
    contract_number: Optional[str] = None
    agency: Optional[str] = None
    awardee_name: str
    award_amount: Optional[int] = None
    award_date: Optional[datetime] = None
    contract_vehicle: Optional[str] = None
    naics_code: Optional[str] = None
    set_aside: Optional[str] = None
    place_of_performance: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None


class AwardUpdate(BaseModel):
    notice_id: Optional[str] = None
    solicitation_number: Optional[str] = None
    contract_number: Optional[str] = None
    agency: Optional[str] = None
    awardee_name: Optional[str] = None
    award_amount: Optional[int] = None
    award_date: Optional[datetime] = None
    contract_vehicle: Optional[str] = None
    naics_code: Optional[str] = None
    set_aside: Optional[str] = None
    place_of_performance: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None


class AwardResponse(BaseModel):
    id: int
    rfp_id: Optional[int]
    notice_id: Optional[str]
    solicitation_number: Optional[str]
    contract_number: Optional[str]
    agency: Optional[str]
    awardee_name: str
    award_amount: Optional[int]
    award_date: Optional[datetime]
    contract_vehicle: Optional[str]
    naics_code: Optional[str]
    set_aside: Optional[str]
    place_of_performance: Optional[str]
    description: Optional[str]
    source_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[AwardResponse])
async def list_awards(
    rfp_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[AwardResponse]:
    query = select(AwardRecord).where(AwardRecord.user_id == current_user.id)
    if rfp_id:
        query = query.where(AwardRecord.rfp_id == rfp_id)
    query = query.order_by(AwardRecord.created_at.desc()).limit(limit)
    result = await session.execute(query)
    awards = result.scalars().all()
    return [AwardResponse.model_validate(award) for award in awards]


@router.post("", response_model=AwardResponse)
async def create_award(
    payload: AwardCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AwardResponse:
    if payload.rfp_id:
        rfp_result = await session.execute(
            select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
        )
        if not rfp_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="RFP not found")

    award = AwardRecord(
        user_id=current_user.id,
        **payload.model_dump(),
    )
    session.add(award)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="award",
        entity_id=award.id,
        action="award.created",
        metadata={"rfp_id": award.rfp_id, "awardee": award.awardee_name},
    )
    await session.commit()
    await session.refresh(award)

    return AwardResponse.model_validate(award)


@router.patch("/{award_id}", response_model=AwardResponse)
async def update_award(
    award_id: int,
    payload: AwardUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AwardResponse:
    result = await session.execute(
        select(AwardRecord).where(
            AwardRecord.id == award_id,
            AwardRecord.user_id == current_user.id,
        )
    )
    award = result.scalar_one_or_none()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(award, field, value)
    award.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="award",
        entity_id=award.id,
        action="award.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(award)

    return AwardResponse.model_validate(award)


@router.delete("/{award_id}")
async def delete_award(
    award_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(AwardRecord).where(
            AwardRecord.id == award_id,
            AwardRecord.user_id == current_user.id,
        )
    )
    award = result.scalar_one_or_none()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="award",
        entity_id=award.id,
        action="award.deleted",
        metadata={"awardee": award.awardee_name},
    )
    await session.delete(award)
    await session.commit()

    return {"message": "Award deleted"}
