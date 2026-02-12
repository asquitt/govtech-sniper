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
    is_shared: bool = False
    shared_with_emails: list[str] = Field(default_factory=list)
    delivery_recipients: list[str] = Field(default_factory=list)
    delivery_enabled: bool = False
    delivery_subject: str | None = Field(default=None, max_length=255)


class SavedReportRead(BaseModel):
    id: int
    user_id: int
    name: str
    report_type: ReportType
    config: dict
    schedule: ScheduleFrequency | None
    is_shared: bool
    shared_with_emails: list[str]
    delivery_recipients: list[str]
    delivery_enabled: bool
    delivery_subject: str | None
    last_generated_at: datetime | None
    last_delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SavedReportUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    report_type: ReportType | None = None
    config: ReportConfig | None = None
    schedule: ScheduleFrequency | None = None
    is_shared: bool | None = None
    shared_with_emails: list[str] | None = None
    delivery_recipients: list[str] | None = None
    delivery_enabled: bool | None = None
    delivery_subject: str | None = Field(default=None, max_length=255)


class ReportShareUpdate(BaseModel):
    is_shared: bool = True
    shared_with_emails: list[str] = Field(default_factory=list)


class ReportDeliveryScheduleUpdate(BaseModel):
    frequency: ScheduleFrequency
    recipients: list[str] = Field(default_factory=list)
    enabled: bool = True
    subject: str | None = Field(default=None, max_length=255)


class ReportDataResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    total_rows: int
