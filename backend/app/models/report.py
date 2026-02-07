"""Saved report models for custom reporting."""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, JSON


class ReportType(str, Enum):
    PIPELINE = "pipeline"
    PROPOSALS = "proposals"
    REVENUE = "revenue"
    ACTIVITY = "activity"


class ScheduleFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SavedReport(SQLModel, table=True):
    __tablename__ = "saved_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=255)
    report_type: ReportType = Field(index=True)
    config: dict = Field(default={}, sa_column=Column(JSON))
    schedule: Optional[ScheduleFrequency] = Field(default=None)
    last_generated_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
