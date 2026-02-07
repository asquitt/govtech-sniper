"""
RFP Sniper - Proposal Outline Models
======================================
Auto-generated proposal outlines with nested sections.
"""

from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, Relationship, SQLModel, Text


class OutlineStatus(str, Enum):
    """Status of a proposal outline."""

    GENERATING = "generating"
    DRAFT = "draft"
    APPROVED = "approved"


class ProposalOutline(SQLModel, table=True):
    """Top-level outline for a proposal, generated from compliance matrix."""

    __tablename__ = "proposal_outlines"

    id: int | None = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposals.id", unique=True, index=True)
    status: OutlineStatus = Field(default=OutlineStatus.DRAFT)
    raw_ai_response: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    sections: list["OutlineSection"] = Relationship(back_populates="outline")


class OutlineSection(SQLModel, table=True):
    """Individual section within a proposal outline."""

    __tablename__ = "outline_sections"

    id: int | None = Field(default=None, primary_key=True)
    outline_id: int = Field(foreign_key="proposal_outlines.id", index=True)
    parent_id: int | None = Field(default=None, foreign_key="outline_sections.id")

    title: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text))
    mapped_requirement_ids: list[str] = Field(default=[], sa_column=Column(JSON))
    display_order: int = Field(default=0)
    estimated_pages: float | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    outline: ProposalOutline | None = Relationship(back_populates="sections")
