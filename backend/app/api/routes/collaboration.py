"""
RFP Sniper - Collaboration Routes
====================================
Shared workspaces, invitations, member management, and data sharing.
"""

import secrets
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.user import User
from app.models.rfp import RFP
from app.models.collaboration import (
    SharedWorkspace,
    WorkspaceInvitation,
    WorkspaceMember,
    SharedDataPermission,
    WorkspaceRole,
)
from app.schemas.collaboration import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceRead,
    InvitationCreate,
    InvitationRead,
    MemberRead,
    ShareDataCreate,
    SharedDataRead,
    PortalView,
)

router = APIRouter(prefix="/collaboration", tags=["Collaboration"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_workspace_or_404(
    workspace_id: int,
    session: AsyncSession,
) -> SharedWorkspace:
    ws = await session.get(SharedWorkspace, workspace_id)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws


async def _require_member_role(
    workspace_id: int,
    user_id: int,
    min_role: WorkspaceRole,
    session: AsyncSession,
) -> None:
    """Check the user is the owner or has at least `min_role`."""
    ws = await _get_workspace_or_404(workspace_id, session)
    if ws.owner_id == user_id:
        return  # Owner always has full access

    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(403, "Not a member of this workspace")

    role_order = {WorkspaceRole.VIEWER: 0, WorkspaceRole.CONTRIBUTOR: 1, WorkspaceRole.ADMIN: 2}
    if role_order.get(WorkspaceRole(member.role), 0) < role_order.get(min_role, 0):
        raise HTTPException(403, "Insufficient permissions")


async def _member_count(workspace_id: int, session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(WorkspaceMember.id)).where(
            WorkspaceMember.workspace_id == workspace_id
        )
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------

@router.get("/workspaces", response_model=List[WorkspaceRead])
async def list_workspaces(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[WorkspaceRead]:
    """List workspaces the user owns or is a member of."""
    # Owned
    owned_q = select(SharedWorkspace).where(SharedWorkspace.owner_id == current_user.id)
    owned = (await session.execute(owned_q)).scalars().all()

    # Member
    member_q = (
        select(SharedWorkspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == SharedWorkspace.id)
        .where(WorkspaceMember.user_id == current_user.id)
    )
    membered = (await session.execute(member_q)).scalars().all()

    seen: set[int] = set()
    results: List[WorkspaceRead] = []
    for ws in [*owned, *membered]:
        if ws.id in seen:
            continue
        seen.add(ws.id)
        count = await _member_count(ws.id, session)
        results.append(
            WorkspaceRead(
                id=ws.id,
                owner_id=ws.owner_id,
                rfp_id=ws.rfp_id,
                name=ws.name,
                description=ws.description,
                member_count=count,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
            )
        )
    return results


@router.post("/workspaces", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceRead:
    ws = SharedWorkspace(
        owner_id=current_user.id,
        name=payload.name,
        rfp_id=payload.rfp_id,
        description=payload.description,
    )
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    return WorkspaceRead(
        id=ws.id,
        owner_id=ws.owner_id,
        rfp_id=ws.rfp_id,
        name=ws.name,
        description=ws.description,
        member_count=0,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceRead:
    ws = await _get_workspace_or_404(workspace_id, session)
    if ws.owner_id != current_user.id:
        raise HTTPException(403, "Only the workspace owner can update it")

    if payload.name is not None:
        ws.name = payload.name
    if payload.description is not None:
        ws.description = payload.description
    ws.updated_at = datetime.utcnow()
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    count = await _member_count(ws.id, session)
    return WorkspaceRead(
        id=ws.id,
        owner_id=ws.owner_id,
        rfp_id=ws.rfp_id,
        name=ws.name,
        description=ws.description,
        member_count=count,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    ws = await _get_workspace_or_404(workspace_id, session)
    if ws.owner_id != current_user.id:
        raise HTTPException(403, "Only the workspace owner can delete it")
    await session.delete(ws)
    await session.commit()


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

@router.post("/workspaces/{workspace_id}/invite", response_model=InvitationRead, status_code=201)
async def invite_to_workspace(
    workspace_id: int,
    payload: InvitationCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvitationRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)

    token = secrets.token_urlsafe(32)
    invite = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=payload.email,
        role=WorkspaceRole(payload.role),
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return InvitationRead(
        id=invite.id,
        workspace_id=invite.workspace_id,
        email=invite.email,
        role=invite.role.value if hasattr(invite.role, "value") else invite.role,
        is_accepted=invite.is_accepted,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.get("/workspaces/{workspace_id}/invitations", response_model=List[InvitationRead])
async def list_invitations(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[InvitationRead]:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    result = await session.execute(
        select(WorkspaceInvitation).where(WorkspaceInvitation.workspace_id == workspace_id)
    )
    invites = result.scalars().all()
    return [
        InvitationRead(
            id=i.id,
            workspace_id=i.workspace_id,
            email=i.email,
            role=i.role.value if hasattr(i.role, "value") else i.role,
            is_accepted=i.is_accepted,
            expires_at=i.expires_at,
            created_at=i.created_at,
        )
        for i in invites
    ]


@router.post("/invitations/accept", response_model=MemberRead)
async def accept_invitation(
    token: str = Query(...),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MemberRead:
    result = await session.execute(
        select(WorkspaceInvitation).where(WorkspaceInvitation.token == token)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(404, "Invitation not found")
    if invite.is_accepted:
        raise HTTPException(400, "Invitation already accepted")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invitation has expired")

    # Mark accepted
    invite.is_accepted = True
    invite.accepted_user_id = current_user.id

    # Create membership
    member = WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=current_user.id,
        role=invite.role,
    )
    session.add(invite)
    session.add(member)
    await session.commit()
    await session.refresh(member)

    # Fetch user info
    user = await session.get(User, current_user.id)
    return MemberRead(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role.value if hasattr(member.role, "value") else member.role,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        created_at=member.created_at,
    )


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/members", response_model=List[MemberRead])
async def list_members(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[MemberRead]:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    result = await session.execute(
        select(WorkspaceMember, User)
        .outerjoin(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    rows = result.all()
    return [
        MemberRead(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role.value if hasattr(m.role, "value") else m.role,
            user_email=u.email if u else None,
            user_name=u.full_name if u else None,
            created_at=m.created_at,
        )
        for m, u in rows
    ]


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=204)
async def remove_member(
    workspace_id: int,
    member_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)
    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Member not found")
    await session.delete(member)
    await session.commit()


# ---------------------------------------------------------------------------
# Data sharing
# ---------------------------------------------------------------------------

@router.post("/workspaces/{workspace_id}/share", response_model=SharedDataRead, status_code=201)
async def share_data(
    workspace_id: int,
    payload: ShareDataCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SharedDataRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    perm = SharedDataPermission(
        workspace_id=workspace_id,
        data_type=payload.data_type,
        entity_id=payload.entity_id,
    )
    session.add(perm)
    await session.commit()
    await session.refresh(perm)
    return SharedDataRead(
        id=perm.id,
        workspace_id=perm.workspace_id,
        data_type=perm.data_type.value if hasattr(perm.data_type, "value") else perm.data_type,
        entity_id=perm.entity_id,
        created_at=perm.created_at,
    )


@router.get("/workspaces/{workspace_id}/shared", response_model=List[SharedDataRead])
async def list_shared_data(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[SharedDataRead]:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    perms = result.scalars().all()
    return [
        SharedDataRead(
            id=p.id,
            workspace_id=p.workspace_id,
            data_type=p.data_type.value if hasattr(p.data_type, "value") else p.data_type,
            entity_id=p.entity_id,
            created_at=p.created_at,
        )
        for p in perms
    ]


@router.delete("/workspaces/{workspace_id}/shared/{perm_id}", status_code=204)
async def unshare_data(
    workspace_id: int,
    perm_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    result = await session.execute(
        select(SharedDataPermission).where(
            SharedDataPermission.id == perm_id,
            SharedDataPermission.workspace_id == workspace_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(404, "Permission not found")
    await session.delete(perm)
    await session.commit()


# ---------------------------------------------------------------------------
# Partner Portal (read-only view)
# ---------------------------------------------------------------------------

@router.get("/portal/{workspace_id}", response_model=PortalView)
async def partner_portal(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PortalView:
    """Read-only portal view for workspace members."""
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    ws = await _get_workspace_or_404(workspace_id, session)

    # RFP title
    rfp_title = None
    if ws.rfp_id:
        rfp = await session.get(RFP, ws.rfp_id)
        if rfp:
            rfp_title = rfp.title

    # Shared items
    perms_result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    shared_items = [
        SharedDataRead(
            id=p.id,
            workspace_id=p.workspace_id,
            data_type=p.data_type.value if hasattr(p.data_type, "value") else p.data_type,
            entity_id=p.entity_id,
            created_at=p.created_at,
        )
        for p in perms_result.scalars().all()
    ]

    # Members
    members_result = await session.execute(
        select(WorkspaceMember, User)
        .outerjoin(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    members = [
        MemberRead(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role.value if hasattr(m.role, "value") else m.role,
            user_email=u.email if u else None,
            user_name=u.full_name if u else None,
            created_at=m.created_at,
        )
        for m, u in members_result.all()
    ]

    return PortalView(
        workspace_name=ws.name,
        workspace_description=ws.description,
        rfp_title=rfp_title,
        shared_items=shared_items,
        members=members,
    )


# ---------------------------------------------------------------------------
# Real-Time Presence & Section Locking (REST fallback)
# ---------------------------------------------------------------------------

@router.get("/proposals/{proposal_id}/presence")
async def get_document_presence(
    proposal_id: int,
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Get who is currently viewing/editing a proposal."""
    from app.api.routes.websocket import manager

    users = manager.get_presence(proposal_id)
    locks = [
        lock for lock in manager.section_locks.values()
    ]
    return {
        "proposal_id": proposal_id,
        "users": users,
        "locks": locks,
    }


@router.post("/sections/{section_id}/lock")
async def lock_section(
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Request a lock on a proposal section for editing."""
    from app.api.routes.websocket import manager

    # Look up user name
    user = await session.get(User, current_user.id)
    user_name = user.full_name if user and user.full_name else f"User {current_user.id}"

    lock = manager.lock_section(section_id, current_user.id, user_name)
    if not lock:
        existing = manager.get_lock(section_id)
        raise HTTPException(
            409,
            detail={
                "message": "Section is already locked",
                "held_by": existing,
            },
        )
    return lock


@router.delete("/sections/{section_id}/lock", status_code=204)
async def unlock_section(
    section_id: int,
    current_user: UserAuth = Depends(get_current_user),
) -> None:
    """Release a lock on a proposal section."""
    from app.api.routes.websocket import manager

    success = manager.unlock_section(section_id, current_user.id)
    if not success:
        raise HTTPException(403, "You do not hold this lock")
