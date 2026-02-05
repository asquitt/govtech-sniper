"""
RFP Sniper - Saved Search Models
================================
Saved opportunity searches and filters.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, JSON


class SavedSearch(SQLModel, table=True):
    """
    Saved opportunity search for a user.
    """
    __tablename__ = "saved_searches"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    filters: dict = Field(default={}, sa_column=Column(JSON))
    is_active: bool = Field(default=True)

    last_run_at: Optional[datetime] = None
    last_match_count: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
