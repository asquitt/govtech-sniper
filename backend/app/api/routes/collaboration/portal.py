"""Partner portal read-only view endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.api.utils import get_or_404
from app.database import get_session
from app.models.collaboration import (
    SharedDataPermission,
    SharedWorkspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.models.rfp import RFP
from app.models.user import User
from app.schemas.collaboration import MemberRead, PortalView
from app.services.auth_service import UserAuth

from .helpers import _is_portal_visible_shared_item, _require_member_role, _serialize_shared_data

router = APIRouter()


@router.get("/portal/{workspace_id}", response_model=PortalView)
async def partner_portal(
    workspace_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PortalView:
    """Read-only portal view for workspace members."""
    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)
    ws = await get_or_404(session, SharedWorkspace, workspace_id, "Workspace not found")

    rfp_title = None
    if ws.rfp_id:
        rfp = await session.get(RFP, ws.rfp_id)
        if rfp:
            rfp_title = rfp.title

    perms_result = await session.execute(
        select(SharedDataPermission).where(SharedDataPermission.workspace_id == workspace_id)
    )
    shared_items = [
        _serialize_shared_data(p)
        for p in perms_result.scalars().all()
        if _is_portal_visible_shared_item(
            p,
            user_id=current_user.id,
            owner_id=ws.owner_id,
        )
    ]

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
