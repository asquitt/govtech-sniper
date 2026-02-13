"""Workspace invitation endpoints."""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.api.utils import get_or_404
from app.database import get_session
from app.models.collaboration import (
    SharedWorkspace,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceRole,
)
from app.models.user import User
from app.schemas.collaboration import InvitationCreate, InvitationRead, MemberRead
from app.services.auth_service import UserAuth

from .helpers import _require_member_role

router = APIRouter()


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
        accept_token=invite.token,
        is_accepted=invite.is_accepted,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.get("/workspaces/{workspace_id}/invitations", response_model=list[InvitationRead])
async def list_invitations(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InvitationRead]:
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
            accept_token=i.token,
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
    if invite.email.lower().strip() != current_user.email.lower().strip():
        raise HTTPException(403, "Invitation email does not match authenticated user")

    workspace = await get_or_404(
        session, SharedWorkspace, invite.workspace_id, "Workspace not found"
    )
    if workspace.owner_id == current_user.id:
        raise HTTPException(400, "Workspace owner already has access")

    membership_result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == invite.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    if membership_result.scalars().first():
        raise HTTPException(400, "User is already a workspace member")

    invite.is_accepted = True
    invite.accepted_user_id = current_user.id

    member = WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=current_user.id,
        role=invite.role,
    )
    session.add(invite)
    session.add(member)
    await session.commit()
    await session.refresh(member)

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
