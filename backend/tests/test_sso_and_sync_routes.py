"""
Integration tests for integrations/sso_and_sync.py —
SSO authorize/callback, sync runs, webhook events.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationConfig, IntegrationProvider
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


@pytest.fixture
async def sso_integration(db_session: AsyncSession, test_user: User) -> IntegrationConfig:
    """Create an SSO-type integration (Okta)."""
    integration = IntegrationConfig(
        user_id=test_user.id,
        provider=IntegrationProvider.OKTA,
        name="Test Okta SSO",
        config={
            "domain": "test.okta.com",
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "issuer": "https://test.okta.com",
            "redirect_uri": "https://app.example.com/callback",
        },
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


@pytest.fixture
async def sharepoint_integration(db_session: AsyncSession, test_user: User) -> IntegrationConfig:
    """Create a SharePoint integration that supports sync."""
    integration = IntegrationConfig(
        user_id=test_user.id,
        provider=IntegrationProvider.SHAREPOINT,
        name="Test SharePoint",
        config={
            "tenant_id": "test-tenant",
            "client_id": "sp-client-id",
            "client_secret": "sp-secret",
            "site_url": "https://test.sharepoint.com",
        },
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


async def _other_user_headers(db_session: AsyncSession) -> dict:
    user = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    tokens = create_token_pair(user.id, user.email, user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


class TestSsoAuthorize:
    """POST /api/v1/integrations/{id}/sso/authorize"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/integrations/1/sso/authorize")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.post(
            "/api/v1/integrations/99999/sso/authorize",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_blocked(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sso_integration: IntegrationConfig,
        test_user: User,
    ):
        """Another user cannot authorize someone else's integration."""
        headers = await _other_user_headers(db_session)
        resp = await client.post(
            f"/api/v1/integrations/{sso_integration.id}/sso/authorize",
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_authorize_sso(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sso_integration: IntegrationConfig,
        test_user: User,
    ):
        resp = await client.post(
            f"/api/v1/integrations/{sso_integration.id}/sso/authorize",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_url" in data
        assert data["provider"] == "okta"
        assert "state" in data

    @pytest.mark.asyncio
    async def test_non_sso_provider_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sharepoint_integration: IntegrationConfig,
        test_user: User,
    ):
        resp = await client.post(
            f"/api/v1/integrations/{sharepoint_integration.id}/sso/authorize",
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestSsoCallback:
    """POST /api/v1/integrations/{id}/sso/callback"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/integrations/1/sso/callback",
            json={"code": "abc", "state": "xyz"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.post(
            "/api/v1/integrations/99999/sso/callback",
            headers=auth_headers,
            json={"code": "abc", "state": "xyz"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_callback_with_code(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sso_integration: IntegrationConfig,
        test_user: User,
    ):
        resp = await client.post(
            f"/api/v1/integrations/{sso_integration.id}/sso/callback",
            headers=auth_headers,
            json={"code": "test-auth-code"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        # Exchange will error since no real SSO server
        assert data["token_exchange"] in ("ok", "error")


class TestRunSync:
    """POST /api/v1/integrations/{id}/sync"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/integrations/1/sync")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.post(
            "/api/v1/integrations/99999/sync",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sharepoint_integration: IntegrationConfig,
        test_user: User,
    ):
        resp = await client.post(
            f"/api/v1/integrations/{sharepoint_integration.id}/sync",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["items_synced"] == 12  # SharePoint returns 12

    @pytest.mark.asyncio
    async def test_sync_unsupported_provider(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sso_integration: IntegrationConfig,
        test_user: User,
    ):
        """SSO provider doesn't support sync."""
        resp = await client.post(
            f"/api/v1/integrations/{sso_integration.id}/sync",
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestListSyncs:
    """GET /api/v1/integrations/{id}/syncs"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/integrations/1/syncs")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get(
            "/api/v1/integrations/99999/syncs",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_syncs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sharepoint_integration: IntegrationConfig,
        test_user: User,
    ):
        resp = await client.get(
            f"/api/v1/integrations/{sharepoint_integration.id}/syncs",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestWebhookReceive:
    """POST /api/v1/integrations/{id}/webhook"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/integrations/1/webhook",
            json={"event_type": "test"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.post(
            "/api/v1/integrations/99999/webhook",
            headers=auth_headers,
            json={"event_type": "test"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_receive_webhook(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sharepoint_integration: IntegrationConfig,
        test_user: User,
    ):
        resp = await client.post(
            f"/api/v1/integrations/{sharepoint_integration.id}/webhook",
            headers=auth_headers,
            json={"event_type": "contract_updated", "data": {"id": 42}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "contract_updated"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_webhook_unsupported_provider(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sso_integration: IntegrationConfig,
        test_user: User,
    ):
        """SSO provider doesn't support webhooks."""
        resp = await client.post(
            f"/api/v1/integrations/{sso_integration.id}/webhook",
            headers=auth_headers,
            json={"event_type": "test"},
        )
        assert resp.status_code == 400


class TestWebhookList:
    """GET /api/v1/integrations/{id}/webhooks"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/integrations/1/webhooks")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        resp = await client.get(
            "/api/v1/integrations/99999/webhooks",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_webhooks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sharepoint_integration: IntegrationConfig,
        test_user: User,
    ):
        resp = await client.get(
            f"/api/v1/integrations/{sharepoint_integration.id}/webhooks",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []
