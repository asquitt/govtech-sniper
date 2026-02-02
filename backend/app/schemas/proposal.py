"""
RFP Sniper - Proposal Schemas
=============================
Request/Response models for proposal endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.proposal import ProposalStatus, SectionStatus, Citation


# =============================================================================
# Proposal Schemas
# =============================================================================

class ProposalCreate(BaseModel):
    """Schema for creating a new proposal."""
    rfp_id: int
    title: str = Field(max_length=500)


class ProposalRead(BaseModel):
    """Schema for reading proposal data."""
    id: int
    user_id: int
    rfp_id: int
    title: str
    version: int
    status: ProposalStatus
    executive_summary: Optional[str]
    total_sections: int
    completed_sections: int
    compliance_score: Optional[float]
    docx_export_path: Optional[str]
    pdf_export_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]
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
    title: Optional[str] = Field(default=None, max_length=500)
    status: Optional[ProposalStatus] = None
    executive_summary: Optional[str] = None


# =============================================================================
# Proposal Section Schemas
# =============================================================================

class ProposalSectionCreate(BaseModel):
    """Schema for creating a proposal section."""
    title: str = Field(max_length=255)
    section_number: str = Field(max_length=50)
    requirement_id: Optional[str] = None
    requirement_text: Optional[str] = None
    display_order: int = 0


class GeneratedContentRead(BaseModel):
    """Schema for reading generated content."""
    raw_text: str
    clean_text: str
    citations: List[Citation]
    model_used: str
    tokens_used: int
    generation_time_seconds: float


class ProposalSectionRead(BaseModel):
    """Schema for reading proposal section."""
    id: int
    proposal_id: int
    title: str
    section_number: str
    requirement_id: Optional[str]
    requirement_text: Optional[str]
    status: SectionStatus
    generated_content: Optional[GeneratedContentRead]
    final_content: Optional[str]
    word_count: Optional[int]
    display_order: int
    created_at: datetime
    updated_at: datetime
    generated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProposalSectionUpdate(BaseModel):
    """Schema for updating proposal section."""
    title: Optional[str] = Field(default=None, max_length=255)
    final_content: Optional[str] = None
    status: Optional[SectionStatus] = None


# =============================================================================
# Draft Generation Schemas
# =============================================================================

class DraftRequest(BaseModel):
    """Request to generate draft for a requirement."""
    requirement_id: str
    additional_context: Optional[str] = None
    max_words: int = Field(default=500, ge=50, le=2000)
    tone: str = Field(default="professional", pattern="^(professional|technical|executive)$")
    include_citations: bool = True


class DraftResponse(BaseModel):
    """Response from draft generation."""
    task_id: str
    requirement_id: str
    section_id: Optional[int] = None
    message: str
    status: str = "generating"


class DraftResult(BaseModel):
    """Final result of draft generation (returned via polling or webhook)."""
    section_id: int
    requirement_id: str
    raw_text: str
    clean_text: str
    citations: List[Citation]
    word_count: int
    model_used: str
    tokens_used: int
    generation_time_seconds: float
    status: str = "completed"

