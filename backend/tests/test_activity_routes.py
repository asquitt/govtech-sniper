"""
Integration tests for activity.py — GET /activity/proposals/{proposal_id}
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityFeedEntry, ActivityType
from app.models.proposal import Proposal
from app.models.user import User


class TestListActivity:
    """GET /api/v1/activity/proposals/{proposal_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.get(f"/api/v1/activity/proposals/{test_proposal.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_feed(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        response = await client.get(
            f"/api/v1/activity/proposals/{test_proposal.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_entries(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        entry = ActivityFeedEntry(
            proposal_id=test_proposal.id,
            user_id=test_user.id,
            activity_type=ActivityType.SECTION_EDITED,
            summary="Edited section 1",
        )
        db_session.add(entry)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/activity/proposals/{test_proposal.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["activity_type"] == "section_edited"
        assert data[0]["summary"] == "Edited section 1"

    @pytest.mark.asyncio
    async def test_filter_by_activity_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        for at in [ActivityType.SECTION_EDITED, ActivityType.COMMENT_ADDED]:
            db_session.add(
                ActivityFeedEntry(
                    proposal_id=test_proposal.id,
                    user_id=test_user.id,
                    activity_type=at,
                    summary=f"Activity {at.value}",
                )
            )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/activity/proposals/{test_proposal.id}",
            headers=auth_headers,
            params={"activity_type": "comment_added"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["activity_type"] == "comment_added"

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        for i in range(5):
            db_session.add(
                ActivityFeedEntry(
                    proposal_id=test_proposal.id,
                    user_id=test_user.id,
                    activity_type=ActivityType.SECTION_EDITED,
                    summary=f"Edit {i}",
                )
            )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/activity/proposals/{test_proposal.id}",
            headers=auth_headers,
            params={"limit": 2, "offset": 0},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

        response2 = await client.get(
            f"/api/v1/activity/proposals/{test_proposal.id}",
            headers=auth_headers,
            params={"limit": 2, "offset": 2},
        )
        assert response2.status_code == 200
        assert len(response2.json()) == 2
