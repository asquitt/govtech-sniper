"""Industry event schemas."""

from datetime import datetime

from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    agency: str | None = None
    event_type: str = "industry_day"
    date: datetime
    location: str | None = None
    registration_url: str | None = None
    related_rfp_id: int | None = None
    description: str | None = None
    source: str | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    agency: str | None = None
    event_type: str | None = None
    date: datetime | None = None
    location: str | None = None
    registration_url: str | None = None
    related_rfp_id: int | None = None
    description: str | None = None
    source: str | None = None
    is_archived: bool | None = None


class EventRead(BaseModel):
    id: int
    user_id: int
    title: str
    agency: str | None
    event_type: str
    date: datetime
    location: str | None
    registration_url: str | None
    related_rfp_id: int | None
    description: str | None
    source: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    events: list[EventRead]
    total: int


class EventIngestResponse(BaseModel):
    created: int
    existing: int
    candidates: int
    created_event_ids: list[int]
    source_breakdown: dict[str, int]


class EventAlertRead(BaseModel):
    event: EventRead
    relevance_score: float
    match_reasons: list[str]
    days_until_event: int


class EventAlertResponse(BaseModel):
    alerts: list[EventAlertRead]
    total: int
    evaluated: int
