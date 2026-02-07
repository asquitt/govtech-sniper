"""Industry event schemas."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    agency: Optional[str] = None
    event_type: str = "industry_day"
    date: datetime
    location: Optional[str] = None
    registration_url: Optional[str] = None
    related_rfp_id: Optional[int] = None
    description: Optional[str] = None
    source: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    agency: Optional[str] = None
    event_type: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    registration_url: Optional[str] = None
    related_rfp_id: Optional[int] = None
    description: Optional[str] = None
    source: Optional[str] = None
    is_archived: Optional[bool] = None


class EventRead(BaseModel):
    id: int
    user_id: int
    title: str
    agency: Optional[str]
    event_type: str
    date: datetime
    location: Optional[str]
    registration_url: Optional[str]
    related_rfp_id: Optional[int]
    description: Optional[str]
    source: Optional[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    events: List[EventRead]
    total: int
