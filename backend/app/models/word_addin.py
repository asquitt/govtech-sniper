"""
RFP Sniper - Word Add-in Models
===============================
Tracks Word add-in sessions and sync events.
"""

from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel


class WordAddinSessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class WordAddinSession(SQLModel, table=True):
    """
    Word add-in session for a proposal.
    """

    __tablename__ = "word_addin_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    proposal_id: int = Field(foreign_key="proposals.id", index=True)

    document_name: str = Field(max_length=255)
    status: WordAddinSessionStatus = Field(default=WordAddinSessionStatus.ACTIVE)
    session_metadata: dict = Field(default={}, sa_column=Column("metadata", JSON))

    last_synced_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WordAddinEvent(SQLModel, table=True):
    """
    Sync events for Word add-in sessions.
    """

    __tablename__ = "word_addin_events"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="word_addin_sessions.id", index=True)

    event_type: str = Field(max_length=128, index=True)
    payload: dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
