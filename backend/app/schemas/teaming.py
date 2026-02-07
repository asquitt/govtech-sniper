"""
RFP Sniper - Teaming Board Schemas
===================================
Request/response models for teaming board and partner discovery.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class TeamingPartnerExtended(BaseModel):
    """Full partner profile with all discovery fields."""
    id: int
    user_id: int
    name: str
    partner_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    company_duns: Optional[str] = None
    cage_code: Optional[str] = None
    naics_codes: List[str] = []
    set_asides: List[str] = []
    capabilities: List[str] = []
    clearance_level: Optional[str] = None
    past_performance_summary: Optional[str] = None
    website: Optional[str] = None
    is_public: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingPartnerPublicProfile(BaseModel):
    """Public-facing partner profile (excludes internal notes and user_id)."""
    id: int
    name: str
    partner_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    company_duns: Optional[str] = None
    cage_code: Optional[str] = None
    naics_codes: List[str] = []
    set_asides: List[str] = []
    capabilities: List[str] = []
    clearance_level: Optional[str] = None
    past_performance_summary: Optional[str] = None
    website: Optional[str] = None

    model_config = {"from_attributes": True}


class TeamingRequestCreate(BaseModel):
    to_partner_id: int
    rfp_id: Optional[int] = None
    message: Optional[str] = None


class TeamingRequestRead(BaseModel):
    id: int
    from_user_id: int
    to_partner_id: int
    rfp_id: Optional[int] = None
    message: Optional[str] = None
    status: str
    partner_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamingRequestUpdate(BaseModel):
    status: str  # "accepted" or "declined"
