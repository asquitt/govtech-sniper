"""
RFP Sniper - Saved Search Models
================================
Saved opportunity searches and filters.
"""

from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class SavedSearch(SQLModel, table=True):
    """
    Saved opportunity search for a user.
    """

    __tablename__ = "saved_searches"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    filters: dict = Field(default={}, sa_column=Column(JSON))
    is_active: bool = Field(default=True)

    last_run_at: datetime | None = None
    last_match_count: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
