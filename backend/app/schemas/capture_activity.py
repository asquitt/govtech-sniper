"""
Capture activity (Gantt timeline) schemas.
"""

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel


class ActivityCreate(BaseModel):
    title: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_milestone: bool = False
    status: str = "planned"
    sort_order: int = 0
    depends_on_id: Optional[int] = None


class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_milestone: Optional[bool] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    depends_on_id: Optional[int] = None


class ActivityRead(BaseModel):
    id: int
    capture_plan_id: int
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    is_milestone: bool
    status: str
    sort_order: int
    depends_on_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GanttPlanRow(BaseModel):
    plan_id: int
    rfp_id: int
    rfp_title: str
    agency: Optional[str]
    stage: str
    response_deadline: Optional[datetime]
    activities: List[ActivityRead]
