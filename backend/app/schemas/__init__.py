"""
RFP Sniper - Pydantic Schemas
=============================
Request/Response validation models.
"""

from app.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
    Token,
    TokenPayload,
)
from app.schemas.rfp import (
    RFPCreate,
    RFPRead,
    RFPUpdate,
    RFPListItem,
    ComplianceMatrixRead,
    SAMSearchParams,
    SAMIngestResponse,
    AnalyzeResponse,
    SAMOpportunitySnapshotRead,
    SAMOpportunitySnapshotDiff,
)
from app.schemas.proposal import (
    ProposalCreate,
    ProposalRead,
    ProposalSectionCreate,
    ProposalSectionRead,
    DraftRequest,
    DraftResponse,
)
from app.schemas.knowledge_base import (
    DocumentCreate,
    DocumentRead,
    DocumentUploadResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "UserProfileCreate",
    "UserProfileRead",
    "UserProfileUpdate",
    "Token",
    "TokenPayload",
    # RFP
    "RFPCreate",
    "RFPRead",
    "RFPUpdate",
    "RFPListItem",
    "ComplianceMatrixRead",
    "SAMSearchParams",
    "SAMIngestResponse",
    "AnalyzeResponse",
    "SAMOpportunitySnapshotRead",
    "SAMOpportunitySnapshotDiff",
    # Proposal
    "ProposalCreate",
    "ProposalRead",
    "ProposalSectionCreate",
    "ProposalSectionRead",
    "DraftRequest",
    "DraftResponse",
    # Knowledge Base
    "DocumentCreate",
    "DocumentRead",
    "DocumentUploadResponse",
]
