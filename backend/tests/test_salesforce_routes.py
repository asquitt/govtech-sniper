"""
Integration tests for salesforce.py:
  - GET  /salesforce/status
  - GET  /salesforce/opportunities
  - POST /salesforce/sync
  - GET  /salesforce/field-mappings
  - POST /salesforce/field-mappings
  - DELETE /salesforce/field-mappings/{id}
  - POST /salesforce/webhooks/inbound
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationConfig, IntegrationProvider
from app.models.salesforce_mapping import SalesforceFieldMapping
from app.models.user import User


@pytest.fixture
async def sf_integration(db_session: AsyncSession, test_user: User) -> IntegrationConfig:
    """Create a Salesforce integration config."""
    integration = IntegrationConfig(
        user_id=test_user.id,
        provider=IntegrationProvider.SALESFORCE,
        name="Test SF",
        is_enabled=True,
        config={
            "instance_url": "https://test.salesforce.com",
            "client_id": "test-client",
            "client_secret": "test-secret",
            "username": "test@sf.com",
            "security_token": "token123",
        },
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


class TestSalesforceStatus:
    """Tests for GET /api/v1/salesforce/status."""

    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/salesforce/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_status_no_config(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/salesforce/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False

    @pytest.mark.asyncio
    async def test_status_with_config(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sf_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.get("/api/v1/salesforce/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["enabled"] is True
        # Connection will fail since SF is fake, but endpoint should not crash
        assert "connected" in data


class TestSalesforceOpportunities:
    """Tests for GET /api/v1/salesforce/opportunities."""

    @pytest.mark.asyncio
    async def test_opportunities_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/salesforce/opportunities")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_opportunities_no_integration(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/salesforce/opportunities", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_opportunities_with_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sf_integration: IntegrationConfig,
        test_user: User,
    ):
        """Should fail gracefully since SF is fake."""
        response = await client.get("/api/v1/salesforce/opportunities", headers=auth_headers)
        # Will get 400 or 502 since SF service can't connect
        assert response.status_code in (400, 502)


class TestSalesforceSync:
    """Tests for POST /api/v1/salesforce/sync."""

    @pytest.mark.asyncio
    async def test_sync_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/salesforce/sync")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_no_integration(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post("/api/v1/salesforce/sync", headers=auth_headers)
        assert response.status_code == 404


class TestFieldMappings:
    """Tests for /api/v1/salesforce/field-mappings."""

    @pytest.mark.asyncio
    async def test_list_mappings_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/salesforce/field-mappings")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_mappings_no_integration(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/salesforce/field-mappings", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_mappings_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sf_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.get("/api/v1/salesforce/field-mappings", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_mapping_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/salesforce/field-mappings",
            json={
                "sniper_field": "title",
                "salesforce_field": "Name",
                "direction": "push",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_mapping_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sf_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.post(
            "/api/v1/salesforce/field-mappings",
            headers=auth_headers,
            json={
                "sniper_field": "title",
                "salesforce_field": "Name",
                "direction": "push",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sniper_field"] == "title"
        assert data["salesforce_field"] == "Name"

    @pytest.mark.asyncio
    async def test_delete_mapping_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/salesforce/field-mappings/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_mapping_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sf_integration: IntegrationConfig,
        test_user: User,
        db_session: AsyncSession,
    ):
        mapping = SalesforceFieldMapping(
            integration_id=sf_integration.id,
            sniper_field="title",
            salesforce_field="Name",
            direction="push",
        )
        db_session.add(mapping)
        await db_session.commit()
        await db_session.refresh(mapping)

        response = await client.delete(
            f"/api/v1/salesforce/field-mappings/{mapping.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_mapping_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sf_integration: IntegrationConfig,
        test_user: User,
    ):
        response = await client.delete(
            "/api/v1/salesforce/field-mappings/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestSalesforceWebhookInbound:
    """Tests for POST /api/v1/salesforce/webhooks/inbound."""

    @pytest.mark.asyncio
    async def test_webhook_inbound_no_auth_required(self, client: AsyncClient):
        """Salesforce inbound webhook is unauthenticated."""
        response = await client.post(
            "/api/v1/salesforce/webhooks/inbound",
            json={"event": "opportunity.updated", "id": "006xxx"},
        )
        assert response.status_code == 200
        assert response.json()["received"] is True

    @pytest.mark.asyncio
    async def test_webhook_inbound_empty_body(self, client: AsyncClient):
        """Should handle empty/malformed body gracefully."""
        response = await client.post(
            "/api/v1/salesforce/webhooks/inbound",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        # Route catches JSON parse errors
        assert response.status_code in (200, 422)
