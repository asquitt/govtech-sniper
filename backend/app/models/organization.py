"""
RFP Sniper - Organization Models
=================================
Multi-tenant organization support with SSO identity linking.
"""

from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel

# =============================================================================
# Organization
# =============================================================================


class OrgRole(str, Enum):
    """Organization-level roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class SSOProvider(str, Enum):
    """Supported SSO identity providers."""

    OKTA = "okta"
    MICROSOFT = "microsoft"
    GOOGLE = "google"


class InvitationStatus(str, Enum):
    """Organization invitation lifecycle state."""

    PENDING = "pending"
    ACTIVATED = "activated"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Organization(SQLModel, table=True):
    """
    Top-level organization entity for multi-tenant enterprise support.
    Teams belong to organizations. Users belong to organizations.
    """

    __tablename__ = "organizations"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100, unique=True, index=True)
    domain: str | None = Field(default=None, max_length=255, index=True)

    # Billing
    billing_email: str | None = Field(default=None, max_length=255)
    stripe_customer_id: str | None = Field(default=None, max_length=255)

    # SSO Configuration
    sso_enabled: bool = Field(default=False)
    sso_provider: SSOProvider | None = Field(default=None)
    sso_enforce: bool = Field(default=False)  # Disable password login
    sso_auto_provision: bool = Field(default=True)  # JIT provisioning

    # Branding
    logo_url: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None, max_length=20)

    # Settings
    settings: dict = Field(default={}, sa_column=Column(JSON))

    # Security
    ip_allowlist: list[str] = Field(default=[], sa_column=Column(JSON))
    data_retention_days: int = Field(default=365)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Organization Membership
# =============================================================================


class OrganizationMember(SQLModel, table=True):
    """User membership in an organization with role."""

    __tablename__ = "organization_members"

    id: int | None = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organizations.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role: OrgRole = Field(default=OrgRole.MEMBER)
    is_active: bool = Field(default=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class OrganizationInvitation(SQLModel, table=True):
    """Email invitation to join an organization."""

    __tablename__ = "organization_invitations"

    id: int | None = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organizations.id", index=True)
    invited_by_user_id: int = Field(foreign_key="users.id", index=True)
    email: str = Field(max_length=255, index=True)
    role: OrgRole = Field(default=OrgRole.MEMBER)
    token: str = Field(max_length=255, unique=True, index=True)
    status: InvitationStatus = Field(default=InvitationStatus.PENDING)
    expires_at: datetime
    accepted_user_id: int | None = Field(default=None, foreign_key="users.id")
    activated_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# SSO Identity (links SSO claims to local user)
# =============================================================================


class SSOIdentity(SQLModel, table=True):
    """
    Maps an external SSO identity to a local user account.
    Allows one user to have multiple SSO identities (e.g., Okta + Google).
    """

    __tablename__ = "sso_identities"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    provider: SSOProvider = Field(index=True)

    # Identity claims from the IdP
    subject: str = Field(max_length=500, index=True)  # sub claim
    email: str = Field(max_length=255)
    name: str | None = Field(default=None, max_length=255)
    groups: list[str] = Field(default=[], sa_column=Column(JSON))

    # Raw token data (for debugging, not auth)
    id_token_claims: dict = Field(default={}, sa_column=Column(JSON))

    # Timestamps
    last_login_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
