"""
Capture activity (Gantt timeline) schemas.
"""

from datetime import date, datetime

from pydantic import BaseModel


class ActivityCreate(BaseModel):
    title: str
    start_date: date | None = None
    end_date: date | None = None
    is_milestone: bool = False
    status: str = "planned"
    sort_order: int = 0
    depends_on_id: int | None = None


class ActivityUpdate(BaseModel):
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_milestone: bool | None = None
    status: str | None = None
    sort_order: int | None = None
    depends_on_id: int | None = None


class ActivityRead(BaseModel):
    id: int
    capture_plan_id: int
    title: str
    start_date: date | None
    end_date: date | None
    is_milestone: bool
    status: str
    sort_order: int
    depends_on_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GanttPlanRow(BaseModel):
    plan_id: int
    rfp_id: int
    rfp_title: str
    agency: str | None
    stage: str
    response_deadline: datetime | None
    activities: list[ActivityRead]
