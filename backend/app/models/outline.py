"""
RFP Sniper - Proposal Outline Models
======================================
Auto-generated proposal outlines with nested sections.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel, Column, JSON, Text


class OutlineStatus(str, Enum):
    """Status of a proposal outline."""
    GENERATING = "generating"
    DRAFT = "draft"
    APPROVED = "approved"


class ProposalOutline(SQLModel, table=True):
    """Top-level outline for a proposal, generated from compliance matrix."""
    __tablename__ = "proposal_outlines"

    id: Optional[int] = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposals.id", unique=True, index=True)
    status: OutlineStatus = Field(default=OutlineStatus.DRAFT)
    raw_ai_response: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    sections: List["OutlineSection"] = Relationship(back_populates="outline")


class OutlineSection(SQLModel, table=True):
    """Individual section within a proposal outline."""
    __tablename__ = "outline_sections"

    id: Optional[int] = Field(default=None, primary_key=True)
    outline_id: int = Field(foreign_key="proposal_outlines.id", index=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="outline_sections.id")

    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    mapped_requirement_ids: List[str] = Field(default=[], sa_column=Column(JSON))
    display_order: int = Field(default=0)
    estimated_pages: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    outline: Optional[ProposalOutline] = Relationship(back_populates="sections")
