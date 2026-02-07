"""
Contract task CRUD operations.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.contract import ContractAward, ContractTask
from app.schemas.contract import TaskCreate, TaskRead, TaskUpdate
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth

router = APIRouter()


@router.get("/{contract_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TaskRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractTask).where(ContractTask.contract_id == contract_id)
    )
    tasks = result.scalars().all()
    return [TaskRead.model_validate(t) for t in tasks]


@router.post("/{contract_id}/tasks", response_model=TaskRead)
async def create_task(
    contract_id: int,
    payload: TaskCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TaskRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    task = ContractTask(
        contract_id=contract_id,
        title=payload.title,
        due_date=payload.due_date,
        notes=payload.notes,
    )
    session.add(task)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_task",
        entity_id=task.id,
        action="contract.task_created",
        metadata={"contract_id": contract_id},
    )
    await session.commit()
    await session.refresh(task)

    return TaskRead.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TaskRead:
    result = await session.execute(select(ContractTask).where(ContractTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == task.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    task.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_task",
        entity_id=task.id,
        action="contract.task_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(task)

    return TaskRead.model_validate(task)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(ContractTask).where(ContractTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == task.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_task",
        entity_id=task.id,
        action="contract.task_deleted",
        metadata={"contract_id": task.contract_id},
    )
    await session.delete(task)
    await session.commit()

    return {"message": "Task deleted"}
