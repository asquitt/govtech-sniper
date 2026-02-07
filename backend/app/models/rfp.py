"""
RFP Sniper - RFP Models
=======================
Solicitation data and compliance matrix.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel, Column, JSON, Text
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.proposal import Proposal


class RFPStatus(str, Enum):
    """Status of an RFP in the pipeline."""
    NEW = "new"                      # Just ingested
    ANALYZING = "analyzing"          # Deep Read in progress
    ANALYZED = "analyzed"            # Compliance matrix extracted
    DRAFTING = "drafting"            # Proposal being written
    READY = "ready"                  # Proposal complete
    SUBMITTED = "submitted"          # User marked as submitted
    ARCHIVED = "archived"            # Past deadline or rejected


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
    MANDATORY = "mandatory"      # Must comply or disqualified
    EVALUATED = "evaluated"      # Scored in evaluation
    OPTIONAL = "optional"        # Nice to have
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
    id: str                          # Unique ID (e.g., "REQ-001")
    section: str                     # Source section (e.g., "Section L.3.2")
    source_section: Optional[str] = None  # RFP structural section (e.g., "Section C", "Section H")
    requirement_text: str            # The actual requirement
    importance: ImportanceLevel      # How critical is this?
    category: Optional[str] = None   # Grouping (e.g., "Technical", "Past Performance")
    page_reference: Optional[int] = None  # Page number in source PDF
    keywords: List[str] = []         # Key terms for matching
    is_addressed: bool = False       # Has user addressed this?
    notes: Optional[str] = None      # User annotations
    status: RequirementStatus = RequirementStatus.OPEN
    assigned_to: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# =============================================================================
# RFP Model
# =============================================================================

class RFPBase(SQLModel):
    """Base RFP fields."""
    title: str = Field(max_length=500, index=True)
    solicitation_number: str = Field(max_length=100, unique=True, index=True)
    agency: str = Field(max_length=255)
    sub_agency: Optional[str] = Field(default=None, max_length=255)
    
    # Classification
    naics_code: Optional[str] = Field(default=None, max_length=10)
    set_aside: Optional[str] = Field(default=None, max_length=100)
    rfp_type: RFPType = Field(default=RFPType.SOLICITATION)
    
    # Dates
    posted_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    
    # Links
    source_url: Optional[str] = Field(default=None, max_length=1000)
    sam_gov_link: Optional[str] = Field(default=None, max_length=1000)
    
    # Contract Details
    estimated_value: Optional[int] = None  # In dollars
    place_of_performance: Optional[str] = Field(default=None, max_length=255)

    # Market Intelligence (GovDash/Govly parity fields)
    source_type: Optional[str] = Field(default=None, max_length=50)  # federal | sled | other
    jurisdiction: Optional[str] = Field(default=None, max_length=255)
    contract_vehicle: Optional[str] = Field(default=None, max_length=255)
    incumbent_vendor: Optional[str] = Field(default=None, max_length=255)
    buyer_contact_name: Optional[str] = Field(default=None, max_length=255)
    buyer_contact_email: Optional[str] = Field(default=None, max_length=255)
    buyer_contact_phone: Optional[str] = Field(default=None, max_length=50)
    budget_estimate: Optional[int] = None
    competitive_landscape: Optional[str] = Field(default=None, sa_column=Column(Text))
    intel_notes: Optional[str] = Field(default=None, sa_column=Column(Text))


class RFP(RFPBase, table=True):
    """
    Request for Proposal / Solicitation from SAM.gov.
    
    Contains the raw solicitation data plus extracted analysis.
    """
    __tablename__ = "rfps"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Status tracking
    status: RFPStatus = Field(default=RFPStatus.NEW)
    
    # Full text content (extracted from PDF)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    full_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # AI Analysis Results
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Killer Filter results
    is_qualified: Optional[bool] = None
    qualification_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    qualification_score: Optional[float] = None  # 0-100
    
    # File references
    pdf_file_path: Optional[str] = Field(default=None, max_length=500)
    attachment_paths: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    analyzed_at: Optional[datetime] = None
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="rfps")
    compliance_matrix: Optional["ComplianceMatrix"] = Relationship(back_populates="rfp")
    proposals: List["Proposal"] = Relationship(back_populates="rfp")


# =============================================================================
# Compliance Matrix Model
# =============================================================================

class ComplianceMatrix(SQLModel, table=True):
    """
    Extracted requirements from RFP.
    The "Deep Read" agent populates this via Gemini 1.5 Pro analysis.
    """
    __tablename__ = "compliance_matrices"

    id: Optional[int] = Field(default=None, primary_key=True)
    rfp_id: int = Field(foreign_key="rfps.id", unique=True)
    
    # The extracted requirements (JSON array of ComplianceRequirement)
    requirements: List[dict] = Field(default=[], sa_column=Column(JSON))
    
    # Summary statistics
    total_requirements: int = Field(default=0)
    mandatory_count: int = Field(default=0)
    addressed_count: int = Field(default=0)
    
    # AI confidence in extraction
    extraction_confidence: Optional[float] = None  # 0-1
    
    # Raw AI response for debugging
    raw_ai_response: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    rfp: Optional[RFP] = Relationship(back_populates="compliance_matrix")

    def get_requirements(self) -> List[ComplianceRequirement]:
        """Parse stored JSON into ComplianceRequirement objects."""
        return [ComplianceRequirement(**req) for req in self.requirements]
    
    def add_requirement(self, requirement: ComplianceRequirement) -> None:
        """Add a new requirement to the matrix."""
        self.requirements.append(requirement.model_dump())
        self.total_requirements = len(self.requirements)
        if requirement.importance == ImportanceLevel.MANDATORY:
            self.mandatory_count += 1
