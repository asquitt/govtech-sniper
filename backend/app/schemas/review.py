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
    # Inline comment fields
    anchor_text: str | None = None
    anchor_offset_start: int | None = None
    anchor_offset_end: int | None = None
    is_inline: bool = False
    mentions: list[int] | None = None  # user_ids


class CommentUpdate(BaseModel):
    status: str | None = None  # open | assigned | addressed | verified | closed | rejected
    resolution_note: str | None = None
    assigned_to_user_id: int | None = None


class CommentRead(BaseModel):
    id: int
    review_id: int
    section_id: int | None = None
    reviewer_user_id: int
    comment_text: str
    severity: str
    status: str
    resolution_note: str | None = None
    assigned_to_user_id: int | None = None
    resolved_by_user_id: int | None = None
    verified_by_user_id: int | None = None
    resolved_at: datetime | None = None
    verified_at: datetime | None = None
    anchor_text: str | None = None
    anchor_offset_start: int | None = None
    anchor_offset_end: int | None = None
    is_inline: bool = False
    mentions: list[int] | None = None
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
# Scoring Summary
# ---------------------------------------------------------------------------


class ScoringSummary(BaseModel):
    review_id: int
    review_type: str
    average_score: float | None = None
    min_score: float | None = None
    max_score: float | None = None
    checklist_pass_rate: float = 0.0
    comments_by_severity: dict[str, int] = {}
    resolution_rate: float = 0.0
    total_comments: int = 0
    resolved_comments: int = 0


# ---------------------------------------------------------------------------
# Review Packet
# ---------------------------------------------------------------------------


class ReviewPacketActionItem(BaseModel):
    rank: int
    comment_id: int
    section_id: int | None = None
    severity: str
    status: str
    risk_score: float
    age_days: int
    assigned_to_user_id: int | None = None
    recommended_action: str
    rationale: str


class ReviewPacketChecklistSummary(BaseModel):
    total_items: int = 0
    pass_count: int = 0
    fail_count: int = 0
    pending_count: int = 0
    na_count: int = 0
    pass_rate: float = 0.0


class ReviewPacketRiskSummary(BaseModel):
    open_critical: int = 0
    open_major: int = 0
    unresolved_comments: int = 0
    highest_risk_score: float = 0.0
    overall_risk_level: str


class ReviewPacketRead(BaseModel):
    review_id: int
    proposal_id: int
    proposal_title: str
    review_type: str
    review_status: str
    generated_at: datetime
    checklist_summary: ReviewPacketChecklistSummary
    risk_summary: ReviewPacketRiskSummary
    action_queue: list[ReviewPacketActionItem]
    recommended_exit_criteria: list[str]


# ---------------------------------------------------------------------------
# List wrapper
# ---------------------------------------------------------------------------


class ReviewListResponse(BaseModel):
    items: list[ReviewRead]
    total: int
