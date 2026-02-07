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
    go_no_go_decision: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewComplete(BaseModel):
    overall_score: float
    summary: str | None = None
    go_no_go_decision: str | None = None


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------


class AssignmentCreate(BaseModel):
    reviewer_user_id: int
    due_date: datetime | None = None


class AssignmentRead(BaseModel):
    id: int
    review_id: int
    reviewer_user_id: int
    status: str
    due_date: datetime | None = None
    completed_at: datetime | None = None
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
# Checklist
# ---------------------------------------------------------------------------


class ChecklistItemCreate(BaseModel):
    category: str
    item_text: str
    display_order: int = 0


class ChecklistItemUpdate(BaseModel):
    status: str | None = None  # pending | pass | fail | na
    reviewer_note: str | None = None


class ChecklistItemRead(BaseModel):
    id: int
    review_id: int
    category: str
    item_text: str
    status: str
    reviewer_note: str | None = None
    display_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChecklistCreateFromTemplate(BaseModel):
    review_type: str  # pink | red | gold — auto-populates items


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class ReviewDashboardItem(BaseModel):
    review_id: int
    proposal_id: int
    proposal_title: str
    review_type: str
    status: str
    scheduled_date: datetime | None = None
    overall_score: float | None = None
    go_no_go_decision: str | None = None
    total_comments: int = 0
    open_comments: int = 0
    total_assignments: int = 0
    completed_assignments: int = 0


# ---------------------------------------------------------------------------
# List wrapper
# ---------------------------------------------------------------------------


class ReviewListResponse(BaseModel):
    items: list[ReviewRead]
    total: int
