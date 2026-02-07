"""
Contract deliverable CRUD operations.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.contract import ContractAward, ContractDeliverable
from app.schemas.contract import DeliverableCreate, DeliverableRead, DeliverableUpdate
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


@router.get("/{contract_id}/deliverables", response_model=list[DeliverableRead])
async def list_deliverables(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DeliverableRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractDeliverable).where(ContractDeliverable.contract_id == contract_id)
    )
    deliverables = result.scalars().all()
    return [DeliverableRead.model_validate(d) for d in deliverables]


@router.post("/{contract_id}/deliverables", response_model=DeliverableRead)
async def create_deliverable(
    contract_id: int,
    payload: DeliverableCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeliverableRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    deliverable = ContractDeliverable(
        contract_id=contract_id,
        title=payload.title,
        due_date=payload.due_date,
        status=payload.status,
        notes=payload.notes,
    )
    session.add(deliverable)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_deliverable",
        entity_id=deliverable.id,
        action="contract.deliverable_created",
        metadata={"contract_id": contract_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="contract.deliverable_created",
        payload={"contract_id": contract_id, "deliverable_id": deliverable.id},
    )
    await session.commit()
    await session.refresh(deliverable)

    return DeliverableRead.model_validate(deliverable)


@router.patch("/deliverables/{deliverable_id}", response_model=DeliverableRead)
async def update_deliverable(
    deliverable_id: int,
    payload: DeliverableUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeliverableRead:
    result = await session.execute(
        select(ContractDeliverable).where(ContractDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    # Ensure ownership
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == deliverable.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deliverable, field, value)
    deliverable.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_deliverable",
        entity_id=deliverable.id,
        action="contract.deliverable_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(deliverable)

    return DeliverableRead.model_validate(deliverable)


@router.delete("/deliverables/{deliverable_id}")
async def delete_deliverable(
    deliverable_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(ContractDeliverable).where(ContractDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == deliverable.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_deliverable",
        entity_id=deliverable.id,
        action="contract.deliverable_deleted",
        metadata={"contract_id": deliverable.contract_id},
    )
    await session.delete(deliverable)
    await session.commit()

    return {"message": "Deliverable deleted"}
