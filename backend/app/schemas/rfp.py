"""
RFP Sniper - RFP Schemas
========================
Request/Response models for RFP endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, HttpUrl, computed_field, model_validator

from app.models.rfp import ImportanceLevel, RequirementStatus, RFPStatus, RFPType


# =============================================================================
# SAM.gov Integration Schemas
# =============================================================================

class SAMSearchParams(BaseModel):
    """Parameters for SAM.gov opportunity search."""
    keywords: str = Field(min_length=1, max_length=500)
    days_back: int = Field(default=90, ge=1, le=365)
    limit: int = Field(default=25, ge=1, le=100)
    naics_codes: Optional[List[str]] = None
    set_aside_types: Optional[List[str]] = None
    active_only: bool = True


class SAMOpportunity(BaseModel):
    """Single opportunity from SAM.gov API."""
    title: str
    solicitation_number: str
    agency: str
    sub_agency: Optional[str] = None
    posted_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    naics_code: Optional[str] = None
    set_aside: Optional[str] = None
    rfp_type: RFPType
    ui_link: Optional[str] = None
    description: Optional[str] = None


class SAMIngestResponse(BaseModel):
    """Response from SAM.gov ingest endpoint."""
    task_id: str
    message: str
    status: str = "processing"
    opportunities_found: Optional[int] = None


class SAMOpportunitySnapshotSummary(BaseModel):
    """Summary fields extracted from a SAM.gov opportunity snapshot."""
    notice_id: Optional[str] = None
    solicitation_number: Optional[str] = None
    title: Optional[str] = None
    posted_date: Optional[str] = None
    response_deadline: Optional[str] = None
    agency: Optional[str] = None
    sub_agency: Optional[str] = None
    naics_code: Optional[str] = None
    set_aside: Optional[str] = None
    rfp_type: Optional[str] = None
    ui_link: Optional[str] = None
    resource_links_count: int = 0
    resource_links_hash: Optional[str] = None
    description_length: int = 0
    description_hash: Optional[str] = None


class SAMOpportunitySnapshotRead(BaseModel):
    """Snapshot record for change tracking."""
    id: int
    notice_id: str
    solicitation_number: Optional[str]
    rfp_id: Optional[int]
    user_id: Optional[int]
    fetched_at: datetime
    posted_date: Optional[datetime]
    response_deadline: Optional[datetime]
    raw_hash: str
    summary: SAMOpportunitySnapshotSummary
    raw_payload: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class SAMOpportunityFieldChange(BaseModel):
    field: str
    from_value: Optional[Any] = None
    to_value: Optional[Any] = None


class SAMOpportunitySnapshotDiff(BaseModel):
    """Diff between two snapshots."""
    from_snapshot_id: int
    to_snapshot_id: int
    changes: List[SAMOpportunityFieldChange]
    summary_from: SAMOpportunitySnapshotSummary
    summary_to: SAMOpportunitySnapshotSummary


# =============================================================================
# RFP Schemas
# =============================================================================

class RFPCreate(BaseModel):
    """Schema for manually creating an RFP."""
    title: str = Field(max_length=500)
    solicitation_number: str = Field(max_length=100)
    agency: str = Field(max_length=255)
    sub_agency: Optional[str] = Field(default=None, max_length=255)
    naics_code: Optional[str] = Field(default=None, max_length=10)
    set_aside: Optional[str] = Field(default=None, max_length=100)
    posted_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    source_url: Optional[str] = None
    description: Optional[str] = None
    estimated_value: Optional[int] = None
    place_of_performance: Optional[str] = None
    source_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    contract_vehicle: Optional[str] = None
    incumbent_vendor: Optional[str] = None
    buyer_contact_name: Optional[str] = None
    buyer_contact_email: Optional[str] = None
    buyer_contact_phone: Optional[str] = None
    budget_estimate: Optional[int] = None
    competitive_landscape: Optional[str] = None
    intel_notes: Optional[str] = None


class RFPRead(BaseModel):
    """Schema for reading full RFP data."""
    id: int
    user_id: int
    title: str
    solicitation_number: str
    agency: str
    sub_agency: Optional[str]
    naics_code: Optional[str]
    set_aside: Optional[str]
    rfp_type: RFPType
    status: RFPStatus
    posted_date: Optional[datetime]
    response_deadline: Optional[datetime]
    source_url: Optional[str]
    sam_gov_link: Optional[str]
    description: Optional[str]
    summary: Optional[str]
    is_qualified: Optional[bool]
    qualification_reason: Optional[str]
    qualification_score: Optional[float]
    estimated_value: Optional[int]
    place_of_performance: Optional[str]
    source_type: Optional[str]
    jurisdiction: Optional[str]
    contract_vehicle: Optional[str]
    incumbent_vendor: Optional[str]
    buyer_contact_name: Optional[str]
    buyer_contact_email: Optional[str]
    buyer_contact_phone: Optional[str]
    budget_estimate: Optional[int]
    competitive_landscape: Optional[str]
    intel_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    analyzed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RFPUpdate(BaseModel):
    """Schema for updating RFP data."""
    title: Optional[str] = Field(default=None, max_length=500)
    status: Optional[RFPStatus] = None
    description: Optional[str] = None
    response_deadline: Optional[datetime] = None
    is_qualified: Optional[bool] = None
    qualification_reason: Optional[str] = None
    qualification_score: Optional[float] = None
    estimated_value: Optional[int] = None
    place_of_performance: Optional[str] = None
    source_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    contract_vehicle: Optional[str] = None
    incumbent_vendor: Optional[str] = None
    buyer_contact_name: Optional[str] = None
    buyer_contact_email: Optional[str] = None
    buyer_contact_phone: Optional[str] = None
    budget_estimate: Optional[int] = None
    competitive_landscape: Optional[str] = None
    intel_notes: Optional[str] = None


class RFPListItem(BaseModel):
    """Condensed RFP for list views."""
    id: int
    title: str
    solicitation_number: str
    agency: str
    status: RFPStatus
    is_qualified: Optional[bool]
    qualification_score: Optional[float]
    response_deadline: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def recommendation_score(self) -> float:
        """
        Lightweight recommendation score for sorting.
        Combines qualification score and deadline urgency.
        """
        base = float(self.qualification_score) if self.qualification_score is not None else 50.0
        bonus = 0.0
        penalty = 0.0

        if self.response_deadline:
            days_left = (self.response_deadline - datetime.utcnow()).days
            if days_left < 0:
                penalty += 30.0
            elif days_left <= 3:
                bonus += 10.0
            elif days_left <= 7:
                bonus += 5.0
            elif days_left > 30:
                penalty += 5.0

        score = max(0.0, min(100.0, base + bonus - penalty))
        return round(score, 2)


# =============================================================================
# Compliance Matrix Schemas
# =============================================================================

class ComplianceRequirementRead(BaseModel):
    """Single requirement from compliance matrix."""
    id: str
    section: str
    source_section: Optional[str] = None
    requirement_text: str
    importance: ImportanceLevel
    category: Optional[str]
    page_reference: Optional[int]
    keywords: List[str]
    is_addressed: bool
    notes: Optional[str]
    status: RequirementStatus = RequirementStatus.OPEN
    assigned_to: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def default_status(cls, values: dict) -> dict:
        if isinstance(values, dict) and not values.get("status"):
            values["status"] = (
                RequirementStatus.ADDRESSED
                if values.get("is_addressed")
                else RequirementStatus.OPEN
            )
        return values


class ComplianceRequirementCreate(BaseModel):
    """Create a new compliance requirement."""
    id: Optional[str] = None
    section: str
    source_section: Optional[str] = None
    requirement_text: str
    importance: ImportanceLevel
    category: Optional[str] = None
    page_reference: Optional[int] = None
    keywords: List[str] = Field(default_factory=list)
    is_addressed: bool = False
    notes: Optional[str] = None
    status: RequirementStatus = RequirementStatus.OPEN
    assigned_to: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ComplianceRequirementUpdate(BaseModel):
    """Update fields on a compliance requirement."""
    section: Optional[str] = None
    source_section: Optional[str] = None
    requirement_text: Optional[str] = None
    importance: Optional[ImportanceLevel] = None
    category: Optional[str] = None
    page_reference: Optional[int] = None
    keywords: Optional[List[str]] = None
    is_addressed: Optional[bool] = None
    notes: Optional[str] = None
    status: Optional[RequirementStatus] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


class ComplianceMatrixRead(BaseModel):
    """Schema for reading compliance matrix."""
    id: int
    rfp_id: int
    requirements: List[ComplianceRequirementRead]
    total_requirements: int
    mandatory_count: int
    addressed_count: int
    extraction_confidence: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Analysis Schemas
# =============================================================================

class AnalyzeRequest(BaseModel):
    """Request to analyze an RFP."""
    force_reanalyze: bool = False


class AnalyzeResponse(BaseModel):
    """Response from RFP analysis endpoint."""
    task_id: str
    rfp_id: int
    message: str
    status: str = "analyzing"
