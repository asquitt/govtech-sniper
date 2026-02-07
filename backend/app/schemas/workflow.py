"""Workflow rule and execution schemas."""

from datetime import datetime
from typing import Optional, List, Union

from pydantic import BaseModel

from app.models.workflow import TriggerType, ExecutionStatus


class WorkflowCondition(BaseModel):
    field: str
    operator: str  # equals, gt, lt, contains, in_list
    value: Union[str, int, float, List[str]]


class WorkflowAction(BaseModel):
    action_type: str  # move_stage, assign_user, send_notification, add_tag
    params: dict


class WorkflowRuleCreate(BaseModel):
    name: str
    trigger_type: TriggerType
    conditions: List[WorkflowCondition] = []
    actions: List[WorkflowAction] = []
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
    name: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    conditions: Optional[List[WorkflowCondition]] = None
    actions: Optional[List[WorkflowAction]] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None


class WorkflowExecutionRead(BaseModel):
    id: int
    rule_id: int
    triggered_at: datetime
    entity_type: str
    entity_id: int
    status: ExecutionStatus
    result: dict
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkflowRuleListResponse(BaseModel):
    items: List[WorkflowRuleRead]
    total: int
