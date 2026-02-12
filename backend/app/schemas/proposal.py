"""
RFP Sniper - Proposal Schemas
=============================
Request/Response models for proposal endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.proposal import (
    Citation,
    DataClassification,
    ProposalStatus,
    SectionStatus,
    SubmissionPackageStatus,
)

# =============================================================================
# Proposal Schemas
# =============================================================================


class ProposalCreate(BaseModel):
    """Schema for creating a new proposal."""

    rfp_id: int
    title: str = Field(max_length=500)
    classification: DataClassification = DataClassification.INTERNAL


class ProposalRead(BaseModel):
    """Schema for reading proposal data."""

    id: int
    user_id: int
    rfp_id: int
    title: str
    version: int
    status: ProposalStatus
    classification: DataClassification
    executive_summary: str | None
    total_sections: int
    completed_sections: int
    compliance_score: float | None
    docx_export_path: str | None
    pdf_export_path: str | None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    completion_percentage: float = 0.0

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_completion(cls, proposal) -> "ProposalRead":
        """Create from ORM with computed completion."""
        data = {
            "id": proposal.id,
            "user_id": proposal.user_id,
            "rfp_id": proposal.rfp_id,
            "title": proposal.title,
            "version": proposal.version,
            "status": proposal.status,
            "classification": proposal.classification,
            "executive_summary": proposal.executive_summary,
            "total_sections": proposal.total_sections,
            "completed_sections": proposal.completed_sections,
            "compliance_score": proposal.compliance_score,
            "docx_export_path": proposal.docx_export_path,
            "pdf_export_path": proposal.pdf_export_path,
            "created_at": proposal.created_at,
            "updated_at": proposal.updated_at,
            "submitted_at": proposal.submitted_at,
            "completion_percentage": proposal.calculate_completion(),
        }
        return cls(**data)


class ProposalUpdate(BaseModel):
    """Schema for updating proposal."""

    title: str | None = Field(default=None, max_length=500)
    status: ProposalStatus | None = None
    classification: DataClassification | None = None
    executive_summary: str | None = None


# =============================================================================
# Proposal Section Schemas
# =============================================================================


class ProposalSectionCreate(BaseModel):
    """Schema for creating a proposal section."""

    title: str = Field(max_length=255)
    section_number: str = Field(max_length=50)
    requirement_id: str | None = None
    requirement_text: str | None = None
    writing_plan: str | None = None
    display_order: int = 0


class GeneratedContentRead(BaseModel):
    """Schema for reading generated content."""

    raw_text: str
    clean_text: str
    citations: list[Citation]
    model_used: str
    tokens_used: int
    generation_time_seconds: float


class ProposalSectionRead(BaseModel):
    """Schema for reading proposal section."""

    id: int
    proposal_id: int
    title: str
    section_number: str
    requirement_id: str | None
    requirement_text: str | None
    writing_plan: str | None
    status: SectionStatus
    generated_content: GeneratedContentRead | None
    final_content: str | None
    word_count: int | None
    quality_score: float | None = None
    quality_breakdown: dict | None = None
    display_order: int
    assigned_to_user_id: int | None = None
    assigned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    generated_at: datetime | None

    model_config = {"from_attributes": True}


class ProposalSectionUpdate(BaseModel):
    """Schema for updating proposal section."""

    title: str | None = Field(default=None, max_length=255)
    section_number: str | None = Field(default=None, max_length=50)
    requirement_id: str | None = None
    requirement_text: str | None = None
    writing_plan: str | None = None
    final_content: str | None = None
    status: SectionStatus | None = None
    display_order: int | None = None


# =============================================================================
# Evidence Schemas
# =============================================================================


class SectionEvidenceCreate(BaseModel):
    """Schema for linking evidence to a section."""

    document_id: int
    chunk_id: int | None = None
    citation: str | None = None
    notes: str | None = None


class SectionEvidenceRead(BaseModel):
    """Schema for reading evidence links."""

    id: int
    section_id: int
    document_id: int
    chunk_id: int | None
    citation: str | None
    notes: str | None
    created_at: datetime
    document_title: str | None = None
    document_filename: str | None = None

    model_config = {"from_attributes": True}


# =============================================================================
# Submission Package Schemas
# =============================================================================


class SubmissionPackageCreate(BaseModel):
    """Schema for creating a submission package."""

    title: str = Field(max_length=255)
    due_date: datetime | None = None
    owner_id: int | None = None
    checklist: list[dict] | None = None
    notes: str | None = None


class SubmissionPackageUpdate(BaseModel):
    """Schema for updating a submission package."""

    title: str | None = Field(default=None, max_length=255)
    due_date: datetime | None = None
    owner_id: int | None = None
    status: SubmissionPackageStatus | None = None
    checklist: list[dict] | None = None
    notes: str | None = None


class SubmissionPackageRead(BaseModel):
    """Schema for reading a submission package."""

    id: int
    proposal_id: int
    owner_id: int | None
    title: str
    status: SubmissionPackageStatus
    due_date: datetime | None
    submitted_at: datetime | None
    checklist: list[dict]
    notes: str | None
    docx_export_path: str | None
    pdf_export_path: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Draft Generation Schemas
# =============================================================================


class RewriteRequest(BaseModel):
    """Request to rewrite a section with a new tone or instructions."""

    tone: str = Field(default="professional", pattern="^(professional|technical|executive)$")
    instructions: str | None = None


class ExpandRequest(BaseModel):
    """Request to expand a section with more detail."""

    target_words: int = Field(default=800, ge=100, le=3000)
    focus_area: str | None = None


class DraftRequest(BaseModel):
    """Request to generate draft for a requirement."""

    requirement_id: str
    rfp_id: int | None = None
    additional_context: str | None = None
    max_words: int = Field(default=500, ge=50, le=2000)
    tone: str = Field(default="professional", pattern="^(professional|technical|executive)$")
    include_citations: bool = True


class DraftResponse(BaseModel):
    """Response from draft generation."""

    task_id: str
    requirement_id: str
    section_id: int | None = None
    message: str
    status: str = "generating"


class DraftResult(BaseModel):
    """Final result of draft generation (returned via polling or webhook)."""

    section_id: int
    requirement_id: str
    raw_text: str
    clean_text: str
    citations: list[Citation]
    word_count: int
    model_used: str
    tokens_used: int
    generation_time_seconds: float
    status: str = "completed"
