"""
RFP Sniper - Activity Service
================================
Helper to log activity events.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityFeedEntry, ActivityType


async def log_activity(
    session: AsyncSession,
    proposal_id: int,
    user_id: int,
    activity_type: ActivityType,
    summary: str,
    section_id: int | None = None,
    metadata: dict | None = None,
) -> ActivityFeedEntry:
    """Insert an activity feed entry and commit."""
    entry = ActivityFeedEntry(
        proposal_id=proposal_id,
        user_id=user_id,
        activity_type=activity_type,
        summary=summary,
        section_id=section_id,
        metadata_json=metadata,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry
