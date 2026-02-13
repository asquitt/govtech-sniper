"""Workspace member management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.collaboration import WorkspaceMember, WorkspaceRole
from app.models.user import User
from app.schemas.collaboration import MemberRead, MemberRoleUpdate
from app.services.auth_service import UserAuth

from .helpers import _require_member_role

router = APIRouter()


@router.get("/workspaces/{workspace_id}/members", response_model=list[MemberRead])
async def list_members(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MemberRead]:
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


@router.patch("/workspaces/{workspace_id}/members/{member_id}/role", response_model=MemberRead)
async def update_member_role(
    workspace_id: int,
    member_id: int,
    payload: MemberRoleUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MemberRead:
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.ADMIN, session)

    try:
        new_role = WorkspaceRole(payload.role)
    except ValueError as exc:
        raise HTTPException(400, "Invalid workspace role") from exc

    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(404, "Member not found")

    member.role = new_role
    session.add(member)
    await session.commit()
    await session.refresh(member)

    user = await session.get(User, member.user_id)
    return MemberRead(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role.value if hasattr(member.role, "value") else member.role,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        created_at=member.created_at,
    )


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
