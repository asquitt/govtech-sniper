"""Workflow automation rules and execution routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.capture import CapturePlan
from app.models.rfp import RFP
from app.models.workflow import WorkflowExecution, WorkflowRule
from app.schemas.workflow import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowExecutionRead,
    WorkflowRuleCreate,
    WorkflowRuleListResponse,
    WorkflowRuleRead,
    WorkflowRuleUpdate,
)
from app.services.auth_service import UserAuth
from app.services.workflow_engine import build_capture_context, execute_workflow_rules

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("/rules", response_model=WorkflowRuleRead)
async def create_rule(
    payload: WorkflowRuleCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRuleRead:
    rule = WorkflowRule(
        user_id=current_user.id,
        name=payload.name,
        trigger_type=payload.trigger_type,
        conditions=[c.model_dump() for c in payload.conditions],
        actions=[a.model_dump() for a in payload.actions],
        priority=payload.priority,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return WorkflowRuleRead.model_validate(rule)


@router.get("/rules", response_model=WorkflowRuleListResponse)
async def list_rules(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRuleListResponse:
    base = select(WorkflowRule).where(WorkflowRule.user_id == current_user.id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    query = base.order_by(WorkflowRule.priority.desc(), WorkflowRule.created_at.desc())
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    rules = result.scalars().all()

    return WorkflowRuleListResponse(
        items=[WorkflowRuleRead.model_validate(r) for r in rules],
        total=total,
    )


@router.get("/rules/{rule_id}", response_model=WorkflowRuleRead)
async def get_rule(
    rule_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRuleRead:
    result = await session.execute(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Workflow rule not found")
    return WorkflowRuleRead.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=WorkflowRuleRead)
async def update_rule(
    rule_id: int,
    payload: WorkflowRuleUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkflowRuleRead:
    result = await session.execute(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Workflow rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "conditions" in update_data and update_data["conditions"] is not None:
        update_data["conditions"] = [
            c.model_dump() if hasattr(c, "model_dump") else c for c in update_data["conditions"]
        ]
    if "actions" in update_data and update_data["actions"] is not None:
        update_data["actions"] = [
            a.model_dump() if hasattr(a, "model_dump") else a for a in update_data["actions"]
        ]

    for field, value in update_data.items():
        setattr(rule, field, value)
    rule.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(rule)
    return WorkflowRuleRead.model_validate(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Workflow rule not found")

    await session.delete(rule)
    await session.commit()
    return {"message": "Workflow rule deleted"}


@router.post("/rules/{rule_id}/test")
async def test_rule(
    rule_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(WorkflowRule).where(
            WorkflowRule.id == rule_id,
            WorkflowRule.user_id == current_user.id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Workflow rule not found")

    # Dry-run: return static diagnostics while keeping deterministic output.
    return {
        "would_match": 1 if rule.is_enabled else 0,
        "sample_results": [
            {
                "rule_id": rule.id,
                "trigger_type": rule.trigger_type.value,
                "conditions": rule.conditions,
                "actions": rule.actions,
            }
        ]
        if rule.is_enabled
        else [],
        "rule_name": rule.name,
        "trigger_type": rule.trigger_type.value,
        "conditions_count": len(rule.conditions) if rule.conditions else 0,
        "actions_count": len(rule.actions) if rule.actions else 0,
    }


@router.get("/executions", response_model=dict)
async def list_executions(
    rule_id: int | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # Join to ensure user owns the rules
    base = (
        select(WorkflowExecution)
        .join(WorkflowRule, WorkflowExecution.rule_id == WorkflowRule.id)
        .where(WorkflowRule.user_id == current_user.id)
    )
    if rule_id is not None:
        base = base.where(WorkflowExecution.rule_id == rule_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    query = base.order_by(WorkflowExecution.triggered_at.desc())
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    executions = result.scalars().all()

    return {
        "items": [WorkflowExecutionRead.model_validate(e) for e in executions],
        "total": total,
    }


@router.post("/execute", response_model=WorkflowExecuteResponse)
async def execute_rules(
    payload: WorkflowExecuteRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkflowExecuteResponse:
    context = dict(payload.context or {})

    if payload.entity_type == "capture_plan":
        capture_plan = await session.get(CapturePlan, payload.entity_id)
        if not capture_plan:
            raise HTTPException(status_code=404, detail="Capture plan not found")

        rfp_result = await session.execute(
            select(RFP).where(
                RFP.id == capture_plan.rfp_id,
                RFP.user_id == current_user.id,
            )
        )
        rfp = rfp_result.scalar_one_or_none()
        if not rfp:
            raise HTTPException(status_code=404, detail="RFP not found")

        context = {**build_capture_context(capture_plan, rfp), **context}

    executions = await execute_workflow_rules(
        session,
        user_id=current_user.id,
        trigger_type=payload.trigger_type,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        context=context,
    )

    return WorkflowExecuteResponse(
        executions=[WorkflowExecutionRead.model_validate(item) for item in executions],
        total=len(executions),
    )
