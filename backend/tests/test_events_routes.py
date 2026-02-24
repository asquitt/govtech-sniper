"""
Integration tests for events.py — /events/ CRUD, ingest, alerts, calendar
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import IndustryEvent
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    user2 = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    tokens = create_token_pair(user2.id, user2.email, user2.tier)
    return user2, {"Authorization": f"Bearer {tokens.access_token}"}


class TestListEvents:
    """GET /api/v1/events"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/events")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_list(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/events", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateEvent:
    """POST /api/v1/events"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/events", json={"title": "Test"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_event(self, client: AsyncClient, auth_headers: dict, test_user: User):
        event_date = (datetime.utcnow() + timedelta(days=10)).isoformat()
        response = await client.post(
            "/api/v1/events",
            headers=auth_headers,
            json={
                "title": "DHS Industry Day",
                "agency": "DHS",
                "event_type": "industry_day",
                "date": event_date,
                "location": "Washington, DC",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "DHS Industry Day"
        assert data["agency"] == "DHS"


class TestGetEvent:
    """GET /api/v1/events/{event_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/events/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_event(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        event = IndustryEvent(
            user_id=test_user.id,
            title="Test Event",
            event_type="industry_day",
            date=datetime.utcnow() + timedelta(days=5),
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        response = await client.get(f"/api/v1/events/{event.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Test Event"

    @pytest.mark.asyncio
    async def test_get_event_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/events/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_event_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        event = IndustryEvent(
            user_id=user2.id,
            title="Other's Event",
            event_type="conference",
            date=datetime.utcnow() + timedelta(days=5),
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        response = await client.get(f"/api/v1/events/{event.id}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateEvent:
    """PATCH /api/v1/events/{event_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/events/1", json={"title": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_event(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        event = IndustryEvent(
            user_id=test_user.id,
            title="Original",
            event_type="conference",
            date=datetime.utcnow() + timedelta(days=5),
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        response = await client.patch(
            f"/api/v1/events/{event.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.patch(
            "/api/v1/events/99999", headers=auth_headers, json={"title": "X"}
        )
        assert response.status_code == 404


class TestDeleteEvent:
    """DELETE /api/v1/events/{event_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/events/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_event(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        event = IndustryEvent(
            user_id=test_user.id,
            title="Delete Me",
            event_type="conference",
            date=datetime.utcnow() + timedelta(days=5),
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        response = await client.delete(f"/api/v1/events/{event.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Event deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete("/api/v1/events/99999", headers=auth_headers)
        assert response.status_code == 404


class TestUpcomingEvents:
    """GET /api/v1/events/upcoming"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/events/upcoming")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upcoming_returns_future_events(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        future_event = IndustryEvent(
            user_id=test_user.id,
            title="Future Event",
            event_type="industry_day",
            date=datetime.utcnow() + timedelta(days=10),
        )
        db_session.add(future_event)
        await db_session.commit()

        response = await client.get("/api/v1/events/upcoming", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestCalendarEvents:
    """GET /api/v1/events/calendar"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/events/calendar", params={"month": 3, "year": 2026})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_calendar_filters_by_month(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        event = IndustryEvent(
            user_id=test_user.id,
            title="March Event",
            event_type="webinar",
            date=datetime(2026, 3, 15),
        )
        db_session.add(event)
        await db_session.commit()

        response = await client.get(
            "/api/v1/events/calendar",
            headers=auth_headers,
            params={"month": 3, "year": 2026},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        response2 = await client.get(
            "/api/v1/events/calendar",
            headers=auth_headers,
            params={"month": 4, "year": 2026},
        )
        assert response2.status_code == 200
        assert len(response2.json()) == 0


class TestIngestEvents:
    """POST /api/v1/events/ingest"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/events/ingest")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_curated(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/events/ingest",
            headers=auth_headers,
            params={"include_curated": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] >= 3
        assert data["candidates"] >= 3

    @pytest.mark.asyncio
    async def test_ingest_deduplication(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        r1 = await client.post("/api/v1/events/ingest", headers=auth_headers)
        assert r1.status_code == 200
        first_created = r1.json()["created"]

        r2 = await client.post("/api/v1/events/ingest", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["created"] == 0
        assert r2.json()["existing"] == first_created


class TestEventAlerts:
    """GET /api/v1/events/alerts"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/events/alerts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_alerts_response_schema(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/events/alerts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total" in data
        assert "evaluated" in data
