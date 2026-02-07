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
