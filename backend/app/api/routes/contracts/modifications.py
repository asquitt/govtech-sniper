"""
Contract modification CRUD operations.
"""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.contract import ContractAward, ContractModification
from app.schemas.contract_modifications import ModificationCreate, ModificationRead
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

router = APIRouter()


@router.get("/{contract_id}/modifications", response_model=list[ModificationRead])
async def list_modifications(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ModificationRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractModification)
        .where(ContractModification.contract_id == contract_id)
        .order_by(ContractModification.effective_date.desc().nullslast())
    )
    mods = result.scalars().all()
    return [ModificationRead.model_validate(m) for m in mods]


@router.post("/{contract_id}/modifications", response_model=ModificationRead)
async def create_modification(
    contract_id: int,
    payload: ModificationCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ModificationRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    mod = ContractModification(
        contract_id=contract_id,
        modification_number=payload.modification_number,
        mod_type=payload.mod_type,
        description=payload.description,
        effective_date=payload.effective_date,
        value_change=payload.value_change,
    )
    session.add(mod)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_modification",
        entity_id=mod.id,
        action="contract.modification_created",
        metadata={"contract_id": contract_id},
    )
    await session.commit()
    await session.refresh(mod)

    return ModificationRead.model_validate(mod)


@router.delete("/{contract_id}/modifications/{mod_id}")
async def delete_modification(
    contract_id: int,
    mod_id: int,
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
        select(ContractModification).where(
            ContractModification.id == mod_id,
            ContractModification.contract_id == contract_id,
        )
    )
    mod = result.scalar_one_or_none()
    if not mod:
        raise HTTPException(status_code=404, detail="Modification not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_modification",
        entity_id=mod.id,
        action="contract.modification_deleted",
        metadata={"contract_id": contract_id},
    )
    await session.delete(mod)
    await session.commit()

    return {"message": "Modification deleted"}
