"""
Admin route schemas.
"""

from pydantic import BaseModel, EmailStr

from app.models.organization import (
    OrganizationInvitation,
    OrgRole,
    SSOProvider,
)


class OrgCreate(BaseModel):
    name: str
    slug: str
    domain: str | None = None
    billing_email: str | None = None


class OrgUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    billing_email: str | None = None
    sso_enabled: bool | None = None
    sso_provider: SSOProvider | None = None
    sso_enforce: bool | None = None
    sso_auto_provision: bool | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    ip_allowlist: list[str] | None = None
    data_retention_days: int | None = None
    require_step_up_for_sensitive_exports: bool | None = None
    require_step_up_for_sensitive_shares: bool | None = None
    apply_cui_watermark_to_sensitive_exports: bool | None = None
    apply_cui_redaction_to_sensitive_exports: bool | None = None


class MemberRoleUpdate(BaseModel):
    role: OrgRole


class InviteMember(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER
    expires_in_days: int = 7


class InvitationResendRequest(BaseModel):
    expires_in_days: int = 7


class OrganizationInvitationRead(BaseModel):
    id: int
    email: str
    role: str
    status: str
    expires_at: str
    activated_at: str | None = None
    accepted_user_id: int | None = None
    invited_by_user_id: int
    activation_ready: bool
    invite_age_hours: int
    invite_age_days: int
    days_until_expiry: int
    sla_state: str


def _serialize_org_invitation(
    invitation: OrganizationInvitation,
    *,
    activation_ready: bool,
    invite_age_hours: int = 0,
    invite_age_days: int = 0,
    days_until_expiry: int = 0,
    sla_state: str = "healthy",
) -> OrganizationInvitationRead:
    return OrganizationInvitationRead(
        id=invitation.id,  # type: ignore[arg-type]
        email=invitation.email,
        role=invitation.role.value if hasattr(invitation.role, "value") else str(invitation.role),
        status=invitation.status.value
        if hasattr(invitation.status, "value")
        else str(invitation.status),
        expires_at=invitation.expires_at.isoformat(),
        activated_at=invitation.activated_at.isoformat() if invitation.activated_at else None,
        accepted_user_id=invitation.accepted_user_id,
        invited_by_user_id=invitation.invited_by_user_id,
        activation_ready=activation_ready,
        invite_age_hours=invite_age_hours,
        invite_age_days=invite_age_days,
        days_until_expiry=days_until_expiry,
        sla_state=sla_state,
    )
