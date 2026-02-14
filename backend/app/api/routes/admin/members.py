"""
Admin routes - Member management.
"""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.models.organization import (
    InvitationStatus,
    OrganizationInvitation,
    OrganizationMember,
    OrgRole,
    SSOIdentity,
)
from app.models.user import User

from .helpers import _require_org_admin
from .schemas import (
    InvitationResendRequest,
    InviteMember,
    MemberRoleUpdate,
    OrganizationInvitationRead,
    _serialize_org_invitation,
)

router = APIRouter()


def _invitation_metrics(invitation: OrganizationInvitation) -> tuple[int, int, int, str]:
    """Compute invitation SLA metadata for admin operations."""
    now = datetime.utcnow()
    age_delta = now - invitation.created_at
    invite_age_hours = max(0, int(age_delta.total_seconds() // 3600))
    invite_age_days = invite_age_hours // 24
    days_until_expiry = int((invitation.expires_at - now).total_seconds() // 86400)

    status = invitation.status
    if status == InvitationStatus.ACTIVATED:
        sla_state = "completed"
    elif status == InvitationStatus.REVOKED:
        sla_state = "revoked"
    elif status == InvitationStatus.EXPIRED or days_until_expiry < 0:
        sla_state = "expired"
    elif days_until_expiry <= 1:
        sla_state = "expiring"
    elif invite_age_days >= 5:
        sla_state = "aging"
    else:
        sla_state = "healthy"

    return invite_age_hours, invite_age_days, days_until_expiry, sla_state


async def _serialize_invitation_with_metrics(
    invitation: OrganizationInvitation,
    *,
    activation_ready: bool,
) -> OrganizationInvitationRead:
    age_hours, age_days, days_until_expiry, sla_state = _invitation_metrics(invitation)
    return _serialize_org_invitation(
        invitation,
        activation_ready=activation_ready,
        invite_age_hours=age_hours,
        invite_age_days=age_days,
        days_until_expiry=days_until_expiry,
        sla_state=sla_state,
    )


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

    return await _serialize_invitation_with_metrics(
        invitation,
        activation_ready=existing_user is not None,
    )


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
            await _serialize_invitation_with_metrics(
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
        return await _serialize_invitation_with_metrics(invitation, activation_ready=True)

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
    return await _serialize_invitation_with_metrics(invitation, activation_ready=True)


@router.post(
    "/member-invitations/{invitation_id}/revoke",
    response_model=OrganizationInvitationRead,
)
async def revoke_member_invitation(
    invitation_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Revoke a pending/expired invitation."""
    org, _ = await _require_org_admin(current_user, session)

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
        raise HTTPException(
            status_code=400,
            detail="Activated invitations cannot be revoked",
        )

    if invitation.status != InvitationStatus.REVOKED:
        invitation.status = InvitationStatus.REVOKED
        session.add(invitation)
        await session.commit()
        await session.refresh(invitation)

    user = (
        await session.execute(select(User).where(User.email == invitation.email.lower()))
    ).scalar_one_or_none()
    return await _serialize_invitation_with_metrics(
        invitation,
        activation_ready=user is not None,
    )


@router.post(
    "/member-invitations/{invitation_id}/resend",
    response_model=OrganizationInvitationRead,
)
async def resend_member_invitation(
    invitation_id: int,
    body: InvitationResendRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Reissue an organization invitation token and reset expiry."""
    org, caller_member = await _require_org_admin(current_user, session)
    if body.expires_in_days < 1 or body.expires_in_days > 30:
        raise HTTPException(status_code=400, detail="expires_in_days must be between 1 and 30")

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
        raise HTTPException(
            status_code=400,
            detail="Activated invitations cannot be resent",
        )

    if invitation.role in (OrgRole.OWNER, OrgRole.ADMIN) and caller_member.role != OrgRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only owners can resend admin/owner invitations",
        )

    invitation.status = InvitationStatus.PENDING
    invitation.token = secrets.token_urlsafe(32)
    invitation.expires_at = datetime.utcnow() + timedelta(days=body.expires_in_days)
    invitation.invited_by_user_id = current_user.id
    invitation.accepted_user_id = None
    invitation.activated_at = None
    session.add(invitation)

    await session.commit()
    await session.refresh(invitation)

    user = (
        await session.execute(select(User).where(User.email == invitation.email.lower()))
    ).scalar_one_or_none()
    return await _serialize_invitation_with_metrics(
        invitation,
        activation_ready=user is not None,
    )


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
