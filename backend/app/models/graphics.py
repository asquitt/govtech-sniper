"""
RFP Sniper - Proposal Graphics Models
=====================================
Tracks proposal graphics requests and delivery status.
"""

from datetime import date, datetime
from enum import Enum

from sqlmodel import Column, Field, SQLModel, Text


class GraphicsRequestStatus(str, Enum):
    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    REJECTED = "rejected"


class ProposalGraphicRequest(SQLModel, table=True):
    """
    Request to create or update proposal graphics.
    """

    __tablename__ = "proposal_graphic_requests"

    id: int | None = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposals.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    section_id: int | None = Field(default=None, foreign_key="proposal_sections.id", index=True)

    title: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text))
    status: GraphicsRequestStatus = Field(default=GraphicsRequestStatus.REQUESTED)
    due_date: date | None = None
    asset_url: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
