"""Report schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.report import ReportType, ScheduleFrequency


class ReportConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    group_by: str | None = None
    sort_by: str | None = None
    sort_order: str = "asc"


class SavedReportCreate(BaseModel):
    name: str = Field(max_length=255)
    report_type: ReportType
    config: ReportConfig = Field(default_factory=ReportConfig)
    schedule: ScheduleFrequency | None = None


class SavedReportRead(BaseModel):
    id: int
    user_id: int
    name: str
    report_type: ReportType
    config: dict
    schedule: ScheduleFrequency | None
    last_generated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SavedReportUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    report_type: ReportType | None = None
    config: ReportConfig | None = None
    schedule: ScheduleFrequency | None = None


class ReportDataResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    total_rows: int
