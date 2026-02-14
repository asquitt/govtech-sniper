"""
RFP Sniper - Collaboration Models
===================================
Cross-organization collaboration: shared workspaces, invitations, and data permissions.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel


class WorkspaceRole(str, Enum):
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"


class SharedDataType(str, Enum):
    RFP_SUMMARY = "rfp_summary"
    COMPLIANCE_MATRIX = "compliance_matrix"
    PROPOSAL_SECTION = "proposal_section"
    FORECAST = "forecast"
    CONTRACT_FEED = "contract_feed"


class ShareApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"


class GovernanceAnomalySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ComplianceDigestFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


class ComplianceDigestChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"


class ComplianceDigestRecipientRole(str, Enum):
    ALL = "all"
    OWNER = "owner"
    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class ComplianceDigestDeliveryStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class SharedWorkspace(SQLModel, table=True):
    """A collaboration workspace owned by a user, optionally tied to an RFP."""

    __tablename__ = "shared_workspaces"

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)
    name: str = Field(max_length=255)
    description: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceInvitation(SQLModel, table=True):
    """Email-based invitation to join a workspace."""

    __tablename__ = "workspace_invitations"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    email: str = Field(max_length=255, index=True)
    role: WorkspaceRole = Field(default=WorkspaceRole.VIEWER)
    token: str = Field(max_length=255, sa_column=Column(String(255), unique=True))
    expires_at: datetime
    is_accepted: bool = Field(default=False)
    accepted_user_id: int | None = Field(default=None, foreign_key="users.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceMember(SQLModel, table=True):
    """Active member of a workspace (created after invitation acceptance)."""

    __tablename__ = "workspace_members"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role: WorkspaceRole = Field(default=WorkspaceRole.VIEWER)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharedDataPermission(SQLModel, table=True):
    """Controls which data items are visible inside a workspace."""

    __tablename__ = "shared_data_permissions"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    data_type: SharedDataType
    entity_id: int  # ID of the shared entity (rfp_id, proposal_id, etc.)
    requires_approval: bool = Field(default=False)
    approval_status: ShareApprovalStatus = Field(default=ShareApprovalStatus.APPROVED)
    approved_by_user_id: int | None = Field(default=None, foreign_key="users.id")
    approved_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None, index=True)
    partner_user_id: int | None = Field(default=None, foreign_key="users.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceComplianceDigestSchedule(SQLModel, table=True):
    """Delivery preferences for workspace governance compliance digests."""

    __tablename__ = "workspace_compliance_digest_schedules"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    frequency: ComplianceDigestFrequency = Field(default=ComplianceDigestFrequency.WEEKLY)
    day_of_week: int | None = Field(default=1, ge=0, le=6)
    hour_utc: int = Field(default=13, ge=0, le=23)
    minute_utc: int = Field(default=0, ge=0, le=59)
    channel: ComplianceDigestChannel = Field(default=ComplianceDigestChannel.IN_APP)
    recipient_role: ComplianceDigestRecipientRole = Field(default=ComplianceDigestRecipientRole.ALL)
    anomalies_only: bool = Field(default=False)
    is_enabled: bool = Field(default=True)
    last_sent_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceComplianceDigestDelivery(SQLModel, table=True):
    """Delivery attempts for workspace compliance digests (success/failure + retries)."""

    __tablename__ = "workspace_compliance_digest_deliveries"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="shared_workspaces.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    schedule_id: int | None = Field(
        default=None, foreign_key="workspace_compliance_digest_schedules.id", index=True
    )
    status: ComplianceDigestDeliveryStatus = Field(default=ComplianceDigestDeliveryStatus.SUCCESS)
    attempt_number: int = Field(default=1, ge=1)
    retry_of_delivery_id: int | None = Field(
        default=None, foreign_key="workspace_compliance_digest_deliveries.id"
    )
    channel: ComplianceDigestChannel = Field(default=ComplianceDigestChannel.IN_APP)
    recipient_role: ComplianceDigestRecipientRole = Field(default=ComplianceDigestRecipientRole.ALL)
    recipient_count: int = Field(default=0, ge=0)
    anomalies_count: int = Field(default=0, ge=0)
    failure_reason: str | None = Field(default=None, max_length=255)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
