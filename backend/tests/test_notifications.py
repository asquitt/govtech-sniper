"""
RFP Sniper - Notifications Route Tests
======================================
Regression coverage for notifications API contracts.
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import hash_password


class TestUpcomingDeadlines:
    """Tests for the upcoming deadlines endpoint."""

    @pytest.mark.asyncio
    async def test_deadlines_filters_by_window_and_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user,
    ):
        now = datetime.utcnow()

        secondary_user = User(
            email="secondary@example.com",
            hashed_password=hash_password("Secondary1!"),
            full_name="Secondary User",
            company_name="Secondary Co",
            is_active=True,
        )
        db_session.add(secondary_user)
        await db_session.flush()

        in_window = RFP(
            user_id=test_user.id,
            title="In Window",
            solicitation_number="IN-001",
            agency="Agency A",
            response_deadline=now + timedelta(days=3),
            status="new",
        )
        out_of_window = RFP(
            user_id=test_user.id,
            title="Out of Window",
            solicitation_number="OUT-001",
            agency="Agency B",
            response_deadline=now + timedelta(days=30),
            status="new",
        )
        past_due = RFP(
            user_id=test_user.id,
            title="Past Due",
            solicitation_number="PAST-001",
            agency="Agency C",
            response_deadline=now - timedelta(days=1),
            status="new",
        )
        other_user = RFP(
            user_id=secondary_user.id,
            title="Other User",
            solicitation_number="OTHER-001",
            agency="Agency D",
            response_deadline=now + timedelta(days=2),
            status="new",
        )

        db_session.add_all([in_window, out_of_window, past_due, other_user])
        await db_session.commit()

        response = await client.get(
            "/api/v1/notifications/deadlines",
            headers=auth_headers,
            params={"days": 7},
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["title"] == "In Window"
        assert payload[0]["days_remaining"] >= 0

    @pytest.mark.asyncio
    async def test_deadlines_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/notifications/deadlines")
        assert response.status_code == 401
