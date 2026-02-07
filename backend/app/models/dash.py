"""
RFP Sniper - Dash (AI Assistant) Models
=======================================
Session and message history for Dash.
"""

from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel


class DashRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DashSession(SQLModel, table=True):
    """
    Chat session for Dash.
    """

    __tablename__ = "dash_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str | None = Field(default=None, max_length=255)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DashMessage(SQLModel, table=True):
    """
    Message within a Dash session.
    """

    __tablename__ = "dash_messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="dash_sessions.id", index=True)
    role: DashRole = Field(index=True)
    content: str
    citations: list[dict] = Field(default=[], sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
