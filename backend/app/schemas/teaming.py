"""
RFP Sniper - Teaming Board Schemas
===================================
Request/response models for teaming board and partner discovery.
"""

from datetime import datetime

from pydantic import BaseModel


class TeamingPartnerExtended(BaseModel):
    """Full partner profile with all discovery fields."""

    id: int
    user_id: int
    name: str
    partner_type: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    notes: str | None = None
    company_duns: str | None = None
    cage_code: str | None = None
    naics_codes: list[str] = []
    set_asides: list[str] = []
    capabilities: list[str] = []
    clearance_level: str | None = None
    past_performance_summary: str | None = None
    website: str | None = None
    is_public: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerPublicProfile(BaseModel):
    """Public-facing partner profile (excludes internal notes and user_id)."""

    id: int
    name: str
    partner_type: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    company_duns: str | None = None
    cage_code: str | None = None
    naics_codes: list[str] = []
    set_asides: list[str] = []
    capabilities: list[str] = []
    clearance_level: str | None = None
    past_performance_summary: str | None = None
    website: str | None = None

    model_config = {"from_attributes": True}


class TeamingRequestCreate(BaseModel):
    to_partner_id: int
    rfp_id: int | None = None
    message: str | None = None


class TeamingRequestRead(BaseModel):
    id: int
    from_user_id: int
    from_user_name: str | None = None
    from_user_email: str | None = None
    to_partner_id: int
    rfp_id: int | None = None
    message: str | None = None
    status: str
    partner_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingRequestUpdate(BaseModel):
    status: str  # "accepted" or "declined"


class TeamingRequestTrendPointRead(BaseModel):
    date: str
    sent_count: int
    accepted_count: int
    declined_count: int
    fit_score: float


class TeamingRequestTrendRead(BaseModel):
    days: int
    total_sent: int
    accepted_count: int
    declined_count: int
    pending_count: int
    acceptance_rate: float
    points: list[TeamingRequestTrendPointRead]


class PartnerTrendDrilldownRead(BaseModel):
    partner_id: int
    partner_name: str
    sent_count: int
    accepted_count: int
    declined_count: int
    pending_count: int
    acceptance_rate: float
    avg_response_hours: float | None = None


class TeamingPartnerTrendDrilldownResponse(BaseModel):
    days: int
    partners: list[PartnerTrendDrilldownRead]


class TeamingCohortDrilldownRead(BaseModel):
    cohort_value: str
    partner_count: int
    sent_count: int
    accepted_count: int
    declined_count: int
    pending_count: int
    acceptance_rate: float


class TeamingPartnerCohortDrilldownResponse(BaseModel):
    days: int
    total_sent: int
    naics_cohorts: list[TeamingCohortDrilldownRead]
    set_aside_cohorts: list[TeamingCohortDrilldownRead]


class TeamingDigestScheduleRead(BaseModel):
    frequency: str
    day_of_week: int | None = None
    hour_utc: int
    minute_utc: int
    channel: str
    include_declined_reasons: bool
    is_enabled: bool
    last_sent_at: datetime | None = None


class TeamingDigestScheduleUpdate(BaseModel):
    frequency: str = "weekly"
    day_of_week: int | None = 1
    hour_utc: int = 14
    minute_utc: int = 0
    channel: str = "in_app"
    include_declined_reasons: bool = True
    is_enabled: bool = True


# ---------------------------------------------------------------------------
# Capability Gap Analysis
# ---------------------------------------------------------------------------


class CapabilityGapItem(BaseModel):
    gap_type: str  # technical | clearance | naics | past_performance | set_aside
    description: str
    required_value: str | None = None
    matching_partner_ids: list[int] = []


class RecommendedPartner(BaseModel):
    partner_id: int
    name: str
    reason: str


class CapabilityGapResult(BaseModel):
    rfp_id: int
    gaps: list[CapabilityGapItem] = []
    recommended_partners: list[RecommendedPartner] = []
    analysis_summary: str = ""


# ---------------------------------------------------------------------------
# NDA Tracking
# ---------------------------------------------------------------------------


class NDACreate(BaseModel):
    partner_id: int
    rfp_id: int | None = None
    signed_date: str | None = None
    expiry_date: str | None = None
    document_path: str | None = None
    notes: str | None = None


class NDAUpdate(BaseModel):
    status: str | None = None  # draft | sent | signed | expired
    signed_date: str | None = None
    expiry_date: str | None = None
    document_path: str | None = None
    notes: str | None = None


class NDARead(BaseModel):
    id: int
    user_id: int
    partner_id: int
    rfp_id: int | None = None
    status: str
    signed_date: str | None = None
    expiry_date: str | None = None
    document_path: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Performance Ratings
# ---------------------------------------------------------------------------


class PerformanceRatingCreate(BaseModel):
    partner_id: int
    rfp_id: int | None = None
    rating: int  # 1-5
    responsiveness: int | None = None
    quality: int | None = None
    timeliness: int | None = None
    comment: str | None = None


class PerformanceRatingRead(BaseModel):
    id: int
    user_id: int
    partner_id: int
    rfp_id: int | None = None
    rating: int
    responsiveness: int | None = None
    quality: int | None = None
    timeliness: int | None = None
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
