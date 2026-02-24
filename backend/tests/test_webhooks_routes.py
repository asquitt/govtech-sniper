"""
Integration tests for webhooks.py:
  - GET    /webhooks
  - POST   /webhooks
  - PATCH  /webhooks/{id}
  - DELETE /webhooks/{id}
  - GET    /webhooks/{id}/deliveries
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.webhook import WebhookDelivery, WebhookSubscription
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def test_webhook(db_session: AsyncSession, test_user: User) -> WebhookSubscription:
    """Create a webhook subscription for testing."""
    webhook = WebhookSubscription(
        user_id=test_user.id,
        name="Test Webhook",
        target_url="https://example.com/webhook",
        event_types=["rfp.created", "proposal.updated"],
        is_active=True,
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)
    return webhook


class TestListWebhooks:
    """Tests for GET /api/v1/webhooks."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/webhooks")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/webhooks", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_webhook: WebhookSubscription,
        test_user: User,
    ):
        response = await client.get("/api/v1/webhooks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Webhook"
        assert data[0]["target_url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        test_webhook: WebhookSubscription,
        db_session: AsyncSession,
    ):
        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/webhooks", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateWebhook:
    """Tests for POST /api/v1/webhooks."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/webhooks",
            json={
                "name": "Test",
                "target_url": "https://example.com/hook",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/webhooks",
            headers=auth_headers,
            json={
                "name": "New Webhook",
                "target_url": "https://example.com/hook",
                "event_types": ["rfp.created"],
                "secret": "mysecret",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Webhook"
        assert data["target_url"] == "https://example.com/hook"
        assert data["event_types"] == ["rfp.created"]

    @pytest.mark.asyncio
    async def test_create_invalid_url(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/webhooks",
            headers=auth_headers,
            json={"name": "Bad", "target_url": "not-a-url"},
        )
        assert response.status_code == 422


class TestUpdateWebhook:
    """Tests for PATCH /api/v1/webhooks/{id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/webhooks/1", json={"name": "Updated"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_webhook: WebhookSubscription,
        test_user: User,
    ):
        response = await client.patch(
            f"/api/v1/webhooks/{test_webhook.id}",
            headers=auth_headers,
            json={"name": "Renamed Webhook", "is_active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Renamed Webhook"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.patch(
            "/api/v1/webhooks/99999",
            headers=auth_headers,
            json={"name": "Nope"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        test_webhook: WebhookSubscription,
        db_session: AsyncSession,
    ):
        other = User(
            email="other2@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"/api/v1/webhooks/{test_webhook.id}",
            headers=headers,
            json={"name": "Hacked"},
        )
        assert response.status_code == 404


class TestDeleteWebhook:
    """Tests for DELETE /api/v1/webhooks/{id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/webhooks/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_webhook: WebhookSubscription,
        test_user: User,
    ):
        response = await client.delete(f"/api/v1/webhooks/{test_webhook.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Webhook deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete("/api/v1/webhooks/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        test_webhook: WebhookSubscription,
        db_session: AsyncSession,
    ):
        other = User(
            email="other3@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.delete(f"/api/v1/webhooks/{test_webhook.id}", headers=headers)
        assert response.status_code == 404


class TestListDeliveries:
    """Tests for GET /api/v1/webhooks/{id}/deliveries."""

    @pytest.mark.asyncio
    async def test_deliveries_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/webhooks/1/deliveries")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deliveries_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_webhook: WebhookSubscription,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/webhooks/{test_webhook.id}/deliveries",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_deliveries_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_webhook: WebhookSubscription,
        test_user: User,
        db_session: AsyncSession,
    ):
        delivery = WebhookDelivery(
            subscription_id=test_webhook.id,
            event_type="rfp.created",
            payload={"rfp_id": 1},
            status="delivered",
            response_code=200,
        )
        db_session.add(delivery)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/webhooks/{test_webhook.id}/deliveries",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "rfp.created"

    @pytest.mark.asyncio
    async def test_deliveries_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/webhooks/99999/deliveries", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deliveries_idor(
        self,
        client: AsyncClient,
        test_webhook: WebhookSubscription,
        db_session: AsyncSession,
    ):
        other = User(
            email="other4@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(
            f"/api/v1/webhooks/{test_webhook.id}/deliveries",
            headers=headers,
        )
        assert response.status_code == 404
