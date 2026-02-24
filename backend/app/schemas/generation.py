"""Response models for generation, outline, auth, and subscription endpoints."""

from pydantic import BaseModel


class MatrixGenerationResponse(BaseModel):
    proposal_id: int
    sections_created: int
    message: str


class GenerationProgressResponse(BaseModel):
    proposal_id: int
    total: int
    completed: int
    pending: int
    generating: int
    generated: int
    editing: int
    approved: int
    completion_percentage: float


class BatchGenerationResponse(BaseModel):
    task_id: str
    proposal_id: int
    message: str
    status: str


class CacheRefreshResponse(BaseModel):
    task_id: str
    message: str
    ttl_hours: int


class GenerationStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class OutlineTaskResponse(BaseModel):
    task_id: str
    message: str
    status: str


class OutlineDeleteResponse(BaseModel):
    message: str
    section_id: int


class OutlineReorderResponse(BaseModel):
    message: str
    sections_updated: int


class OutlineApproveResponse(BaseModel):
    message: str
    sections_created: int
    outline_id: int


class StatusMessageResponse(BaseModel):
    """Generic status + message response (e.g. MFA verify/disable)."""

    status: str
    message: str


class MessageResponse(BaseModel):
    """Generic message-only response."""

    message: str


class LogoutResponse(BaseModel):
    message: str
    note: str


class SubscriptionStatusResponse(BaseModel):
    tier: str
    status: str
    expires_at: str | None = None
    has_stripe_customer: bool
    has_subscription: bool


class BidEvaluateResponse(BaseModel):
    id: int
    rfp_id: int
    overall_score: float | None = None
    recommendation: str | None = None
    confidence: float | None = None
    criteria_scores: list[dict]
    reasoning: str | None = None
    win_probability: float | None = None


class BidVoteResponse(BaseModel):
    id: int
    rfp_id: int
    overall_score: float | None = None
    recommendation: str | None = None
    scorer_type: str
    scorer_id: int | None = None


class BidSummaryResponse(BaseModel):
    rfp_id: int
    total_votes: int
    ai_score: float | None = None
    human_avg: float | None = None
    overall_recommendation: str | None = None
    bid_count: int
    no_bid_count: int
    conditional_count: int
