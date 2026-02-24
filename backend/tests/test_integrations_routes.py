"""
Integration tests for integrations.py:
  - GET    /integrations/providers
  - GET    /integrations
  - POST   /integrations
  - PATCH  /integrations/{id}
  - POST   /integrations/{id}/test
  - POST   /integrations/{id}/sync
  - GET    /integrations/{id}/syncs
  - POST   /integrations/{id}/webhook
  - GET    /integrations/{id}/webhooks
  - DELETE /integrations/{id}
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationConfig, IntegrationProvider
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def slack_integration(db_session: AsyncSession, test_user: User) -> IntegrationConfig:
    """Create a Slack integration for testing."""
    integration = IntegrationConfig(
        user_id=test_user.id,
        provider=IntegrationProvider.SLACK,
        name="Test Slack",
        is_enabled=True,
        config={"webhook_url": "https://hooks.slack.com/test"},
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


@pytest.fixture
async def sharepoint_integration(db_session: AsyncSession, test_user: User) -> IntegrationConfig:
    """Create a SharePoint integration (supports sync/webhooks)."""
    integration = IntegrationConfig(
        user_id=test_user.id,
        provider=IntegrationProvider.SHAREPOINT,
        name="Test SharePoint",
        is_enabled=True,
        config={
            "site_url": "https://test.sharepoint.com",
            "tenant_id": "tenant-123",
            "client_id": "client-123",
            "client_secret": "secret-123",
        },
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


class TestListProviders:
    """Tests for GET /api/v1/integrations/providers."""

    @pytest.mark.asyncio
    async def test_providers_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/integrations/providers")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_providers_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/integrations/providers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        providers = [p["provider"] for p in data]
        assert "slack" in providers
        assert "sharepoint" in providers


class TestListIntegrations:
    """Tests for GET /api/v1/integrations."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/integrations")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/integrations", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.get("/api/v1/integrations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "slack"

    @pytest.mark.asyncio
    async def test_list_filter_by_provider(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.get("/api/v1/integrations?provider=slack", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        slack_integration: IntegrationConfig,
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

        response = await client.get("/api/v1/integrations", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateIntegration:
    """Tests for POST /api/v1/integrations."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/integrations",
            json={"provider": "slack", "config": {"webhook_url": "https://a.b"}},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/integrations",
            headers=auth_headers,
            json={
                "provider": "slack",
                "name": "My Slack",
                "config": {"webhook_url": "https://hooks.slack.com/test"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "slack"
        assert data["name"] == "My Slack"


class TestUpdateIntegration:
    """Tests for PATCH /api/v1/integrations/{id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/integrations/1", json={"name": "Updated"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.patch(
            f"/api/v1/integrations/{slack_integration.id}",
            headers=auth_headers,
            json={"name": "Renamed Slack"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Slack"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.patch(
            "/api/v1/integrations/99999",
            headers=auth_headers,
            json={"name": "Nope"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        slack_integration: IntegrationConfig,
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
            f"/api/v1/integrations/{slack_integration.id}",
            headers=headers,
            json={"name": "Hacked"},
        )
        assert response.status_code == 404


class TestTestIntegration:
    """Tests for POST /api/v1/integrations/{id}/test."""

    @pytest.mark.asyncio
    async def test_test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/integrations/1/test")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_test_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/integrations/{slack_integration.id}/test",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "error", "disabled")

    @pytest.mark.asyncio
    async def test_test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post("/api/v1/integrations/99999/test", headers=auth_headers)
        assert response.status_code == 404


class TestRunSync:
    """Tests for POST /api/v1/integrations/{id}/sync."""

    @pytest.mark.asyncio
    async def test_sync_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/integrations/1/sync")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sharepoint_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/integrations/{sharepoint_integration.id}/sync",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["items_synced"] > 0

    @pytest.mark.asyncio
    async def test_sync_unsupported_provider(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/integrations/{slack_integration.id}/sync",
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post("/api/v1/integrations/99999/sync", headers=auth_headers)
        assert response.status_code == 404


class TestListSyncs:
    """Tests for GET /api/v1/integrations/{id}/syncs."""

    @pytest.mark.asyncio
    async def test_syncs_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/integrations/1/syncs")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_syncs_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/integrations/{slack_integration.id}/syncs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_syncs_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/integrations/99999/syncs", headers=auth_headers)
        assert response.status_code == 404


class TestReceiveWebhook:
    """Tests for POST /api/v1/integrations/{id}/webhook."""

    @pytest.mark.asyncio
    async def test_webhook_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/integrations/1/webhook",
            json={"event_type": "test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_webhook_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sharepoint_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/integrations/{sharepoint_integration.id}/webhook",
            headers=auth_headers,
            json={"event_type": "file.created", "file": "doc.pdf"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "file.created"

    @pytest.mark.asyncio
    async def test_webhook_unsupported_provider(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/integrations/{slack_integration.id}/webhook",
            headers=auth_headers,
            json={"event_type": "test"},
        )
        assert response.status_code == 400


class TestListWebhookEvents:
    """Tests for GET /api/v1/integrations/{id}/webhooks."""

    @pytest.mark.asyncio
    async def test_webhook_events_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/integrations/1/webhooks")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_webhook_events_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/integrations/{slack_integration.id}/webhooks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []


class TestDeleteIntegration:
    """Tests for DELETE /api/v1/integrations/{id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/integrations/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        slack_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.delete(
            f"/api/v1/integrations/{slack_integration.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Integration deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete("/api/v1/integrations/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        slack_integration: IntegrationConfig,
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

        response = await client.delete(
            f"/api/v1/integrations/{slack_integration.id}",
            headers=headers,
        )
        assert response.status_code == 404
