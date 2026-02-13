"""Workspace CRUD endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.api.utils import get_or_404
from app.database import get_session
from app.models.collaboration import SharedWorkspace, WorkspaceMember
from app.schemas.collaboration import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.services.auth_service import UserAuth

from .helpers import _member_count

router = APIRouter()


@router.get("/workspaces", response_model=list[WorkspaceRead])
async def list_workspaces(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[WorkspaceRead]:
    """List workspaces the user owns or is a member of."""
    owned_q = select(SharedWorkspace).where(SharedWorkspace.owner_id == current_user.id)
    owned = (await session.execute(owned_q)).scalars().all()

    member_q = (
        select(SharedWorkspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == SharedWorkspace.id)
        .where(WorkspaceMember.user_id == current_user.id)
    )
    membered = (await session.execute(member_q)).scalars().all()

    seen: set[int] = set()
    results: list[WorkspaceRead] = []
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
    ws = await get_or_404(session, SharedWorkspace, workspace_id, "Workspace not found")
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
    ws = await get_or_404(session, SharedWorkspace, workspace_id, "Workspace not found")
    if ws.owner_id != current_user.id:
        raise HTTPException(403, "Only the workspace owner can delete it")
    await session.delete(ws)
    await session.commit()
