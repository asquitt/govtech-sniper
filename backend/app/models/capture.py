"""
RFP Sniper - Capture Models
===========================
Capture pipeline, bid decisions, and teaming partners.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel, Column, JSON


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

    id: Optional[int] = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True, unique=True)
    owner_id: int = Field(foreign_key="users.id", index=True)

    stage: CaptureStage = Field(default=CaptureStage.IDENTIFIED)
    bid_decision: BidDecision = Field(default=BidDecision.PENDING)
    win_probability: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GateReview(SQLModel, table=True):
    """
    Capture gate review record.
    """
    __tablename__ = "gate_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)
    reviewer_id: int = Field(foreign_key="users.id", index=True)

    stage: CaptureStage = Field(default=CaptureStage.QUALIFIED)
    decision: BidDecision = Field(default=BidDecision.PENDING)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class TeamingPartner(SQLModel, table=True):
    """
    Teaming partner directory.
    """
    __tablename__ = "teaming_partners"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    partner_type: Optional[str] = Field(default=None, max_length=100)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RFPTeamingPartner(SQLModel, table=True):
    """
    Link table between RFPs and teaming partners.
    """
    __tablename__ = "rfp_teaming_partners"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)
    partner_id: int = Field(foreign_key="teaming_partners.id", index=True)
    role: Optional[str] = Field(default=None, max_length=255)

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

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=255)
    field_type: CaptureFieldType = Field(default=CaptureFieldType.TEXT)
    options: list = Field(default=[], sa_column=Column(JSON))
    stage: Optional[CaptureStage] = Field(default=None)
    is_required: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CaptureFieldValue(SQLModel, table=True):
    """
    Values for custom fields on a capture plan.
    """
    __tablename__ = "capture_field_values"

    id: Optional[int] = Field(default=None, primary_key=True)
    capture_plan_id: int = Field(foreign_key="capture_plans.id", index=True)
    field_id: int = Field(foreign_key="capture_custom_fields.id", index=True)

    value: dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
