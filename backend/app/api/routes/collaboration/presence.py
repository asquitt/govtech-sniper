"""Real-time presence and section locking REST endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.services.auth_service import UserAuth

router = APIRouter()


@router.get("/proposals/{proposal_id}/presence")
async def get_document_presence(
    proposal_id: int,
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Get who is currently viewing/editing a proposal."""
    from app.api.routes.websocket import manager

    users = manager.get_presence(proposal_id)
    locks = [lock for lock in manager.section_locks.values()]
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
