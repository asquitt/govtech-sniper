"""
RFP Sniper - Award Intelligence Routes
======================================
CRUD for award intelligence records.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.award import AwardRecord
from app.models.rfp import RFP
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/awards", tags=["Awards"])


class AwardCreate(BaseModel):
    rfp_id: int | None = None
    notice_id: str | None = None
    solicitation_number: str | None = None
    contract_number: str | None = None
    agency: str | None = None
    awardee_name: str
    award_amount: int | None = None
    award_date: datetime | None = None
    contract_vehicle: str | None = None
    naics_code: str | None = None
    set_aside: str | None = None
    place_of_performance: str | None = None
    description: str | None = None
    source_url: str | None = None


class AwardUpdate(BaseModel):
    notice_id: str | None = None
    solicitation_number: str | None = None
    contract_number: str | None = None
    agency: str | None = None
    awardee_name: str | None = None
    award_amount: int | None = None
    award_date: datetime | None = None
    contract_vehicle: str | None = None
    naics_code: str | None = None
    set_aside: str | None = None
    place_of_performance: str | None = None
    description: str | None = None
    source_url: str | None = None


class AwardResponse(BaseModel):
    id: int
    rfp_id: int | None
    notice_id: str | None
    solicitation_number: str | None
    contract_number: str | None
    agency: str | None
    awardee_name: str
    award_amount: int | None
    award_date: datetime | None
    contract_vehicle: str | None
    naics_code: str | None
    set_aside: str | None
    place_of_performance: str | None
    description: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AwardResponse])
async def list_awards(
    rfp_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AwardResponse]:
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
