"""Workflow automation rules and execution history models."""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, JSON


class TriggerType(str, Enum):
    RFP_CREATED = "rfp_created"
    STAGE_CHANGED = "stage_changed"
    DEADLINE_APPROACHING = "deadline_approaching"
    SCORE_THRESHOLD = "score_threshold"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowRule(SQLModel, table=True):
    __tablename__ = "workflow_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=255)
    is_enabled: bool = Field(default=True)
    trigger_type: TriggerType = Field(index=True)
    conditions: list = Field(default=[], sa_column=Column(JSON))
    actions: list = Field(default=[], sa_column=Column(JSON))
    priority: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowExecution(SQLModel, table=True):
    __tablename__ = "workflow_executions"

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_id: int = Field(foreign_key="workflow_rules.id", index=True)
    triggered_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    entity_type: str = Field(max_length=50)
    entity_id: int
    status: ExecutionStatus
    result: dict = Field(default={}, sa_column=Column(JSON))
    completed_at: Optional[datetime] = None
