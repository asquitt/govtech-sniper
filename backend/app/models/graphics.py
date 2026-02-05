"""
RFP Sniper - Proposal Graphics Models
=====================================
Tracks proposal graphics requests and delivery status.
"""

from datetime import datetime, date
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, Text


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

    id: Optional[int] = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposals.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    section_id: Optional[int] = Field(default=None, foreign_key="proposal_sections.id", index=True)

    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    status: GraphicsRequestStatus = Field(default=GraphicsRequestStatus.REQUESTED)
    due_date: Optional[date] = None
    asset_url: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
