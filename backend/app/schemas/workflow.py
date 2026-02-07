"""Workflow rule and execution schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.models.workflow import ExecutionStatus, TriggerType


class WorkflowCondition(BaseModel):
    field: str
    operator: str  # equals, gt, lt, contains, in_list
    value: str | int | float | list[str]


class WorkflowAction(BaseModel):
    action_type: str  # move_stage, assign_user, send_notification, add_tag
    params: dict


class WorkflowRuleCreate(BaseModel):
    name: str
    trigger_type: TriggerType
    conditions: list[WorkflowCondition] = []
    actions: list[WorkflowAction] = []
    priority: int = 0


class WorkflowRuleRead(BaseModel):
    id: int
    user_id: int
    name: str
    is_enabled: bool
    trigger_type: TriggerType
    conditions: list
    actions: list
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRuleUpdate(BaseModel):
    name: str | None = None
    trigger_type: TriggerType | None = None
    conditions: list[WorkflowCondition] | None = None
    actions: list[WorkflowAction] | None = None
    priority: int | None = None
    is_enabled: bool | None = None


class WorkflowExecutionRead(BaseModel):
    id: int
    rule_id: int
    triggered_at: datetime
    entity_type: str
    entity_id: int
    status: ExecutionStatus
    result: dict
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowRuleListResponse(BaseModel):
    items: list[WorkflowRuleRead]
    total: int
