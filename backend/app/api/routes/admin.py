"""
RFP Sniper - Admin Routes
==========================
Organization admin dashboard: user management, org settings, usage analytics.
"""

import secrets
import socket
from datetime import datetime, timedelta
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.config import settings
from app.database import get_session
from app.models.audit import AuditEvent
from app.models.integration import IntegrationConfig
from app.models.organization import (
    InvitationStatus,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrgRole,
    SSOIdentity,
    SSOProvider,
)
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.secret import SecretRecord
from app.models.user import User
from app.models.webhook import WebhookSubscription

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# Helpers
# =============================================================================


async def _require_org_admin(
    user: UserAuth,
    session: AsyncSession,
) -> tuple[Organization, OrganizationMember]:
    """Verify user is an admin or owner of their organization."""
    db_user = (await session.execute(select(User).where(User.id == user.id))).scalar_one_or_none()
    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=403, detail="No organization membership")

    org = (
        await session.execute(
            select(Organization).where(Organization.id == db_user.organization_id)
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    member = (
        await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not member or member.role not in (OrgRole.OWNER, OrgRole.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    return org, member


def _celery_broker_available() -> bool:
    """
    Best-effort broker probe for capability diagnostics.
    """
    broker_url = settings.celery_broker_url
    parsed = urlparse(broker_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return True

    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def _celery_worker_available() -> bool:
    """
    Best-effort worker availability probe for local/dev diagnostics.
    """
    try:
        from app.tasks.celery_app import celery_app

        replies = celery_app.control.inspect(timeout=0.5).ping() or {}
        return len(replies) > 0
    except Exception:
        return False


def _database_engine_name(database_url: str) -> str:
    normalized = database_url.lower()
    if "sqlite" in normalized:
        return "sqlite"
    if "postgres" in normalized:
        return "postgresql"
    if "mysql" in normalized:
        return "mysql"
    return "unknown"


def _websocket_runtime_snapshot() -> dict[str, int]:
    """
    Best-effort snapshot of websocket runtime state for diagnostics.
    """
    try:
        from app.api.routes.websocket import manager

        active_connections = sum(
            len(connections) for connections in manager.active_connections.values()
        )
        watched_tasks = len(manager.task_watchers)
        active_documents = len(manager.document_presence)
        presence_users = sum(len(users) for users in manager.document_presence.values())
        active_section_locks = len(manager.section_locks)
        active_cursors = sum(len(cursors) for cursors in manager.document_cursors.values())
        return {
            "active_connections": active_connections,
            "watched_tasks": watched_tasks,
            "active_documents": active_documents,
            "presence_users": presence_users,
            "active_section_locks": active_section_locks,
            "active_cursors": active_cursors,
        }
    except Exception:
        return {
            "active_connections": 0,
            "watched_tasks": 0,
            "active_documents": 0,
            "presence_users": 0,
            "active_section_locks": 0,
            "active_cursors": 0,
        }


# =============================================================================
# Schemas
# =============================================================================


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


class MemberRoleUpdate(BaseModel):
    role: OrgRole


class InviteMember(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER
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


def _serialize_org_invitation(
    invitation: OrganizationInvitation,
    *,
    activation_ready: bool,
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
    )


# =============================================================================
# Organization CRUD
# =============================================================================


@router.post("/organizations")
async def create_organization(
    body: OrgCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new organization. The creator becomes the owner."""
    # Check slug uniqueness
    existing = (
        await session.execute(select(Organization).where(Organization.slug == body.slug))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    org = Organization(
        name=body.name,
        slug=body.slug,
        domain=body.domain,
        billing_email=body.billing_email,
    )
    session.add(org)
    await session.flush()

    # Add creator as owner
    member = OrganizationMember(
        organization_id=org.id,  # type: ignore[arg-type]
        user_id=current_user.id,
        role=OrgRole.OWNER,
    )
    session.add(member)

    # Link user to org
    user = (
        await session.execute(select(User).where(User.id == current_user.id))
    ).scalar_one_or_none()
    if user:
        user.organization_id = org.id
        session.add(user)

    await session.commit()
    await session.refresh(org)

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "domain": org.domain,
        "created_at": org.created_at.isoformat(),
    }


@router.get("/organization")
async def get_organization(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current user's organization details."""
    org, _member = await _require_org_admin(current_user, session)
    member_count = (
        await session.execute(
            select(func.count()).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one() or 0

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "domain": org.domain,
        "billing_email": org.billing_email,
        "sso_enabled": org.sso_enabled,
        "sso_provider": org.sso_provider,
        "sso_enforce": org.sso_enforce,
        "sso_auto_provision": org.sso_auto_provision,
        "logo_url": org.logo_url,
        "primary_color": org.primary_color,
        "ip_allowlist": org.ip_allowlist,
        "data_retention_days": org.data_retention_days,
        "member_count": member_count,
        "created_at": org.created_at.isoformat(),
    }


@router.patch("/organization")
async def update_organization(
    body: OrgUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update organization settings. Requires admin/owner."""
    org, _ = await _require_org_admin(current_user, session)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    org.updated_at = datetime.utcnow()
    session.add(org)
    await session.commit()

    return {"status": "updated"}


@router.get("/capability-health")
async def get_capability_health(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Summarized capability integration and operational health for admins."""
    org, _ = await _require_org_admin(current_user, session)

    integrations = (
        await session.execute(
            select(IntegrationConfig).where(IntegrationConfig.user_id == current_user.id)
        )
    ).scalars()
    integration_by_provider: dict[str, dict[str, int]] = {}
    for integration in integrations:
        provider = (
            integration.provider.value
            if hasattr(integration.provider, "value")
            else str(integration.provider)
        )
        bucket = integration_by_provider.setdefault(provider, {"total": 0, "enabled": 0})
        bucket["total"] += 1
        if integration.is_enabled:
            bucket["enabled"] += 1

    secret_count = (
        await session.execute(select(func.count()).where(SecretRecord.user_id == current_user.id))
    ).scalar_one() or 0
    webhook_count = (
        await session.execute(
            select(func.count()).where(WebhookSubscription.user_id == current_user.id)
        )
    ).scalar_one() or 0

    broker_reachable = _celery_broker_available()
    worker_online = _celery_worker_available()
    task_mode = "queued" if broker_reachable and worker_online else "sync_fallback"
    scim_configured = bool(settings.scim_bearer_token)
    websocket_runtime = _websocket_runtime_snapshot()

    discoverability = [
        {
            "capability": "Template Marketplace",
            "frontend_path": "/templates",
            "backend_prefix": "/api/v1/templates",
            "status": "integrated",
            "note": "Primary dashboard navigation route enabled.",
        },
        {
            "capability": "Word Add-in",
            "frontend_path": "/word-addin",
            "backend_prefix": "/api/v1/word-addin",
            "status": "integrated",
            "note": "Primary dashboard navigation route enabled with taskpane redirect.",
        },
        {
            "capability": "SCIM Provisioning",
            "frontend_path": None,
            "backend_prefix": "/api/v1/scim/v2",
            "status": "configured" if scim_configured else "needs_configuration",
            "note": (
                "SCIM bearer token configured."
                if scim_configured
                else "Set SCIM_BEARER_TOKEN to enable SCIM provisioning."
            ),
        },
        {
            "capability": "Webhook Subscriptions",
            "frontend_path": "/settings",
            "backend_prefix": "/api/v1/webhooks",
            "status": "configured" if webhook_count > 0 else "ready",
            "note": (
                f"{webhook_count} webhook subscriptions configured for current user."
                if webhook_count > 0
                else "No webhook subscriptions configured yet."
            ),
        },
        {
            "capability": "Secrets Vault",
            "frontend_path": "/settings",
            "backend_prefix": "/api/v1/secrets",
            "status": "configured" if secret_count > 0 else "ready",
            "note": (
                f"{secret_count} secrets stored for current user."
                if secret_count > 0
                else "No secrets stored yet."
            ),
        },
        {
            "capability": "WebSocket Task Feed",
            "frontend_path": "/diagnostics",
            "backend_prefix": "/api/v1/ws",
            "status": "integrated",
            "note": (
                f"{websocket_runtime['active_connections']} active socket connections, "
                f"{websocket_runtime['watched_tasks']} watched tasks, "
                f"{websocket_runtime['active_section_locks']} section locks."
            ),
        },
    ]

    return {
        "organization_id": org.id,
        "timestamp": datetime.utcnow().isoformat(),
        "runtime": {
            "debug": settings.debug,
            "mock_ai": settings.mock_ai,
            "mock_sam_gov": settings.mock_sam_gov,
            "database_engine": _database_engine_name(settings.database_url),
            "websocket": {
                "endpoint": "/api/v1/ws?token=<jwt>",
                "active_connections": websocket_runtime["active_connections"],
                "watched_tasks": websocket_runtime["watched_tasks"],
                "active_documents": websocket_runtime["active_documents"],
                "presence_users": websocket_runtime["presence_users"],
                "active_section_locks": websocket_runtime["active_section_locks"],
                "active_cursors": websocket_runtime["active_cursors"],
            },
        },
        "workers": {
            "broker_reachable": broker_reachable,
            "worker_online": worker_online,
            "task_mode": task_mode,
        },
        "enterprise": {
            "scim_configured": scim_configured,
            "scim_default_team_name": settings.scim_default_team_name,
            "webhook_subscriptions": webhook_count,
            "stored_secrets": secret_count,
        },
        "integrations_by_provider": [
            {"provider": provider, **counts}
            for provider, counts in sorted(integration_by_provider.items(), key=lambda p: p[0])
        ],
        "discoverability": discoverability,
    }


# =============================================================================
# Member Management
# =============================================================================


@router.post("/members/invite", response_model=OrganizationInvitationRead, status_code=201)
async def invite_member(
    body: InviteMember,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create an organization invitation for a user email."""
    org, caller_member = await _require_org_admin(current_user, session)

    normalized_email = body.email.lower().strip()
    if body.expires_in_days < 1 or body.expires_in_days > 30:
        raise HTTPException(status_code=400, detail="expires_in_days must be between 1 and 30")

    if body.role in (OrgRole.OWNER, OrgRole.ADMIN) and caller_member.role != OrgRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can invite admins/owners")

    existing_user = (
        await session.execute(select(User).where(User.email == normalized_email))
    ).scalar_one_or_none()
    if existing_user:
        existing_member = (
            await session.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == org.id,
                    OrganizationMember.user_id == existing_user.id,
                )
            )
        ).scalar_one_or_none()
        if existing_member and existing_member.is_active:
            raise HTTPException(
                status_code=409, detail="User is already an active organization member"
            )

    now = datetime.utcnow()
    existing_invite = (
        await session.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.organization_id == org.id,
                OrganizationInvitation.email == normalized_email,
                OrganizationInvitation.status == InvitationStatus.PENDING,
                OrganizationInvitation.expires_at > now,
            )
        )
    ).scalar_one_or_none()
    if existing_invite:
        raise HTTPException(
            status_code=409, detail="An active invitation already exists for this email"
        )

    invitation = OrganizationInvitation(
        organization_id=org.id,  # type: ignore[arg-type]
        invited_by_user_id=current_user.id,
        email=normalized_email,
        role=body.role,
        token=secrets.token_urlsafe(32),
        status=InvitationStatus.PENDING,
        expires_at=now + timedelta(days=body.expires_in_days),
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)

    return _serialize_org_invitation(invitation, activation_ready=existing_user is not None)


@router.get("/member-invitations", response_model=list[OrganizationInvitationRead])
async def list_member_invitations(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List organization invitations and activation readiness."""
    org, _ = await _require_org_admin(current_user, session)

    invitations = (
        (
            await session.execute(
                select(OrganizationInvitation)
                .where(OrganizationInvitation.organization_id == org.id)
                .order_by(OrganizationInvitation.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    emails = {invite.email for invite in invitations}
    users = (
        (await session.execute(select(User).where(User.email.in_(emails)))).scalars().all()
        if emails
        else []
    )
    user_by_email = {user.email.lower(): user for user in users}

    now = datetime.utcnow()
    response: list[OrganizationInvitationRead] = []
    for invite in invitations:
        if invite.status == InvitationStatus.PENDING and invite.expires_at <= now:
            invite.status = InvitationStatus.EXPIRED
            session.add(invite)
        response.append(
            _serialize_org_invitation(
                invite,
                activation_ready=invite.email.lower() in user_by_email,
            )
        )

    await session.commit()
    return response


@router.post(
    "/member-invitations/{invitation_id}/activate",
    response_model=OrganizationInvitationRead,
)
async def activate_member_invitation(
    invitation_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Activate invitation by linking a registered user into organization membership."""
    org, caller_member = await _require_org_admin(current_user, session)

    invitation = (
        await session.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.id == invitation_id,
                OrganizationInvitation.organization_id == org.id,
            )
        )
    ).scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status == InvitationStatus.ACTIVATED:
        return _serialize_org_invitation(invitation, activation_ready=True)

    if invitation.expires_at <= datetime.utcnow():
        invitation.status = InvitationStatus.EXPIRED
        session.add(invitation)
        await session.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    if invitation.role in (OrgRole.OWNER, OrgRole.ADMIN) and caller_member.role != OrgRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only owners can activate admin/owner invitations",
        )

    user = (
        await session.execute(select(User).where(User.email == invitation.email.lower()))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=409,
            detail="Invited user must register before activation",
        )

    membership = (
        await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if membership:
        membership.role = invitation.role
        membership.is_active = True
        session.add(membership)
    else:
        session.add(
            OrganizationMember(
                organization_id=org.id,  # type: ignore[arg-type]
                user_id=user.id,  # type: ignore[arg-type]
                role=invitation.role,
                is_active=True,
            )
        )

    user.organization_id = org.id
    user.is_active = True
    session.add(user)

    invitation.status = InvitationStatus.ACTIVATED
    invitation.accepted_user_id = user.id
    invitation.activated_at = datetime.utcnow()
    session.add(invitation)

    await session.commit()
    await session.refresh(invitation)
    return _serialize_org_invitation(invitation, activation_ready=True)


@router.get("/members")
async def list_members(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all organization members."""
    org, _ = await _require_org_admin(current_user, session)

    members = (
        await session.execute(
            select(OrganizationMember, User)
            .join(User, OrganizationMember.user_id == User.id)
            .where(OrganizationMember.organization_id == org.id)
            .order_by(OrganizationMember.joined_at)
        )
    ).all()

    result = []
    for om, user in members:
        # Check if user has SSO identity
        sso = (
            await session.execute(select(SSOIdentity).where(SSOIdentity.user_id == user.id))
        ).scalar_one_or_none()
        result.append(
            {
                "id": om.id,
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": om.role.value,
                "is_active": om.is_active,
                "tier": user.tier.value,
                "joined_at": om.joined_at.isoformat(),
                "last_login": sso.last_login_at.isoformat() if sso and sso.last_login_at else None,
                "sso_provider": sso.provider.value if sso else None,
            }
        )

    return {"members": result, "total": len(result)}


@router.patch("/members/{user_id}/role")
async def update_member_role(
    user_id: int,
    body: MemberRoleUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Change a member's role. Requires owner (for admin changes) or admin."""
    org, caller_member = await _require_org_admin(current_user, session)

    # Can't change your own role
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    target_member = (
        await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Only owners can promote/demote admins
    if body.role in (OrgRole.OWNER, OrgRole.ADMIN) or target_member.role in (
        OrgRole.OWNER,
        OrgRole.ADMIN,
    ):
        if caller_member.role != OrgRole.OWNER:
            raise HTTPException(status_code=403, detail="Only owners can manage admin roles")

    target_member.role = body.role
    session.add(target_member)
    await session.commit()

    return {"status": "updated", "user_id": user_id, "role": body.role.value}


@router.post("/members/{user_id}/deactivate")
async def deactivate_member(
    user_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Deactivate a member. They can no longer access the org."""
    org, caller_member = await _require_org_admin(current_user, session)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    target_member = (
        await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Only owners can deactivate admins
    if target_member.role in (OrgRole.OWNER, OrgRole.ADMIN) and caller_member.role != OrgRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can deactivate admins")

    target_member.is_active = False
    session.add(target_member)

    # Also deactivate the user account
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user:
        user.is_active = False
        session.add(user)

    await session.commit()
    return {"status": "deactivated", "user_id": user_id}


@router.post("/members/{user_id}/reactivate")
async def reactivate_member(
    user_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Reactivate a previously deactivated member."""
    org, _ = await _require_org_admin(current_user, session)

    target_member = (
        await session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    target_member.is_active = True
    session.add(target_member)

    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user:
        user.is_active = True
        session.add(user)

    await session.commit()
    return {"status": "reactivated", "user_id": user_id}


# =============================================================================
# Usage Analytics
# =============================================================================


@router.get("/usage")
async def get_usage_analytics(
    days: int = Query(default=30, ge=7, le=90),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Organization usage analytics for the admin dashboard."""
    org, _ = await _require_org_admin(current_user, session)
    since = datetime.utcnow() - timedelta(days=days)

    # Get all org user IDs
    org_user_ids_result = await session.execute(
        select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
    )
    org_user_ids = list(org_user_ids_result.scalars().all())

    if not org_user_ids:
        return {
            "members": 0,
            "proposals": 0,
            "rfps": 0,
            "audit_events": 0,
            "active_users": 0,
            "by_action": [],
        }

    # Count proposals created in period
    proposals_count = (
        await session.execute(
            select(func.count()).where(
                Proposal.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                Proposal.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Count RFPs uploaded in period
    rfps_count = (
        await session.execute(
            select(func.count()).where(
                RFP.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                RFP.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Audit events count in period
    audit_count = (
        await session.execute(
            select(func.count()).where(
                AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                AuditEvent.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Active users (users with at least 1 audit event in period)
    active_users = (
        await session.execute(
            select(func.count(func.distinct(AuditEvent.user_id))).where(
                AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
                AuditEvent.created_at >= since,
            )
        )
    ).scalar_one() or 0

    # Audit events by action type
    by_action_result = await session.execute(
        select(AuditEvent.action, func.count())
        .where(
            AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
            AuditEvent.created_at >= since,
        )
        .group_by(AuditEvent.action)
        .order_by(func.count().desc())
        .limit(10)
    )
    by_action = [{"action": action, "count": count} for action, count in by_action_result.all()]

    return {
        "members": len(org_user_ids),
        "proposals": proposals_count,
        "rfps": rfps_count,
        "audit_events": audit_count,
        "active_users": active_users,
        "by_action": by_action,
        "period_days": days,
    }


# =============================================================================
# Org-Level Audit Log
# =============================================================================


@router.get("/audit")
async def get_org_audit_log(
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """View audit log for the entire organization."""
    org, _ = await _require_org_admin(current_user, session)

    # Get org user IDs
    org_user_ids_result = await session.execute(
        select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == org.id,
        )
    )
    org_user_ids = list(org_user_ids_result.scalars().all())

    query = select(AuditEvent).where(
        AuditEvent.user_id.in_(org_user_ids),  # type: ignore[attr-defined]
    )
    if action:
        query = query.where(AuditEvent.action == action)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)

    query = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)  # type: ignore[union-attr]
    events = (await session.execute(query)).scalars().all()

    # Resolve user emails
    user_map: dict[int, str] = {}
    if events:
        user_ids = {e.user_id for e in events if e.user_id}
        if user_ids:
            users = (
                (
                    await session.execute(select(User).where(User.id.in_(user_ids)))  # type: ignore[attr-defined]
                )
                .scalars()
                .all()
            )
            user_map = {u.id: u.email for u in users}

    return {
        "events": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "user_email": user_map.get(e.user_id, "unknown") if e.user_id else None,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "action": e.action,
                "metadata": e.event_metadata,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events),
        "offset": offset,
        "limit": limit,
    }
