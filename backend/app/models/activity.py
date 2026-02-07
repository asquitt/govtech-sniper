"""
RFP Sniper - Activity Feed Models
===================================
Tracks user actions across proposals for real-time activity feeds.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel


class ActivityType(str, Enum):
    SECTION_EDITED = "section_edited"
    SECTION_GENERATED = "section_generated"
    REVIEW_SCHEDULED = "review_scheduled"
    REVIEW_COMPLETED = "review_completed"
    COMMENT_ADDED = "comment_added"
    COMMENT_RESOLVED = "comment_resolved"
    MEMBER_JOINED = "member_joined"
    SECTION_ASSIGNED = "section_assigned"
    DOCUMENT_EXPORTED = "document_exported"
    STATUS_CHANGED = "status_changed"


class ActivityFeedEntry(SQLModel, table=True):
    """Single activity event within a proposal."""

    __tablename__ = "activity_feed"

    id: int | None = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposals.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    activity_type: ActivityType
    summary: str = Field(max_length=500)
    section_id: int | None = Field(default=None, foreign_key="proposal_sections.id")
    metadata_json: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
