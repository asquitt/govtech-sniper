"""
RFP Sniper - RFP Schemas
========================
Request/Response models for RFP endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.models.rfp import ImportanceLevel, RequirementStatus, RFPStatus, RFPType

# =============================================================================
# SAM.gov Integration Schemas
# =============================================================================


class SAMSearchParams(BaseModel):
    """Parameters for SAM.gov opportunity search."""

    keywords: str = Field(min_length=1, max_length=500)
    days_back: int = Field(default=90, ge=1, le=365)
    limit: int = Field(default=25, ge=1, le=100)
    naics_codes: list[str] | None = None
    set_aside_types: list[str] | None = None
    active_only: bool = True


class SAMOpportunity(BaseModel):
    """Single opportunity from SAM.gov API."""

    title: str
    solicitation_number: str
    agency: str
    sub_agency: str | None = None
    posted_date: datetime | None = None
    response_deadline: datetime | None = None
    naics_code: str | None = None
    set_aside: str | None = None
    rfp_type: RFPType
    ui_link: str | None = None
    description: str | None = None


class SAMIngestResponse(BaseModel):
    """Response from SAM.gov ingest endpoint."""

    task_id: str
    message: str
    status: str = "processing"
    opportunities_found: int | None = None


class SAMOpportunitySnapshotSummary(BaseModel):
    """Summary fields extracted from a SAM.gov opportunity snapshot."""

    notice_id: str | None = None
    solicitation_number: str | None = None
    title: str | None = None
    posted_date: str | None = None
    response_deadline: str | None = None
    agency: str | None = None
    sub_agency: str | None = None
    naics_code: str | None = None
    set_aside: str | None = None
    rfp_type: str | None = None
    ui_link: str | None = None
    resource_links_count: int = 0
    resource_links_hash: str | None = None
    description_length: int = 0
    description_hash: str | None = None


class SAMOpportunitySnapshotRead(BaseModel):
    """Snapshot record for change tracking."""

    id: int
    notice_id: str
    solicitation_number: str | None
    rfp_id: int | None
    user_id: int | None
    fetched_at: datetime
    posted_date: datetime | None
    response_deadline: datetime | None
    raw_hash: str
    summary: SAMOpportunitySnapshotSummary
    raw_payload: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class SAMOpportunityFieldChange(BaseModel):
    field: str
    from_value: Any | None = None
    to_value: Any | None = None


class SAMOpportunitySnapshotDiff(BaseModel):
    """Diff between two snapshots."""

    from_snapshot_id: int
    to_snapshot_id: int
    changes: list[SAMOpportunityFieldChange]
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
    sub_agency: str | None = Field(default=None, max_length=255)
    naics_code: str | None = Field(default=None, max_length=10)
    set_aside: str | None = Field(default=None, max_length=100)
    posted_date: datetime | None = None
    response_deadline: datetime | None = None

    @field_validator("posted_date", "response_deadline", mode="after")
    @classmethod
    def strip_timezone(cls, v: datetime | None) -> datetime | None:
        """DB uses TIMESTAMP WITHOUT TIME ZONE — normalize to naive UTC."""
        if v is not None and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

    source_url: str | None = None
    description: str | None = None
    estimated_value: int | None = None
    place_of_performance: str | None = None
    source_type: str | None = None
    jurisdiction: str | None = None
    contract_vehicle: str | None = None
    incumbent_vendor: str | None = None
    buyer_contact_name: str | None = None
    buyer_contact_email: str | None = None
    buyer_contact_phone: str | None = None
    budget_estimate: int | None = None
    competitive_landscape: str | None = None
    intel_notes: str | None = None


class RFPRead(BaseModel):
    """Schema for reading full RFP data."""

    id: int
    user_id: int
    title: str
    solicitation_number: str
    agency: str
    sub_agency: str | None
    naics_code: str | None
    set_aside: str | None
    rfp_type: RFPType
    status: RFPStatus
    posted_date: datetime | None
    response_deadline: datetime | None
    source_url: str | None
    sam_gov_link: str | None
    description: str | None
    summary: str | None
    is_qualified: bool | None
    qualification_reason: str | None
    qualification_score: float | None
    estimated_value: int | None
    place_of_performance: str | None
    source_type: str | None
    jurisdiction: str | None
    contract_vehicle: str | None
    incumbent_vendor: str | None
    buyer_contact_name: str | None
    buyer_contact_email: str | None
    buyer_contact_phone: str | None
    budget_estimate: int | None
    competitive_landscape: str | None
    intel_notes: str | None
    match_score: float | None = None
    match_reasoning: str | None = None
    match_details: dict | None = None
    created_at: datetime
    updated_at: datetime
    analyzed_at: datetime | None

    model_config = {"from_attributes": True}


class RFPUpdate(BaseModel):
    """Schema for updating RFP data."""

    title: str | None = Field(default=None, max_length=500)
    status: RFPStatus | None = None
    description: str | None = None
    response_deadline: datetime | None = None
    is_qualified: bool | None = None
    qualification_reason: str | None = None
    qualification_score: float | None = None
    estimated_value: int | None = None
    place_of_performance: str | None = None
    source_type: str | None = None
    jurisdiction: str | None = None
    contract_vehicle: str | None = None
    incumbent_vendor: str | None = None
    buyer_contact_name: str | None = None
    buyer_contact_email: str | None = None
    buyer_contact_phone: str | None = None
    budget_estimate: int | None = None
    competitive_landscape: str | None = None
    intel_notes: str | None = None


class RFPListItem(BaseModel):
    """Condensed RFP for list views."""

    id: int
    title: str
    solicitation_number: str
    agency: str
    status: RFPStatus
    is_qualified: bool | None
    qualification_score: float | None
    match_score: float | None = None
    response_deadline: datetime | None
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
    source_section: str | None = None
    requirement_text: str
    importance: ImportanceLevel
    category: str | None
    page_reference: int | None
    keywords: list[str]
    is_addressed: bool
    notes: str | None
    confidence: float = 0.0
    status: RequirementStatus = RequirementStatus.OPEN
    assigned_to: str | None = None
    tags: list[str] = Field(default_factory=list)

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

    id: str | None = None
    section: str
    source_section: str | None = None
    requirement_text: str
    importance: ImportanceLevel
    category: str | None = None
    page_reference: int | None = None
    keywords: list[str] = Field(default_factory=list)
    is_addressed: bool = False
    notes: str | None = None
    status: RequirementStatus = RequirementStatus.OPEN
    assigned_to: str | None = None
    tags: list[str] = Field(default_factory=list)


class ComplianceRequirementUpdate(BaseModel):
    """Update fields on a compliance requirement."""

    section: str | None = None
    source_section: str | None = None
    requirement_text: str | None = None
    importance: ImportanceLevel | None = None
    category: str | None = None
    page_reference: int | None = None
    keywords: list[str] | None = None
    is_addressed: bool | None = None
    notes: str | None = None
    status: RequirementStatus | None = None
    assigned_to: str | None = None
    tags: list[str] | None = None


class ComplianceMatrixRead(BaseModel):
    """Schema for reading compliance matrix."""

    id: int
    rfp_id: int
    requirements: list[ComplianceRequirementRead]
    total_requirements: int
    mandatory_count: int
    addressed_count: int
    extraction_confidence: float | None
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
