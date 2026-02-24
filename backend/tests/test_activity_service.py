"""Unit tests for activity_service module."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityType
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User
from app.services.activity_service import log_activity
from app.services.auth_service import hash_password


@pytest_asyncio.fixture
async def activity_user(db_session: AsyncSession) -> User:
    user = User(
        email="activity@example.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Activity User",
        company_name="Test Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def activity_proposal(db_session: AsyncSession, activity_user: User) -> Proposal:
    from datetime import datetime

    rfp = RFP(
        user_id=activity_user.id,
        title="Activity Test RFP",
        solicitation_number="ACT-001",
        agency="Test Agency",
        status="new",
        posted_date=datetime.utcnow(),
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)

    proposal = Proposal(
        user_id=activity_user.id,
        rfp_id=rfp.id,
        title="Activity Test Proposal",
        status="draft",
        total_sections=3,
        completed_sections=0,
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    return proposal


@pytest.mark.asyncio
async def test_log_activity_creates_entry(
    db_session: AsyncSession, activity_user: User, activity_proposal: Proposal
):
    entry = await log_activity(
        db_session,
        proposal_id=activity_proposal.id,
        user_id=activity_user.id,
        activity_type=ActivityType.SECTION_EDITED,
        summary="Edited section 1",
    )
    assert entry.id is not None
    assert entry.proposal_id == activity_proposal.id
    assert entry.user_id == activity_user.id
    assert entry.activity_type == ActivityType.SECTION_EDITED
    assert entry.summary == "Edited section 1"


@pytest.mark.asyncio
async def test_log_activity_with_section_id(
    db_session: AsyncSession, activity_user: User, activity_proposal: Proposal
):
    entry = await log_activity(
        db_session,
        proposal_id=activity_proposal.id,
        user_id=activity_user.id,
        activity_type=ActivityType.SECTION_GENERATED,
        summary="Generated section",
        section_id=42,
    )
    assert entry.section_id == 42


@pytest.mark.asyncio
async def test_log_activity_with_metadata(
    db_session: AsyncSession, activity_user: User, activity_proposal: Proposal
):
    metadata = {"word_count": 500, "quality_score": 85.5}
    entry = await log_activity(
        db_session,
        proposal_id=activity_proposal.id,
        user_id=activity_user.id,
        activity_type=ActivityType.REVIEW_COMPLETED,
        summary="Review done",
        metadata=metadata,
    )
    assert entry.metadata_json == metadata


@pytest.mark.asyncio
async def test_log_activity_without_optional_fields(
    db_session: AsyncSession, activity_user: User, activity_proposal: Proposal
):
    entry = await log_activity(
        db_session,
        proposal_id=activity_proposal.id,
        user_id=activity_user.id,
        activity_type=ActivityType.MEMBER_JOINED,
        summary="New member",
    )
    assert entry.section_id is None
    assert entry.metadata_json is None


@pytest.mark.asyncio
async def test_log_activity_persists_to_db(
    db_session: AsyncSession, activity_user: User, activity_proposal: Proposal
):
    entry = await log_activity(
        db_session,
        proposal_id=activity_proposal.id,
        user_id=activity_user.id,
        activity_type=ActivityType.STATUS_CHANGED,
        summary="Status changed to review",
    )
    # Entry should have been flushed and refreshed
    assert entry.id is not None
    assert entry.created_at is not None


@pytest.mark.asyncio
async def test_log_activity_all_types(
    db_session: AsyncSession, activity_user: User, activity_proposal: Proposal
):
    """Verify all activity types can be logged."""
    for activity_type in ActivityType:
        entry = await log_activity(
            db_session,
            proposal_id=activity_proposal.id,
            user_id=activity_user.id,
            activity_type=activity_type,
            summary=f"Testing {activity_type.value}",
        )
        assert entry.activity_type == activity_type


@pytest.mark.asyncio
async def test_log_multiple_activities(
    db_session: AsyncSession, activity_user: User, activity_proposal: Proposal
):
    """Multiple activities can be logged for the same proposal."""
    entries = []
    for i in range(5):
        entry = await log_activity(
            db_session,
            proposal_id=activity_proposal.id,
            user_id=activity_user.id,
            activity_type=ActivityType.COMMENT_ADDED,
            summary=f"Comment {i}",
        )
        entries.append(entry)

    assert len(entries) == 5
    ids = {e.id for e in entries}
    assert len(ids) == 5  # All unique IDs
