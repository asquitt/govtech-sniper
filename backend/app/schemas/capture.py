"""
RFP Sniper - Capture Schemas
============================
Request/response models for capture pipeline.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.capture import CaptureStage, BidDecision


class CapturePlanCreate(BaseModel):
    rfp_id: int
    stage: CaptureStage = CaptureStage.IDENTIFIED
    bid_decision: BidDecision = BidDecision.PENDING
    win_probability: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None


class CapturePlanUpdate(BaseModel):
    stage: Optional[CaptureStage] = None
    bid_decision: Optional[BidDecision] = None
    win_probability: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None


class CapturePlanRead(BaseModel):
    id: int
    rfp_id: int
    owner_id: int
    stage: CaptureStage
    bid_decision: BidDecision
    win_probability: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GateReviewCreate(BaseModel):
    rfp_id: int
    stage: CaptureStage = CaptureStage.QUALIFIED
    decision: BidDecision = BidDecision.PENDING
    notes: Optional[str] = None


class GateReviewRead(BaseModel):
    id: int
    rfp_id: int
    reviewer_id: int
    stage: CaptureStage
    decision: BidDecision
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerCreate(BaseModel):
    name: str
    partner_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class TeamingPartnerUpdate(BaseModel):
    name: Optional[str] = None
    partner_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class TeamingPartnerRead(BaseModel):
    id: int
    name: str
    partner_type: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerLinkCreate(BaseModel):
    rfp_id: int
    partner_id: int
    role: Optional[str] = None


class TeamingPartnerLinkRead(BaseModel):
    id: int
    rfp_id: int
    partner_id: int
    role: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerLinkList(BaseModel):
    links: List[TeamingPartnerLinkRead]
    total: int
