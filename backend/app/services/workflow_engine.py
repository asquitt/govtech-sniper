"""Workflow execution engine for rule evaluation and action dispatch."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.routes.notifications import Notification, NotificationType
from app.models.capture import CapturePlan, TeamingPartner
from app.models.rfp import RFP
from app.models.workflow import ExecutionStatus, TriggerType, WorkflowExecution, WorkflowRule


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _match_condition(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "equals":
        return actual == expected

    if operator == "gt":
        left = _to_float(actual)
        right = _to_float(expected)
        return left is not None and right is not None and left > right

    if operator == "lt":
        left = _to_float(actual)
        right = _to_float(expected)
        return left is not None and right is not None and left < right

    if operator == "contains":
        if actual is None:
            return False
        if isinstance(actual, list):
            return expected in actual
        return str(expected).lower() in str(actual).lower()

    if operator == "in_list":
        if not isinstance(expected, list):
            return False
        return actual in expected

    return False


def _rule_matches(rule: WorkflowRule, context: dict[str, Any]) -> bool:
    if not rule.conditions:
        return True

    for condition in rule.conditions:
        field = str(condition.get("field", "")).strip()
        operator = str(condition.get("operator", "")).strip()
        expected = condition.get("value")
        actual = context.get(field)
        if not _match_condition(actual, operator, expected):
            return False
    return True


async def _execute_action(
    session: AsyncSession,
    *,
    action: dict[str, Any],
    entity_type: str,
    entity_id: int,
    owner_user_id: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    action_type = str(action.get("action_type", "")).strip()
    params = action.get("params") or {}

    if action_type == "move_stage" and entity_type == "capture_plan":
        stage = str(params.get("stage", "")).strip()
        if not stage:
            return {"action_type": action_type, "status": "skipped", "reason": "missing stage"}
        capture_plan = await session.get(CapturePlan, entity_id)
        if not capture_plan:
            return {
                "action_type": action_type,
                "status": "failed",
                "reason": "capture plan missing",
            }
        previous_stage = capture_plan.stage.value
        capture_plan.stage = stage  # enum coercion handled by SQLModel
        capture_plan.updated_at = datetime.utcnow()
        return {
            "action_type": action_type,
            "status": "success",
            "from": previous_stage,
            "to": stage,
        }

    if action_type == "assign_user" and entity_type == "capture_plan":
        assignee_id = params.get("user_id")
        assignee_int = int(assignee_id) if assignee_id is not None else None
        if assignee_int is None:
            return {
                "action_type": action_type,
                "status": "skipped",
                "reason": "missing user_id",
            }
        capture_plan = await session.get(CapturePlan, entity_id)
        if not capture_plan:
            return {
                "action_type": action_type,
                "status": "failed",
                "reason": "capture plan missing",
            }
        previous_owner = capture_plan.owner_id
        capture_plan.owner_id = assignee_int
        capture_plan.updated_at = datetime.utcnow()
        return {
            "action_type": action_type,
            "status": "success",
            "from": previous_owner,
            "to": assignee_int,
        }

    if action_type == "add_tag" and entity_type == "capture_plan":
        tag = str(params.get("tag", "")).strip()
        if not tag:
            return {"action_type": action_type, "status": "skipped", "reason": "missing tag"}

        capture_plan = await session.get(CapturePlan, entity_id)
        if not capture_plan:
            return {
                "action_type": action_type,
                "status": "failed",
                "reason": "capture plan missing",
            }

        rfp = await session.get(RFP, capture_plan.rfp_id)
        if not rfp:
            return {"action_type": action_type, "status": "failed", "reason": "rfp missing"}

        existing_notes = rfp.intel_notes or ""
        marker = f"#{tag}"
        if marker not in existing_notes:
            rfp.intel_notes = (existing_notes + " " + marker).strip()
        rfp.updated_at = datetime.utcnow()
        return {"action_type": action_type, "status": "success", "tag": marker}

    if action_type == "send_notification":
        title = str(params.get("title") or "Workflow rule executed")
        message = str(params.get("message") or "An automation rule was triggered.")
        notification = Notification(
            user_id=owner_user_id,
            notification_type=NotificationType.SYSTEM_ALERT,
            title=title,
            message=message,
            channels=["in_app"],
            rfp_id=context.get("rfp_id"),
            proposal_id=context.get("proposal_id"),
            meta={
                "workflow_entity_type": entity_type,
                "workflow_entity_id": entity_id,
                "action_type": action_type,
            },
        )
        session.add(notification)
        return {
            "action_type": action_type,
            "status": "success",
            "title": title,
        }

    if action_type == "evaluate_teaming":
        rfp_id = context.get("rfp_id")
        if not rfp_id:
            return {
                "action_type": action_type,
                "status": "skipped",
                "reason": "missing rfp context",
            }

        rfp = await session.get(RFP, int(rfp_id))
        if not rfp:
            return {"action_type": action_type, "status": "failed", "reason": "rfp missing"}

        partner_result = await session.execute(
            select(TeamingPartner).where(
                TeamingPartner.user_id == owner_user_id,
                TeamingPartner.is_public == True,
            )
        )
        partners = partner_result.scalars().all()
        matched = [
            partner
            for partner in partners
            if rfp.naics_code and rfp.naics_code in (partner.naics_codes or [])
        ]
        preview = [{"partner_id": partner.id, "name": partner.name} for partner in matched[:5]]
        return {
            "action_type": action_type,
            "status": "success",
            "matched_partners": preview,
            "match_count": len(matched),
        }

    return {
        "action_type": action_type,
        "status": "skipped",
        "reason": "unsupported action",
    }


async def execute_workflow_rules(
    session: AsyncSession,
    *,
    user_id: int,
    trigger_type: TriggerType,
    entity_type: str,
    entity_id: int,
    context: dict[str, Any],
) -> list[WorkflowExecution]:
    """Evaluate and execute enabled workflow rules for the given trigger."""

    rules_result = await session.execute(
        select(WorkflowRule)
        .where(
            WorkflowRule.user_id == user_id,
            WorkflowRule.trigger_type == trigger_type,
            WorkflowRule.is_enabled == True,
        )
        .order_by(WorkflowRule.priority.desc(), WorkflowRule.created_at.asc())
    )
    rules = rules_result.scalars().all()

    executions: list[WorkflowExecution] = []
    owner_user_id = int(context.get("owner_id") or user_id)

    for rule in rules:
        matched = _rule_matches(rule, context)
        if not matched:
            execution = WorkflowExecution(
                rule_id=rule.id,
                entity_type=entity_type,
                entity_id=entity_id,
                status=ExecutionStatus.SKIPPED,
                result={"matched": False},
                completed_at=datetime.utcnow(),
            )
            session.add(execution)
            executions.append(execution)
            continue

        action_results: list[dict[str, Any]] = []
        failed = False
        for action in rule.actions or []:
            action_result = await _execute_action(
                session,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                owner_user_id=owner_user_id,
                context=context,
            )
            action_results.append(action_result)
            if action_result.get("status") == "failed":
                failed = True

        execution = WorkflowExecution(
            rule_id=rule.id,
            entity_type=entity_type,
            entity_id=entity_id,
            status=ExecutionStatus.FAILED if failed else ExecutionStatus.SUCCESS,
            result={"matched": True, "actions": action_results},
            completed_at=datetime.utcnow(),
        )
        session.add(execution)
        executions.append(execution)

    await session.commit()

    for execution in executions:
        await session.refresh(execution)

    return executions


def build_capture_context(plan: CapturePlan, rfp: RFP | None) -> dict[str, Any]:
    """Build a normalized workflow context payload for capture entities."""
    now = datetime.utcnow()
    days_to_deadline: int | None = None
    if rfp and rfp.response_deadline:
        days_to_deadline = (rfp.response_deadline - now).days

    return {
        "capture_plan_id": plan.id,
        "rfp_id": plan.rfp_id,
        "owner_id": plan.owner_id,
        "stage": plan.stage.value,
        "bid_decision": plan.bid_decision.value,
        "win_probability": plan.win_probability,
        "rfp_title": rfp.title if rfp else None,
        "agency": rfp.agency if rfp else None,
        "naics_code": rfp.naics_code if rfp else None,
        "estimated_value": rfp.estimated_value if rfp else None,
        "days_to_deadline": days_to_deadline,
    }
