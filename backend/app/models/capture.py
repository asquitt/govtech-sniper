"""
RFP Sniper - Capture Models
===========================
Capture pipeline, bid decisions, and teaming partners.
"""

from datetime import date, datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel, Text


class CaptureStage(str, Enum):
    IDENTIFIED = "identified"
    QUALIFIED = "qualified"
    PURSUIT = "pursuit"
    PROPOSAL = "proposal"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"


class BidDecision(str, Enum):
    PENDING = "pending"
    BID = "bid"
    NO_BID = "no_bid"


class CapturePlan(SQLModel, table=True):
    """
    Capture plan for an opportunity.
    """

    __tablename__ = "capture_plans"

    id: int | None = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True, unique=True)
    owner_id: int = Field(foreign_key="users.id", index=True)

    stage: CaptureStage = Field(default=CaptureStage.IDENTIFIED)
    bid_decision: BidDecision = Field(default=BidDecision.PENDING)
    win_probability: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GateReview(SQLModel, table=True):
    """
    Capture gate review record.
    """

    __tablename__ = "gate_reviews"

    id: int | None = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)
    reviewer_id: int = Field(foreign_key="users.id", index=True)

    stage: CaptureStage = Field(default=CaptureStage.QUALIFIED)
    decision: BidDecision = Field(default=BidDecision.PENDING)
    notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class TeamingPartner(SQLModel, table=True):
    """
    Teaming partner directory.
    """

    __tablename__ = "teaming_partners"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    partner_type: str | None = Field(default=None, max_length=100)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    # Extended fields for teaming board
    company_duns: str | None = Field(default=None, max_length=20)
    cage_code: str | None = Field(default=None, max_length=10)
    naics_codes: list = Field(default=[], sa_column=Column(JSON))
    set_asides: list = Field(default=[], sa_column=Column(JSON))
    capabilities: list = Field(default=[], sa_column=Column(JSON))
    clearance_level: str | None = Field(default=None, max_length=50)
    past_performance_summary: str | None = None
    website: str | None = Field(default=None, max_length=500)
    is_public: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RFPTeamingPartner(SQLModel, table=True):
    """
    Link table between RFPs and teaming partners.
    """

    __tablename__ = "rfp_teaming_partners"

    id: int | None = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)
    partner_id: int = Field(foreign_key="teaming_partners.id", index=True)
    role: str | None = Field(default=None, max_length=255)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class CaptureFieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    DATE = "date"
    BOOLEAN = "boolean"


class CaptureCustomField(SQLModel, table=True):
    """
    Custom fields for capture plans.
    """

    __tablename__ = "capture_custom_fields"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    field_type: CaptureFieldType = Field(default=CaptureFieldType.TEXT)
    options: list = Field(default=[], sa_column=Column(JSON))
    stage: CaptureStage | None = Field(default=None)
    is_required: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CaptureFieldValue(SQLModel, table=True):
    """
    Values for custom fields on a capture plan.
    """

    __tablename__ = "capture_field_values"

    id: int | None = Field(default=None, primary_key=True)
    capture_plan_id: int = Field(foreign_key="capture_plans.id", index=True)
    field_id: int = Field(foreign_key="capture_custom_fields.id", index=True)

    value: dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CaptureCompetitor(SQLModel, table=True):
    """
    Competitive intelligence entries for an opportunity.
    """

    __tablename__ = "capture_competitors"

    id: int | None = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    incumbent: bool = Field(default=False)
    strengths: str | None = None
    weaknesses: str | None = None
    notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ActivityStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class CaptureActivity(SQLModel, table=True):
    """
    Timeline activity for a capture plan (Gantt chart items).
    """

    __tablename__ = "capture_activities"

    id: int | None = Field(default=None, primary_key=True)
    capture_plan_id: int = Field(foreign_key="capture_plans.id", index=True)

    title: str = Field(max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    is_milestone: bool = Field(default=False)
    status: ActivityStatus = Field(default=ActivityStatus.PLANNED)
    sort_order: int = Field(default=0)
    depends_on_id: int | None = Field(default=None, foreign_key="capture_activities.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamingRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class TeamingRequest(SQLModel, table=True):
    """
    Teaming request between users and partners.
    """

    __tablename__ = "teaming_requests"

    id: int | None = Field(default=None, primary_key=True)
    from_user_id: int = Field(foreign_key="users.id", index=True)
    to_partner_id: int = Field(foreign_key="teaming_partners.id", index=True)
    rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)
    message: str | None = None
    status: TeamingRequestStatus = Field(default=TeamingRequestStatus.PENDING)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BidScorecardRecommendation(str, Enum):
    BID = "bid"
    NO_BID = "no_bid"
    CONDITIONAL = "conditional"


class ScorerType(str, Enum):
    AI = "ai"
    HUMAN = "human"


class BidScorecard(SQLModel, table=True):
    """Individual bid/no-bid scorecard from AI or a human team member."""

    __tablename__ = "bid_scorecards"

    id: int | None = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    criteria_scores: list[dict] = Field(default=[], sa_column=Column(JSON))
    overall_score: float | None = None
    recommendation: BidScorecardRecommendation | None = None
    confidence: float | None = None
    reasoning: str | None = Field(default=None, sa_column=Column(Text))

    scorer_type: ScorerType = Field(default=ScorerType.AI)
    scorer_id: int | None = None  # user_id if human scorer

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
