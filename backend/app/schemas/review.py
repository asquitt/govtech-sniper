"""
RFP Sniper - Review Schemas
=============================
Request/response models for color team reviews, assignments, and comments.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

class ReviewCreate(BaseModel):
    review_type: str  # pink | red | gold
    scheduled_date: Optional[datetime] = None


class ReviewUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_date: Optional[datetime] = None


class ReviewRead(BaseModel):
    id: int
    proposal_id: int
    review_type: str
    status: str
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    overall_score: Optional[float] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewComplete(BaseModel):
    overall_score: float
    summary: Optional[str] = None


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

class AssignmentCreate(BaseModel):
    reviewer_user_id: int


class AssignmentRead(BaseModel):
    id: int
    review_id: int
    reviewer_user_id: int
    status: str
    assigned_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------

class CommentCreate(BaseModel):
    section_id: Optional[int] = None
    comment_text: str
    severity: str = "minor"  # critical | major | minor | suggestion


class CommentUpdate(BaseModel):
    status: Optional[str] = None  # open | accepted | rejected | resolved
    resolution_note: Optional[str] = None


class CommentRead(BaseModel):
    id: int
    review_id: int
    section_id: Optional[int] = None
    reviewer_user_id: int
    comment_text: str
    severity: str
    status: str
    resolution_note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# List wrapper
# ---------------------------------------------------------------------------

class ReviewListResponse(BaseModel):
    items: List[ReviewRead]
    total: int
