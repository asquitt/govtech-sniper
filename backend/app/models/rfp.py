"""
RFP Sniper - RFP Models
=======================
Solicitation data and compliance matrix.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel
from sqlalchemy import UniqueConstraint
from sqlmodel import JSON, Column, Field, Relationship, SQLModel, Text

if TYPE_CHECKING:
    from app.models.proposal import Proposal
    from app.models.user import User


class RFPStatus(str, Enum):
    """Status of an RFP in the pipeline."""

    NEW = "new"  # Just ingested
    ANALYZING = "analyzing"  # Deep Read in progress
    ANALYZED = "analyzed"  # Compliance matrix extracted
    DRAFTING = "drafting"  # Proposal being written
    READY = "ready"  # Proposal complete
    SUBMITTED = "submitted"  # User marked as submitted
    ARCHIVED = "archived"  # Past deadline or rejected


class RFPType(str, Enum):
    """Type of procurement."""

    SOLICITATION = "solicitation"
    SOURCES_SOUGHT = "sources_sought"
    COMBINED = "combined"
    PRESOLICITATION = "presolicitation"
    AWARD = "award"
    SPECIAL_NOTICE = "special_notice"


class ImportanceLevel(str, Enum):
    """Importance level for compliance requirements."""

    MANDATORY = "mandatory"  # Must comply or disqualified
    EVALUATED = "evaluated"  # Scored in evaluation
    OPTIONAL = "optional"  # Nice to have
    INFORMATIONAL = "informational"


class RequirementStatus(str, Enum):
    """Status for compliance requirement tracking."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    ADDRESSED = "addressed"


# =============================================================================
# Compliance Requirement (Pydantic model for JSON storage)
# =============================================================================


class ComplianceRequirement(BaseModel):
    """
    Single requirement extracted from RFP.
    Stored as JSON array in ComplianceMatrix.
    """

    id: str  # Unique ID (e.g., "REQ-001")
    section: str  # Source section (e.g., "Section L.3.2")
    source_section: str | None = None  # RFP structural section (e.g., "Section C", "Section H")
    requirement_text: str  # The actual requirement
    importance: ImportanceLevel  # How critical is this?
    category: str | None = None  # Grouping (e.g., "Technical", "Past Performance")
    page_reference: int | None = None  # Page number in source PDF
    keywords: list[str] = []  # Key terms for matching
    is_addressed: bool = False  # Has user addressed this?
    notes: str | None = None  # User annotations
    confidence: float = 0.0  # AI extraction confidence (0.0-1.0)
    status: RequirementStatus = RequirementStatus.OPEN
    assigned_to: str | None = None
    tags: list[str] = Field(default_factory=list)


# =============================================================================
# RFP Model
# =============================================================================


class RFPBase(SQLModel):
    """Base RFP fields."""

    title: str = Field(max_length=500, index=True)
    solicitation_number: str = Field(max_length=100, index=True)
    agency: str = Field(max_length=255)
    sub_agency: str | None = Field(default=None, max_length=255)

    # Classification
    naics_code: str | None = Field(default=None, max_length=10)
    set_aside: str | None = Field(default=None, max_length=100)
    rfp_type: RFPType = Field(default=RFPType.SOLICITATION)

    # Dates
    posted_date: datetime | None = None
    response_deadline: datetime | None = None

    # Links
    source_url: str | None = Field(default=None, max_length=1000)
    sam_gov_link: str | None = Field(default=None, max_length=1000)

    # Contract Details
    estimated_value: int | None = None  # In dollars
    place_of_performance: str | None = Field(default=None, max_length=255)

    # Market Intelligence (GovDash/Govly parity fields)
    source_type: str | None = Field(default=None, max_length=50)  # federal | sled | other
    jurisdiction: str | None = Field(default=None, max_length=255)
    contract_vehicle: str | None = Field(default=None, max_length=255)
    incumbent_vendor: str | None = Field(default=None, max_length=255)
    buyer_contact_name: str | None = Field(default=None, max_length=255)
    buyer_contact_email: str | None = Field(default=None, max_length=255)
    buyer_contact_phone: str | None = Field(default=None, max_length=50)
    budget_estimate: int | None = None
    competitive_landscape: str | None = Field(default=None, sa_column=Column(Text))
    intel_notes: str | None = Field(default=None, sa_column=Column(Text))


class RFP(RFPBase, table=True):
    """
    Request for Proposal / Solicitation from SAM.gov.

    Contains the raw solicitation data plus extracted analysis.
    """

    __tablename__ = "rfps"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "solicitation_number",
            name="uq_rfps_user_solicitation_number",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    # Data classification for CUI/FCI policy enforcement
    classification: str = Field(default="internal", max_length=20)

    # Status tracking
    status: RFPStatus = Field(default=RFPStatus.NEW)

    # Full text content (extracted from PDF)
    description: str | None = Field(default=None, sa_column=Column(Text))
    full_text: str | None = Field(default=None, sa_column=Column(Text))

    # AI Analysis Results
    summary: str | None = Field(default=None, sa_column=Column(Text))

    # Killer Filter results
    is_qualified: bool | None = None
    qualification_reason: str | None = Field(default=None, sa_column=Column(Text))
    qualification_score: float | None = None  # 0-100

    # AI Match Score (opportunity matching against user profile)
    match_score: float | None = None  # 0-100
    match_reasoning: str | None = Field(default=None, sa_column=Column(Text))
    match_details: dict | None = Field(default=None, sa_column=Column(JSON))

    # File references
    pdf_file_path: str | None = Field(default=None, max_length=500)
    attachment_paths: list[str] = Field(default=[], sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    analyzed_at: datetime | None = None

    # Relationships
    user: Optional["User"] = Relationship(back_populates="rfps")
    compliance_matrix: Optional["ComplianceMatrix"] = Relationship(back_populates="rfp")
    proposals: list["Proposal"] = Relationship(back_populates="rfp")


# =============================================================================
# Compliance Matrix Model
# =============================================================================


class ComplianceMatrix(SQLModel, table=True):
    """
    Extracted requirements from RFP.
    The "Deep Read" agent populates this via Gemini 1.5 Pro analysis.
    """

    __tablename__ = "compliance_matrices"

    id: int | None = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", unique=True)

    # The extracted requirements (JSON array of ComplianceRequirement)
    requirements: list[dict] = Field(default=[], sa_column=Column(JSON))

    # Summary statistics
    total_requirements: int = Field(default=0)
    mandatory_count: int = Field(default=0)
    addressed_count: int = Field(default=0)

    # AI confidence in extraction
    extraction_confidence: float | None = None  # 0-1

    # Raw AI response for debugging
    raw_ai_response: str | None = Field(default=None, sa_column=Column(Text))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    rfp: RFP | None = Relationship(back_populates="compliance_matrix")

    def get_requirements(self) -> list[ComplianceRequirement]:
        """Parse stored JSON into ComplianceRequirement objects."""
        return [ComplianceRequirement(**req) for req in self.requirements]

    def add_requirement(self, requirement: ComplianceRequirement) -> None:
        """Add a new requirement to the matrix."""
        self.requirements.append(requirement.model_dump())
        self.total_requirements = len(self.requirements)
        if requirement.importance == ImportanceLevel.MANDATORY:
            self.mandatory_count += 1
