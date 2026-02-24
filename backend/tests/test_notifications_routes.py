"""
Integration tests for notifications.py — /notifications/ CRUD, preferences, push subscriptions
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.notifications import (
    Notification,
    NotificationType,
)
from app.models.rfp import RFP
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


class TestListNotifications:
    """GET /api/v1/notifications/"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/notifications/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_list(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/notifications/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_notifications(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        notif = Notification(
            user_id=test_user.id,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Test Alert",
            message="Something happened",
        )
        db_session.add(notif)
        await db_session.commit()

        response = await client.get("/api/v1/notifications/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Alert"

    @pytest.mark.asyncio
    async def test_unread_only_filter(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        db_session.add(
            Notification(
                user_id=test_user.id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title="Read",
                message="Already read",
                is_read=True,
            )
        )
        db_session.add(
            Notification(
                user_id=test_user.id,
                notification_type=NotificationType.RFP_MATCH,
                title="Unread",
                message="Not read yet",
                is_read=False,
            )
        )
        await db_session.commit()

        response = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
            params={"unread_only": True},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["title"] == "Unread"


class TestUnreadCount:
    """GET /api/v1/notifications/unread-count"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/notifications/unread-count")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unread_count(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        for i in range(3):
            db_session.add(
                Notification(
                    user_id=test_user.id,
                    notification_type=NotificationType.SYSTEM_ALERT,
                    title=f"N{i}",
                    message=f"Msg {i}",
                    is_read=i == 0,
                )
            )
        await db_session.commit()

        response = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["unread_count"] == 2


class TestMarkAsRead:
    """POST /api/v1/notifications/{notification_id}/read"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/notifications/1/read")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_as_read(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        notif = Notification(
            user_id=test_user.id,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Mark Me",
            message="Read me",
        )
        db_session.add(notif)
        await db_session.commit()
        await db_session.refresh(notif)

        response = await client.post(f"/api/v1/notifications/{notif.id}/read", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Notification marked as read"

    @pytest.mark.asyncio
    async def test_mark_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post("/api/v1/notifications/99999/read", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, _ = await _create_second_user(db_session)
        notif = Notification(
            user_id=user2.id,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Other's",
            message="Not yours",
        )
        db_session.add(notif)
        await db_session.commit()
        await db_session.refresh(notif)

        response = await client.post(f"/api/v1/notifications/{notif.id}/read", headers=auth_headers)
        assert response.status_code == 404


class TestMarkAllRead:
    """POST /api/v1/notifications/read-all"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/notifications/read-all")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_all_read(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        for i in range(3):
            db_session.add(
                Notification(
                    user_id=test_user.id,
                    notification_type=NotificationType.SYSTEM_ALERT,
                    title=f"N{i}",
                    message=f"Msg {i}",
                )
            )
        await db_session.commit()

        response = await client.post("/api/v1/notifications/read-all", headers=auth_headers)
        assert response.status_code == 200

        count_response = await client.get(
            "/api/v1/notifications/unread-count", headers=auth_headers
        )
        assert count_response.json()["unread_count"] == 0


class TestDeadlines:
    """GET /api/v1/notifications/deadlines"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/notifications/deadlines")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upcoming_deadlines(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        rfp = RFP(
            user_id=test_user.id,
            title="Deadline RFP",
            solicitation_number="TEST-001",
            agency="DoD",
            status="new",
            response_deadline=datetime.utcnow() + timedelta(days=5),
        )
        db_session.add(rfp)
        await db_session.commit()

        response = await client.get("/api/v1/notifications/deadlines", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Deadline RFP"


class TestPreferences:
    """GET/PUT /api/v1/notifications/preferences"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/notifications/preferences")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_creates_defaults(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] is True
        assert data["deadline_reminders"] is True

    @pytest.mark.asyncio
    async def test_update_preferences(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.put(
            "/api/v1/notifications/preferences",
            headers=auth_headers,
            json={"email_enabled": False, "deadline_reminders": False},
        )
        assert response.status_code == 200

        get_response = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
        data = get_response.json()
        assert data["email_enabled"] is False
        assert data["deadline_reminders"] is False


class TestPushSubscriptions:
    """POST/GET/DELETE /api/v1/notifications/push-subscriptions"""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/notifications/push-subscriptions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_push_subscription(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/notifications/push-subscriptions",
            headers=auth_headers,
            json={
                "endpoint": "https://push.example.com/sub1",
                "p256dh_key": "key123",
                "auth_key": "auth456",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["endpoint"] == "https://push.example.com/sub1"

    @pytest.mark.asyncio
    async def test_list_push_subscriptions(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        await client.post(
            "/api/v1/notifications/push-subscriptions",
            headers=auth_headers,
            json={
                "endpoint": "https://push.example.com/sub1",
                "p256dh_key": "key123",
                "auth_key": "auth456",
            },
        )
        response = await client.get(
            "/api/v1/notifications/push-subscriptions", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_delete_push_subscription(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        create_response = await client.post(
            "/api/v1/notifications/push-subscriptions",
            headers=auth_headers,
            json={
                "endpoint": "https://push.example.com/del",
                "p256dh_key": "key",
                "auth_key": "auth",
            },
        )
        sub_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/notifications/push-subscriptions/{sub_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Push subscription deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete(
            "/api/v1/notifications/push-subscriptions/99999", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upsert_existing_endpoint(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        payload = {
            "endpoint": "https://push.example.com/same",
            "p256dh_key": "key1",
            "auth_key": "auth1",
        }
        r1 = await client.post(
            "/api/v1/notifications/push-subscriptions", headers=auth_headers, json=payload
        )
        assert r1.status_code == 201
        id1 = r1.json()["id"]

        payload["p256dh_key"] = "key2"
        r2 = await client.post(
            "/api/v1/notifications/push-subscriptions", headers=auth_headers, json=payload
        )
        assert r2.status_code == 201
        assert r2.json()["id"] == id1
