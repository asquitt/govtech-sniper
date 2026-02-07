"""Report schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.report import ReportType, ScheduleFrequency


class ReportConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    group_by: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"


class SavedReportCreate(BaseModel):
    name: str = Field(max_length=255)
    report_type: ReportType
    config: ReportConfig = Field(default_factory=ReportConfig)
    schedule: Optional[ScheduleFrequency] = None


class SavedReportRead(BaseModel):
    id: int
    user_id: int
    name: str
    report_type: ReportType
    config: dict
    schedule: Optional[ScheduleFrequency]
    last_generated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SavedReportUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    report_type: Optional[ReportType] = None
    config: Optional[ReportConfig] = None
    schedule: Optional[ScheduleFrequency] = None


class ReportDataResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    total_rows: int
