"""
RFP Sniper - Collaboration Schemas
====================================
Request/response models for workspaces, invitations, and data sharing.
"""

from datetime import datetime

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    rfp_id: int | None = None
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class WorkspaceRead(BaseModel):
    id: int
    owner_id: int
    rfp_id: int | None = None
    name: str
    description: str | None = None
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvitationCreate(BaseModel):
    email: str
    role: str = "viewer"


class InvitationRead(BaseModel):
    id: int
    workspace_id: int
    email: str
    role: str
    accept_token: str | None = None
    is_accepted: bool
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberRead(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    user_email: str | None = None
    user_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberRoleUpdate(BaseModel):
    role: str


class ShareDataCreate(BaseModel):
    data_type: str  # rfp_summary, compliance_matrix, proposal_section, forecast, contract_feed
    entity_id: int
    requires_approval: bool = False
    expires_at: datetime | None = None
    partner_user_id: int | None = None
    step_up_code: str | None = None


class SharedDataRead(BaseModel):
    id: int
    workspace_id: int
    data_type: str
    entity_id: int
    label: str | None = None
    requires_approval: bool
    approval_status: str
    approved_by_user_id: int | None = None
    approved_at: datetime | None = None
    expires_at: datetime | None = None
    partner_user_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractFeedCatalogItem(BaseModel):
    id: int
    name: str
    source: str
    description: str


class ContractFeedPresetItem(BaseModel):
    key: str
    name: str
    description: str
    feed_ids: list[int]


class SharePresetCreate(BaseModel):
    preset_key: str
    step_up_code: str | None = None


class SharePresetApplyResponse(BaseModel):
    preset_key: str
    applied_count: int
    shared_items: list[SharedDataRead]


class ShareGovernanceSummaryRead(BaseModel):
    workspace_id: int
    total_shared_items: int
    pending_approval_count: int
    approved_count: int
    revoked_count: int
    expired_count: int
    expiring_7d_count: int
    scoped_share_count: int
    global_share_count: int


class ShareGovernanceTrendPointRead(BaseModel):
    date: str
    shared_count: int
    approvals_completed_count: int
    approved_within_sla_count: int
    approved_after_sla_count: int
    average_approval_hours: float | None = None


class ShareGovernanceTrendRead(BaseModel):
    workspace_id: int
    days: int
    sla_hours: int
    overdue_pending_count: int
    sla_approval_rate: float
    points: list[ShareGovernanceTrendPointRead]


class GovernanceAnomalyRead(BaseModel):
    code: str
    severity: str
    title: str
    description: str
    metric_value: float
    threshold: float
    recommendation: str


class ComplianceDigestScheduleRead(BaseModel):
    workspace_id: int
    user_id: int
    frequency: str
    day_of_week: int | None = None
    hour_utc: int
    minute_utc: int
    channel: str
    recipient_role: str
    anomalies_only: bool
    is_enabled: bool
    last_sent_at: datetime | None = None


class ComplianceDigestScheduleUpdate(BaseModel):
    frequency: str = "weekly"
    day_of_week: int | None = 1
    hour_utc: int = 13
    minute_utc: int = 0
    channel: str = "in_app"
    recipient_role: str = "all"
    anomalies_only: bool = False
    is_enabled: bool = True


class ComplianceDigestDeliveryRead(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    schedule_id: int | None = None
    status: str
    attempt_number: int
    retry_of_delivery_id: int | None = None
    channel: str
    recipient_role: str
    recipient_count: int
    anomalies_count: int
    failure_reason: str | None = None
    generated_at: datetime
    created_at: datetime


class ComplianceDigestDeliverySummaryRead(BaseModel):
    total_attempts: int
    success_count: int
    failed_count: int
    retry_attempt_count: int
    last_status: str | None = None
    last_failure_reason: str | None = None
    last_sent_at: datetime | None = None


class ComplianceDigestDeliveryListRead(BaseModel):
    workspace_id: int
    user_id: int
    summary: ComplianceDigestDeliverySummaryRead
    items: list[ComplianceDigestDeliveryRead]


class ComplianceDigestPreviewRead(BaseModel):
    workspace_id: int
    generated_at: datetime
    recipient_role: str
    recipient_count: int
    summary: ShareGovernanceSummaryRead
    trends: ShareGovernanceTrendRead
    anomalies: list[GovernanceAnomalyRead]
    schedule: ComplianceDigestScheduleRead
    delivery_summary: ComplianceDigestDeliverySummaryRead | None = None


class PortalView(BaseModel):
    """Read-only partner portal view of a workspace."""

    workspace_name: str
    workspace_description: str | None = None
    rfp_title: str | None = None
    shared_items: list[SharedDataRead] = []
    members: list[MemberRead] = []
