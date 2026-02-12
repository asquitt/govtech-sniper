"""
RFP Sniper - Inbox Routes
============================
Shared team inbox for workspace collaboration messages.
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.inbox import InboxMessage, InboxMessageType
from app.models.user import User
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/collaboration", tags=["Inbox"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class InboxMessageCreate(BaseModel):
    subject: str
    body: str
    message_type: str = "general"
    attachments: list[str] | None = None


class InboxMessageRead(BaseModel):
    id: int
    workspace_id: int
    sender_id: int
    sender_name: str | None = None
    sender_email: str | None = None
    subject: str
    body: str
    message_type: str
    is_read: bool
    read_by: list[int]
    attachments: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InboxListResponse(BaseModel):
    items: list[InboxMessageRead]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


async def _serialize_message(
    msg: InboxMessage,
    session: AsyncSession,
) -> InboxMessageRead:
    user = await session.get(User, msg.sender_id)
    return InboxMessageRead(
        id=msg.id,
        workspace_id=msg.workspace_id,
        sender_id=msg.sender_id,
        sender_name=user.full_name if user else None,
        sender_email=user.email if user else None,
        subject=msg.subject,
        body=msg.body,
        message_type=msg.message_type,
        is_read=msg.is_read,
        read_by=_parse_json_list(msg.read_by),
        attachments=_parse_json_list(msg.attachments),
        created_at=msg.created_at,
        updated_at=msg.updated_at,
    )


def _validate_message_type(value: str) -> str:
    valid = {t.value for t in InboxMessageType}
    if value not in valid:
        raise HTTPException(
            400, f"Invalid message_type. Must be one of: {', '.join(sorted(valid))}"
        )
    return value


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/inbox",
    response_model=InboxListResponse,
)
async def list_inbox_messages(
    workspace_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InboxListResponse:
    """List inbox messages for a workspace (paginated)."""
    # Import here to avoid circular imports at module level
    from app.api.routes.collaboration import _require_member_role
    from app.models.collaboration import WorkspaceRole

    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)

    count_q = select(func.count(InboxMessage.id)).where(InboxMessage.workspace_id == workspace_id)
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    q = (
        select(InboxMessage)
        .where(InboxMessage.workspace_id == workspace_id)
        .order_by(InboxMessage.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    messages = (await session.execute(q)).scalars().all()
    items = [await _serialize_message(m, session) for m in messages]

    return InboxListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/workspaces/{workspace_id}/inbox",
    response_model=InboxMessageRead,
    status_code=201,
)
async def send_inbox_message(
    workspace_id: int,
    payload: InboxMessageCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InboxMessageRead:
    """Send a message to a workspace's shared inbox."""
    from app.api.routes.collaboration import _require_member_role
    from app.models.collaboration import WorkspaceRole

    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.CONTRIBUTOR, session)
    _validate_message_type(payload.message_type)

    msg = InboxMessage(
        workspace_id=workspace_id,
        sender_id=current_user.id,
        subject=payload.subject,
        body=payload.body,
        message_type=payload.message_type,
        attachments=json.dumps(payload.attachments) if payload.attachments else None,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return await _serialize_message(msg, session)


@router.patch(
    "/workspaces/{workspace_id}/inbox/{message_id}/read",
    response_model=InboxMessageRead,
)
async def mark_message_read(
    workspace_id: int,
    message_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InboxMessageRead:
    """Mark an inbox message as read by the current user."""
    from app.api.routes.collaboration import _require_member_role
    from app.models.collaboration import WorkspaceRole

    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)

    result = await session.execute(
        select(InboxMessage).where(
            InboxMessage.id == message_id,
            InboxMessage.workspace_id == workspace_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")

    read_by = _parse_json_list(msg.read_by)
    if current_user.id not in read_by:
        read_by.append(current_user.id)
        msg.read_by = json.dumps(read_by)
        msg.is_read = True
        msg.updated_at = datetime.utcnow()
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

    return await _serialize_message(msg, session)


@router.delete(
    "/workspaces/{workspace_id}/inbox/{message_id}",
    status_code=204,
)
async def delete_inbox_message(
    workspace_id: int,
    message_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an inbox message (admin or sender only)."""
    from app.api.routes.collaboration import _get_workspace_or_404, _require_member_role
    from app.models.collaboration import WorkspaceRole

    await _require_member_role(workspace_id, current_user.id, WorkspaceRole.VIEWER, session)

    result = await session.execute(
        select(InboxMessage).where(
            InboxMessage.id == message_id,
            InboxMessage.workspace_id == workspace_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")

    # Only sender or workspace admin/owner can delete
    ws = await _get_workspace_or_404(workspace_id, session)
    is_owner = ws.owner_id == current_user.id
    is_sender = msg.sender_id == current_user.id
    if not is_owner and not is_sender:
        # Check if user is admin
        from app.models.collaboration import WorkspaceMember

        member_result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
        )
        member = member_result.scalar_one_or_none()
        role_value = (
            member.role.value
            if member and hasattr(member.role, "value")
            else (member.role if member else None)
        )
        if not member or role_value != WorkspaceRole.ADMIN.value:
            raise HTTPException(403, "Only message sender or workspace admin can delete messages")

    await session.delete(msg)
    await session.commit()
