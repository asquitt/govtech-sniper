"""Industry events and days model."""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, Text


class EventType(str, Enum):
    INDUSTRY_DAY = "industry_day"
    PRE_SOLICITATION = "pre_solicitation"
    CONFERENCE = "conference"
    WEBINAR = "webinar"


class IndustryEvent(SQLModel, table=True):
    __tablename__ = "industry_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=255)
    agency: Optional[str] = Field(default=None, max_length=255, index=True)
    event_type: EventType = Field(default=EventType.INDUSTRY_DAY)
    date: datetime
    location: Optional[str] = Field(default=None, max_length=500)
    registration_url: Optional[str] = Field(default=None, max_length=500)
    related_rfp_id: Optional[int] = Field(default=None, foreign_key="rfps.id", index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    source: Optional[str] = Field(default=None, max_length=100)
    is_archived: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
