"""
RFP Sniper - Inbox Models
===========================
Shared team inbox messages for workspace collaboration.
"""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class InboxMessageType(str, Enum):
    GENERAL = "general"
    OPPORTUNITY_ALERT = "opportunity_alert"
    RFP_FORWARD = "rfp_forward"


class InboxMessage(SQLModel, table=True):
    """A message in a workspace's shared team inbox."""

    __tablename__ = "inbox_messages"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    sender_id: int = Field(foreign_key="users.id", index=True)
    subject: str = Field(max_length=500)
    body: str
    message_type: str = Field(default=InboxMessageType.GENERAL.value, max_length=50)
    is_read: bool = Field(default=False)
    read_by: str = Field(default="[]")  # JSON array of user IDs who've read it
    attachments: str | None = Field(default=None)  # JSON array of attachment refs

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
