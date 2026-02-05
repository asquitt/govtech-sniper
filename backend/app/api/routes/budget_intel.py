"""
RFP Sniper - Budget Intelligence Routes
=======================================
CRUD endpoints for budget intel records.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.budget_intel import BudgetIntelligence
from app.models.rfp import RFP
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/budget-intel", tags=["Budget Intelligence"])


class BudgetIntelCreate(BaseModel):
    rfp_id: Optional[int] = None
    title: str = Field(max_length=255)
    fiscal_year: Optional[int] = None
    amount: Optional[float] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None


class BudgetIntelUpdate(BaseModel):
    title: Optional[str] = None
    fiscal_year: Optional[int] = None
    amount: Optional[float] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None


class BudgetIntelRead(BaseModel):
    id: int
    rfp_id: Optional[int]
    title: str
    fiscal_year: Optional[int]
    amount: Optional[float]
    source_url: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[BudgetIntelRead])
async def list_budget_intel(
    rfp_id: Optional[int] = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[BudgetIntelRead]:
    query = select(BudgetIntelligence).where(BudgetIntelligence.user_id == current_user.id)
    if rfp_id:
        query = query.where(BudgetIntelligence.rfp_id == rfp_id)
    result = await session.execute(query)
    records = result.scalars().all()
    return [BudgetIntelRead.model_validate(record) for record in records]


@router.post("", response_model=BudgetIntelRead)
async def create_budget_intel(
    payload: BudgetIntelCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BudgetIntelRead:
    if payload.rfp_id:
        rfp_result = await session.execute(
            select(RFP).where(
                RFP.id == payload.rfp_id,
                RFP.user_id == current_user.id,
            )
        )
        if not rfp_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="RFP not found")

    record = BudgetIntelligence(
        user_id=current_user.id,
        rfp_id=payload.rfp_id,
        title=payload.title,
        fiscal_year=payload.fiscal_year,
        amount=payload.amount,
        source_url=payload.source_url,
        notes=payload.notes,
    )
    session.add(record)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="budget_intel",
        entity_id=record.id,
        action="budget_intel.created",
        metadata={"rfp_id": payload.rfp_id, "title": payload.title},
    )
    await session.commit()
    await session.refresh(record)
    return BudgetIntelRead.model_validate(record)


@router.patch("/{record_id}", response_model=BudgetIntelRead)
async def update_budget_intel(
    record_id: int,
    payload: BudgetIntelUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BudgetIntelRead:
    result = await session.execute(
        select(BudgetIntelligence).where(
            BudgetIntelligence.id == record_id,
            BudgetIntelligence.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Budget record not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="budget_intel",
        entity_id=record.id,
        action="budget_intel.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(record)
    return BudgetIntelRead.model_validate(record)


@router.delete("/{record_id}")
async def delete_budget_intel(
    record_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(BudgetIntelligence).where(
            BudgetIntelligence.id == record_id,
            BudgetIntelligence.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Budget record not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="budget_intel",
        entity_id=record.id,
        action="budget_intel.deleted",
        metadata={"rfp_id": record.rfp_id},
    )
    await session.delete(record)
    await session.commit()
    return {"message": "Budget record deleted"}
