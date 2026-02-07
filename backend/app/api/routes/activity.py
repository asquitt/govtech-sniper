"""
RFP Sniper - Activity Feed Routes
====================================
Paginated activity feed per proposal.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.activity import ActivityFeedEntry, ActivityType
from app.schemas.activity import ActivityFeedRead
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("/proposals/{proposal_id}", response_model=list[ActivityFeedRead])
async def list_activity(
    proposal_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    activity_type: str | None = None,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ActivityFeedRead]:
    """Paginated activity feed for a proposal."""
    stmt = (
        select(ActivityFeedEntry)
        .where(ActivityFeedEntry.proposal_id == proposal_id)
        .order_by(ActivityFeedEntry.created_at.desc())
    )
    if activity_type:
        stmt = stmt.where(ActivityFeedEntry.activity_type == ActivityType(activity_type))
    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    return [ActivityFeedRead.model_validate(e) for e in result.scalars().all()]
