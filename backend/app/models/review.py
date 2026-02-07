"""
RFP Sniper - Color Team Review Models
======================================
Pink, Red, and Gold team reviews for proposal quality gates.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, Text


class ReviewType(str, Enum):
    PINK = "pink"
    RED = "red"
    GOLD = "gold"


class ReviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssignmentStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"


class CommentSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


class CommentStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class ProposalReview(SQLModel, table=True):
    """Color team review for a proposal."""
    __tablename__ = "proposal_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposals.id", index=True)
    review_type: ReviewType
    status: ReviewStatus = Field(default=ReviewStatus.SCHEDULED)
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    overall_score: Optional[float] = None
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewAssignment(SQLModel, table=True):
    """Reviewer assignment to a review."""
    __tablename__ = "review_assignments"

    id: Optional[int] = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="proposal_reviews.id", index=True)
    reviewer_user_id: int = Field(foreign_key="users.id", index=True)
    status: AssignmentStatus = Field(default=AssignmentStatus.PENDING)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewComment(SQLModel, table=True):
    """Comment left by a reviewer during a review."""
    __tablename__ = "review_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="proposal_reviews.id", index=True)
    section_id: Optional[int] = Field(
        default=None, foreign_key="proposal_sections.id", index=True
    )
    reviewer_user_id: int = Field(foreign_key="users.id")
    comment_text: str = Field(sa_column=Column(Text))
    severity: CommentSeverity = Field(default=CommentSeverity.MINOR)
    status: CommentStatus = Field(default=CommentStatus.OPEN)
    resolution_note: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
