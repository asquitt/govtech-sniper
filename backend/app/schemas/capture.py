"""
RFP Sniper - Capture Schemas
============================
Request/response models for capture pipeline.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.capture import BidDecision, CaptureFieldType, CaptureStage


class CapturePlanCreate(BaseModel):
    rfp_id: int
    stage: CaptureStage = CaptureStage.IDENTIFIED
    bid_decision: BidDecision = BidDecision.PENDING
    win_probability: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class CapturePlanUpdate(BaseModel):
    stage: CaptureStage | None = None
    bid_decision: BidDecision | None = None
    win_probability: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class CapturePlanRead(BaseModel):
    id: int
    rfp_id: int
    owner_id: int
    stage: CaptureStage
    bid_decision: BidDecision
    win_probability: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CapturePlanListItem(CapturePlanRead):
    rfp_title: str
    rfp_agency: str | None = None
    rfp_status: str | None = None


class CapturePlanListResponse(BaseModel):
    plans: list[CapturePlanListItem]
    total: int


class GateReviewCreate(BaseModel):
    rfp_id: int
    stage: CaptureStage = CaptureStage.QUALIFIED
    decision: BidDecision = BidDecision.PENDING
    notes: str | None = None


class GateReviewRead(BaseModel):
    id: int
    rfp_id: int
    reviewer_id: int
    stage: CaptureStage
    decision: BidDecision
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerCreate(BaseModel):
    name: str
    partner_type: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    notes: str | None = None


class TeamingPartnerUpdate(BaseModel):
    name: str | None = None
    partner_type: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    notes: str | None = None


class TeamingPartnerRead(BaseModel):
    id: int
    name: str
    partner_type: str | None
    contact_name: str | None
    contact_email: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerLinkCreate(BaseModel):
    rfp_id: int
    partner_id: int
    role: str | None = None


class TeamingPartnerLinkRead(BaseModel):
    id: int
    rfp_id: int
    partner_id: int
    role: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerLinkList(BaseModel):
    links: list[TeamingPartnerLinkRead]
    total: int


# -----------------------------------------------------------------------------
# Custom Fields
# -----------------------------------------------------------------------------


class CaptureFieldCreate(BaseModel):
    name: str
    field_type: CaptureFieldType = CaptureFieldType.TEXT
    options: list[str] | None = None
    stage: CaptureStage | None = None
    is_required: bool = False


class CaptureFieldUpdate(BaseModel):
    name: str | None = None
    field_type: CaptureFieldType | None = None
    options: list[str] | None = None
    stage: CaptureStage | None = None
    is_required: bool | None = None


class CaptureFieldRead(BaseModel):
    id: int
    name: str
    field_type: CaptureFieldType
    options: list[str]
    stage: CaptureStage | None
    is_required: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaptureFieldValueUpdate(BaseModel):
    field_id: int
    value: Any


class CaptureFieldValueRead(BaseModel):
    field: CaptureFieldRead
    value: Any | None = None


class CaptureFieldValueList(BaseModel):
    fields: list[CaptureFieldValueRead]


# -----------------------------------------------------------------------------
# Competitor Intelligence
# -----------------------------------------------------------------------------


class CaptureCompetitorCreate(BaseModel):
    rfp_id: int
    name: str
    incumbent: bool = False
    strengths: str | None = None
    weaknesses: str | None = None
    notes: str | None = None


class CaptureCompetitorUpdate(BaseModel):
    name: str | None = None
    incumbent: bool | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    notes: str | None = None


class CaptureCompetitorRead(BaseModel):
    id: int
    rfp_id: int
    user_id: int
    name: str
    incumbent: bool
    strengths: str | None
    weaknesses: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaptureMatchInsight(BaseModel):
    plan_id: int
    rfp_id: int
    summary: str
    factors: list[dict]
