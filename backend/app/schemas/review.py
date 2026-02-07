"""
RFP Sniper - Review Schemas
=============================
Request/response models for color team reviews, assignments, and comments.
"""

from datetime import datetime

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewCreate(BaseModel):
    review_type: str  # pink | red | gold
    scheduled_date: datetime | None = None


class ReviewUpdate(BaseModel):
    status: str | None = None
    scheduled_date: datetime | None = None


class ReviewRead(BaseModel):
    id: int
    proposal_id: int
    review_type: str
    status: str
    scheduled_date: datetime | None = None
    completed_date: datetime | None = None
    overall_score: float | None = None
    summary: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewComplete(BaseModel):
    overall_score: float
    summary: str | None = None


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
    section_id: int | None = None
    comment_text: str
    severity: str = "minor"  # critical | major | minor | suggestion


class CommentUpdate(BaseModel):
    status: str | None = None  # open | accepted | rejected | resolved
    resolution_note: str | None = None


class CommentRead(BaseModel):
    id: int
    review_id: int
    section_id: int | None = None
    reviewer_user_id: int
    comment_text: str
    severity: str
    status: str
    resolution_note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# List wrapper
# ---------------------------------------------------------------------------


class ReviewListResponse(BaseModel):
    items: list[ReviewRead]
    total: int
