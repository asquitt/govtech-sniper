"""
Compliance dashboard and trust-center schemas.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DataPrivacyInfo(BaseModel):
    data_handling: list[str]
    encryption: list[str]
    access_controls: list[str]
    data_retention: list[str]
    certifications: list[str]


class ComplianceReadinessProgram(BaseModel):
    id: str
    name: str
    status: str
    percent_complete: int = Field(ge=0, le=100)
    next_milestone: str


class ComplianceReadinessResponse(BaseModel):
    programs: list[ComplianceReadinessProgram]
    last_updated: str


class ComplianceReadinessCheckpoint(BaseModel):
    checkpoint_id: str
    program_id: str
    title: str
    status: str
    target_date: datetime
    owner: str
    third_party_required: bool
    evidence_items_ready: int = Field(ge=0)
    evidence_items_total: int = Field(ge=0)
    evidence_source: Literal["static", "registry"] | None = None
    evidence_last_updated_at: datetime | None = None
    assessor_signoff_status: Literal["pending", "approved", "rejected"] | None = None
    assessor_signoff_by: str | None = None
    assessor_signed_at: datetime | None = None


class ComplianceReadinessCheckpointResponse(BaseModel):
    checkpoints: list[ComplianceReadinessCheckpoint]
    generated_at: datetime


class ComplianceCheckpointEvidenceCreate(BaseModel):
    evidence_id: int
    status: Literal["submitted", "accepted", "rejected"] | None = None
    notes: str | None = None


class ComplianceCheckpointEvidenceUpdate(BaseModel):
    status: Literal["submitted", "accepted", "rejected"] | None = None
    reviewer_notes: str | None = None


class ComplianceCheckpointEvidenceRead(BaseModel):
    link_id: int
    checkpoint_id: str
    evidence_id: int
    title: str
    evidence_type: str
    description: str | None = None
    file_path: str | None = None
    url: str | None = None
    collected_at: datetime
    expires_at: datetime | None = None
    status: Literal["submitted", "accepted", "rejected"]
    notes: str | None = None
    reviewer_user_id: int | None = None
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    linked_at: datetime


class ComplianceCheckpointSignoffWrite(BaseModel):
    status: Literal["pending", "approved", "rejected"]
    assessor_name: str
    assessor_org: str | None = None
    notes: str | None = None


class ComplianceCheckpointSignoffRead(BaseModel):
    checkpoint_id: str
    status: Literal["pending", "approved", "rejected"]
    assessor_name: str
    assessor_org: str | None = None
    notes: str | None = None
    signed_by_user_id: int | None = None
    signed_at: datetime | None = None
    updated_at: datetime


class GovCloudMigrationPhase(BaseModel):
    phase_id: str
    title: str
    status: str
    target_date: datetime
    owner: str
    exit_criteria: list[str]


class GovCloudDeploymentProfile(BaseModel):
    program_id: str
    provider: str
    status: str
    target_regions: list[str]
    boundary_services: list[str]
    identity_federation_status: str
    network_isolation_status: str
    data_residency_status: str
    migration_phases: list[GovCloudMigrationPhase]
    updated_at: datetime


class SOC2ControlDomainStatus(BaseModel):
    domain_id: str
    domain_name: str
    controls_total: int = Field(ge=0)
    controls_ready: int = Field(ge=0)
    percent_complete: int = Field(ge=0, le=100)
    owner: str


class SOC2Milestone(BaseModel):
    milestone_id: str
    title: str
    status: str
    due_date: datetime
    owner: str
    evidence_ready: bool
    notes: str


class SOC2ReadinessResponse(BaseModel):
    program_id: str
    name: str
    status: str
    audit_firm_status: str
    observation_window_start: datetime
    observation_window_end: datetime
    overall_percent_complete: int = Field(ge=0, le=100)
    domains: list[SOC2ControlDomainStatus]
    milestones: list[SOC2Milestone]
    updated_at: datetime


class TrustCenterPolicy(BaseModel):
    allow_ai_requirement_analysis: bool
    allow_ai_draft_generation: bool
    require_human_review_for_submission: bool
    share_anonymized_product_telemetry: bool
    retain_prompt_logs_days: int = Field(ge=0, le=30)
    retain_output_logs_days: int = Field(ge=0, le=365)


class TrustCenterPolicyUpdate(BaseModel):
    allow_ai_requirement_analysis: bool | None = None
    allow_ai_draft_generation: bool | None = None
    require_human_review_for_submission: bool | None = None
    share_anonymized_product_telemetry: bool | None = None
    retain_prompt_logs_days: int | None = Field(default=None, ge=0, le=30)
    retain_output_logs_days: int | None = Field(default=None, ge=0, le=365)

    @field_validator("retain_prompt_logs_days", "retain_output_logs_days")
    @classmethod
    def _ensure_non_negative(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("Retention days must be >= 0")
        return value


class TrustCenterRuntimeGuarantees(BaseModel):
    model_provider: str
    processing_mode: str
    provider_training_allowed: bool
    provider_retention_hours: int
    no_training_enforced: bool


class TrustCenterEvidenceItem(BaseModel):
    control: str
    status: Literal["enforced", "warning", "configured"]
    detail: str


class TrustCenterProfile(BaseModel):
    organization_id: int | None = None
    organization_name: str | None = None
    can_manage_policy: bool
    policy: TrustCenterPolicy
    runtime_guarantees: TrustCenterRuntimeGuarantees
    evidence: list[TrustCenterEvidenceItem]
    updated_at: datetime
