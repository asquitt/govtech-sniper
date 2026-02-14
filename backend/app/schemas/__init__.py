"""
RFP Sniper - Pydantic Schemas
=============================
Request/Response validation models.
"""

from app.schemas.compliance import (
    ComplianceReadinessProgram,
    ComplianceReadinessResponse,
    DataPrivacyInfo,
    TrustCenterEvidenceItem,
    TrustCenterPolicy,
    TrustCenterPolicyUpdate,
    TrustCenterProfile,
    TrustCenterRuntimeGuarantees,
)
from app.schemas.knowledge_base import (
    DocumentCreate,
    DocumentRead,
    DocumentUploadResponse,
)
from app.schemas.proposal import (
    DraftRequest,
    DraftResponse,
    ProposalCreate,
    ProposalRead,
    ProposalSectionCreate,
    ProposalSectionRead,
    ProposalSectionUpdate,
    SectionEvidenceCreate,
    SectionEvidenceRead,
    SubmissionPackageCreate,
    SubmissionPackageRead,
    SubmissionPackageUpdate,
)
from app.schemas.rfp import (
    AmendmentImpactSignal,
    AmendmentSectionRemediation,
    AnalyzeResponse,
    ComplianceMatrixRead,
    ComplianceRequirementCreate,
    ComplianceRequirementUpdate,
    RFPCreate,
    RFPListItem,
    RFPRead,
    RFPUpdate,
    SAMIngestResponse,
    SAMOpportunityAmendmentImpact,
    SAMOpportunitySnapshotDiff,
    SAMOpportunitySnapshotRead,
    SAMSearchParams,
)
from app.schemas.user import (
    Token,
    TokenPayload,
    UserCreate,
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
    UserRead,
    UserUpdate,
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
    "ComplianceRequirementCreate",
    "ComplianceRequirementUpdate",
    "AmendmentImpactSignal",
    "AmendmentSectionRemediation",
    "SAMSearchParams",
    "SAMIngestResponse",
    "AnalyzeResponse",
    "SAMOpportunityAmendmentImpact",
    "SAMOpportunitySnapshotRead",
    "SAMOpportunitySnapshotDiff",
    # Proposal
    "ProposalCreate",
    "ProposalRead",
    "ProposalSectionCreate",
    "ProposalSectionRead",
    "ProposalSectionUpdate",
    "SubmissionPackageCreate",
    "SubmissionPackageRead",
    "SubmissionPackageUpdate",
    "SectionEvidenceCreate",
    "SectionEvidenceRead",
    "DraftRequest",
    "DraftResponse",
    # Knowledge Base
    "DocumentCreate",
    "DocumentRead",
    "DocumentUploadResponse",
    # Compliance
    "DataPrivacyInfo",
    "ComplianceReadinessProgram",
    "ComplianceReadinessResponse",
    "TrustCenterPolicy",
    "TrustCenterPolicyUpdate",
    "TrustCenterRuntimeGuarantees",
    "TrustCenterEvidenceItem",
    "TrustCenterProfile",
]
