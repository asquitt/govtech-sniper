"""Industry events and days model."""

from datetime import datetime
from enum import Enum

from sqlmodel import Column, Field, SQLModel, Text


class EventType(str, Enum):
    INDUSTRY_DAY = "industry_day"
    PRE_SOLICITATION = "pre_solicitation"
    CONFERENCE = "conference"
    WEBINAR = "webinar"


class IndustryEvent(SQLModel, table=True):
    __tablename__ = "industry_events"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=255)
    agency: str | None = Field(default=None, max_length=255, index=True)
    event_type: EventType = Field(default=EventType.INDUSTRY_DAY)
    date: datetime
    location: str | None = Field(default=None, max_length=500)
    registration_url: str | None = Field(default=None, max_length=500)
    related_rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    source: str | None = Field(default=None, max_length=100)
    is_archived: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
