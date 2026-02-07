"""
Contract CLIN CRUD operations.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.contract import ContractAward, ContractCLIN
from app.schemas.contract_modifications import CLINCreate, CLINUpdate, CLINRead
from app.services.audit_service import log_audit_event

router = APIRouter()


@router.get("/{contract_id}/clins", response_model=List[CLINRead])
async def list_clins(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[CLINRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractCLIN).where(ContractCLIN.contract_id == contract_id)
    )
    clins = result.scalars().all()
    return [CLINRead.model_validate(c) for c in clins]


@router.post("/{contract_id}/clins", response_model=CLINRead)
async def create_clin(
    contract_id: int,
    payload: CLINCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CLINRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    clin = ContractCLIN(
        contract_id=contract_id,
        clin_number=payload.clin_number,
        description=payload.description,
        clin_type=payload.clin_type,
        unit_price=payload.unit_price,
        quantity=payload.quantity,
        total_value=payload.total_value,
        funded_amount=payload.funded_amount,
    )
    session.add(clin)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_clin",
        entity_id=clin.id,
        action="contract.clin_created",
        metadata={"contract_id": contract_id},
    )
    await session.commit()
    await session.refresh(clin)

    return CLINRead.model_validate(clin)


@router.patch("/{contract_id}/clins/{clin_id}", response_model=CLINRead)
async def update_clin(
    contract_id: int,
    clin_id: int,
    payload: CLINUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CLINRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractCLIN).where(
            ContractCLIN.id == clin_id,
            ContractCLIN.contract_id == contract_id,
        )
    )
    clin = result.scalar_one_or_none()
    if not clin:
        raise HTTPException(status_code=404, detail="CLIN not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clin, field, value)
    clin.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_clin",
        entity_id=clin.id,
        action="contract.clin_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(clin)

    return CLINRead.model_validate(clin)


@router.delete("/{contract_id}/clins/{clin_id}")
async def delete_clin(
    contract_id: int,
    clin_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractCLIN).where(
            ContractCLIN.id == clin_id,
            ContractCLIN.contract_id == contract_id,
        )
    )
    clin = result.scalar_one_or_none()
    if not clin:
        raise HTTPException(status_code=404, detail="CLIN not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_clin",
        entity_id=clin.id,
        action="contract.clin_deleted",
        metadata={"contract_id": contract_id},
    )
    await session.delete(clin)
    await session.commit()

    return {"message": "CLIN deleted"}
