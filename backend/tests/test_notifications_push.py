"""Integration tests for push subscription notification endpoints."""

import pytest
from httpx import AsyncClient


class TestPushSubscriptions:
    @pytest.mark.asyncio
    async def test_push_subscription_lifecycle(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/notifications/push-subscriptions",
            headers=auth_headers,
            json={
                "endpoint": "browser://test/device-1",
                "p256dh_key": "public-key",
                "auth_key": "auth-key",
                "user_agent": "pytest-agent",
            },
        )
        assert create.status_code == 201
        created = create.json()
        assert created["endpoint"] == "browser://test/device-1"

        listed = await client.get("/api/v1/notifications/push-subscriptions", headers=auth_headers)
        assert listed.status_code == 200
        rows = listed.json()
        assert len(rows) == 1
        assert rows[0]["endpoint"] == "browser://test/device-1"

        delete = await client.delete(
            f"/api/v1/notifications/push-subscriptions/{created['id']}",
            headers=auth_headers,
        )
        assert delete.status_code == 200

        listed_again = await client.get(
            "/api/v1/notifications/push-subscriptions", headers=auth_headers
        )
        assert listed_again.status_code == 200
        assert listed_again.json() == []
