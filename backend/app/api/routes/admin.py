"""
RFP Sniper - Admin Routes
==========================
Organization admin dashboard: user management, org settings, usage analytics.
"""

from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.models.audit import AuditEvent
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrgRole,
    SSOIdentity,
    SSOProvider,
)
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User

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
    email: str
    role: OrgRole = OrgRole.MEMBER


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


# =============================================================================
# Member Management
# =============================================================================


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
