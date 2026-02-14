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
