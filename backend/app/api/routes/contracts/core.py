"""
Contract CRUD operations.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.contract import ContractAward
from app.schemas.contract import (
    ContractCreate,
    ContractListResponse,
    ContractRead,
    ContractUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


@router.get("/", response_model=ContractListResponse)
async def list_contracts(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractListResponse:
    result = await session.execute(
        select(ContractAward).where(ContractAward.user_id == current_user.id)
    )
    contracts = result.scalars().all()
    data = [ContractRead.model_validate(c) for c in contracts]
    return ContractListResponse(contracts=data, total=len(data))


@router.post("/", response_model=ContractRead)
async def create_contract(
    payload: ContractCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractRead:
    contract = ContractAward(
        user_id=current_user.id,
        rfp_id=payload.rfp_id,
        contract_number=payload.contract_number,
        title=payload.title,
        agency=payload.agency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        value=payload.value,
        status=payload.status,
        summary=payload.summary,
    )
    session.add(contract)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        action="contract.created",
        metadata={"contract_number": contract.contract_number},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="contract.created",
        payload={"contract_id": contract.id, "title": contract.title},
    )
    await session.commit()
    await session.refresh(contract)

    return ContractRead.model_validate(contract)


@router.get("/{contract_id}", response_model=ContractRead)
async def get_contract(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractRead:
    result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return ContractRead.model_validate(contract)


@router.patch("/{contract_id}", response_model=ContractRead)
async def update_contract(
    contract_id: int,
    payload: ContractUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractRead:
    result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    contract.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        action="contract.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(contract)

    return ContractRead.model_validate(contract)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        action="contract.deleted",
        metadata={"contract_number": contract.contract_number},
    )
    await session.delete(contract)
    await session.commit()

    return {"message": "Contract deleted"}
