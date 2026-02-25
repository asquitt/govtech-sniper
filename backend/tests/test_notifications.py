"""
RFP Sniper - Notifications Route Tests
======================================
Integration tests for notifications, preferences, push subscriptions, and deadlines.
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.notifications import (
    Notification,
    NotificationType,
)
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import hash_password


@pytest_asyncio.fixture
async def notifications(db_session: AsyncSession, test_user: User) -> list[Notification]:
    notifs = [
        Notification(
            user_id=test_user.id,
            notification_type=NotificationType.RFP_MATCH,
            title="New Match",
            message="An RFP matches your profile",
            is_read=False,
        ),
        Notification(
            user_id=test_user.id,
            notification_type=NotificationType.ANALYSIS_COMPLETE,
            title="Analysis Done",
            message="RFP analysis is complete",
            is_read=True,
        ),
        Notification(
            user_id=test_user.id,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="System Update",
            message="Scheduled maintenance tonight",
            is_read=False,
        ),
    ]
    for n in notifs:
        db_session.add(n)
    await db_session.commit()
    for n in notifs:
        await db_session.refresh(n)
    return notifs


# ---- Auth guards ----


class TestNotificationAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/notifications/")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unread_count_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/notifications/unread-count")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_preferences_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/notifications/preferences")
        assert resp.status_code == 401


# ---- List notifications ----


class TestListNotifications:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/notifications/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_all(self, client: AsyncClient, auth_headers: dict, notifications):
        resp = await client.get("/api/v1/notifications/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    @pytest.mark.asyncio
    async def test_list_unread_only(self, client: AsyncClient, auth_headers: dict, notifications):
        resp = await client.get(
            "/api/v1/notifications/", headers=auth_headers, params={"unread_only": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(not n["is_read"] for n in data)


# ---- Unread count ----


class TestUnreadCount:
    @pytest.mark.asyncio
    async def test_unread_count_zero(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_unread_count(self, client: AsyncClient, auth_headers: dict, notifications):
        resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 2


# ---- Mark as read ----


class TestMarkAsRead:
    @pytest.mark.asyncio
    async def test_mark_single_read(self, client: AsyncClient, auth_headers: dict, notifications):
        unread = notifications[0]
        resp = await client.post(f"/api/v1/notifications/{unread.id}/read", headers=auth_headers)
        assert resp.status_code == 200

        count_resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert count_resp.json()["unread_count"] == 1

    @pytest.mark.asyncio
    async def test_mark_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/notifications/99999/read", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_all_read(self, client: AsyncClient, auth_headers: dict, notifications):
        resp = await client.post("/api/v1/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200

        count_resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert count_resp.json()["unread_count"] == 0


# ---- Preferences ----


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_creates_defaults(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email_enabled"] is True
        assert data["deadline_reminders"] is True
        assert data["slack_enabled"] is False

    @pytest.mark.asyncio
    async def test_update_preferences(self, client: AsyncClient, auth_headers: dict):
        # Get first to create defaults
        await client.get("/api/v1/notifications/preferences", headers=auth_headers)

        resp = await client.put(
            "/api/v1/notifications/preferences",
            headers=auth_headers,
            json={
                "email_enabled": False,
                "slack_enabled": True,
                "slack_webhook_url": "https://hooks.slack.com/test",
                "quiet_hours_enabled": True,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
            },
        )
        assert resp.status_code == 200

        get_resp = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
        data = get_resp.json()
        assert data["email_enabled"] is False
        assert data["slack_enabled"] is True
        assert data["quiet_hours_enabled"] is True

    @pytest.mark.asyncio
    async def test_partial_update(self, client: AsyncClient, auth_headers: dict):
        await client.get("/api/v1/notifications/preferences", headers=auth_headers)
        resp = await client.put(
            "/api/v1/notifications/preferences",
            headers=auth_headers,
            json={"deadline_reminders": False},
        )
        assert resp.status_code == 200

        get_resp = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
        data = get_resp.json()
        assert data["deadline_reminders"] is False
        assert data["email_enabled"] is True  # Unchanged


# ---- Push subscriptions ----


class TestPushSubscriptions:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/notifications/push-subscriptions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_subscription(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/notifications/push-subscriptions",
            headers=auth_headers,
            json={
                "endpoint": "https://fcm.googleapis.com/test/send/abc123",
                "p256dh_key": "BNlA1234keydata",
                "auth_key": "authkey123",
                "user_agent": "Chrome/120",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["endpoint"] == "https://fcm.googleapis.com/test/send/abc123"

    @pytest.mark.asyncio
    async def test_create_duplicate_updates(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "endpoint": "https://fcm.googleapis.com/test/send/dup",
            "p256dh_key": "key1",
            "auth_key": "auth1",
        }
        resp1 = await client.post(
            "/api/v1/notifications/push-subscriptions", headers=auth_headers, json=payload
        )
        id1 = resp1.json()["id"]

        payload["p256dh_key"] = "key2_updated"
        resp2 = await client.post(
            "/api/v1/notifications/push-subscriptions", headers=auth_headers, json=payload
        )
        assert resp2.status_code == 201
        # Should update existing rather than create new
        assert resp2.json()["id"] == id1

    @pytest.mark.asyncio
    async def test_delete_subscription(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/notifications/push-subscriptions",
            headers=auth_headers,
            json={
                "endpoint": "https://fcm.googleapis.com/test/del",
                "p256dh_key": "k",
                "auth_key": "a",
            },
        )
        sub_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/notifications/push-subscriptions/{sub_id}", headers=auth_headers
        )
        assert del_resp.status_code == 200

        list_resp = await client.get(
            "/api/v1/notifications/push-subscriptions", headers=auth_headers
        )
        assert len(list_resp.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete(
            "/api/v1/notifications/push-subscriptions/99999", headers=auth_headers
        )
        assert resp.status_code == 404


# ---- Upcoming deadlines ----


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
