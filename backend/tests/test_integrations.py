"""
RFP Sniper - Integrations Tests
===============================
Tests for integration configuration endpoints.
"""

import pytest
from httpx import AsyncClient


class TestIntegrations:
    @pytest.mark.asyncio
    async def test_integrations_crud(self, client: AsyncClient, auth_headers: dict):
        # Create
        payload = {
            "provider": "okta",
            "name": "Okta SSO",
            "is_enabled": True,
            "config": {"domain": "example.okta.com"},
        }
        response = await client.post(
            "/api/v1/integrations",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "okta"
        integration_id = data["id"]

        # List
        response = await client.get("/api/v1/integrations", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["id"] == integration_id

        # Update
        response = await client.patch(
            f"/api/v1/integrations/{integration_id}",
            headers=auth_headers,
            json={"is_enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["is_enabled"] is False

        # Delete
        response = await client.delete(
            f"/api/v1/integrations/{integration_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_integration_providers_and_testing(self, client: AsyncClient, auth_headers: dict):
        # Providers
        response = await client.get("/api/v1/integrations/providers", headers=auth_headers)
        assert response.status_code == 200
        providers = response.json()
        assert any(item["provider"] == "okta" for item in providers)
        assert any(item["provider"] == "salesforce" for item in providers)

        # Create integration with missing config
        response = await client.post(
            "/api/v1/integrations",
            headers=auth_headers,
            json={"provider": "okta", "name": "Okta SSO"},
        )
        assert response.status_code == 200
        integration_id = response.json()["id"]

        response = await client.post(
            f"/api/v1/integrations/{integration_id}/test",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        test_result = response.json()
        assert test_result["status"] == "error"
        assert "client_id" in test_result["missing_fields"]

        # Update with required fields and retest
        response = await client.patch(
            f"/api/v1/integrations/{integration_id}",
            headers=auth_headers,
            json={
                "config": {
                    "domain": "example.okta.com",
                    "client_id": "client",
                    "client_secret": "secret",
                    "issuer": "https://example.okta.com/oauth2/default",
                    "redirect_uri": "https://app.example.com/sso/callback",
                }
            },
        )
        assert response.status_code == 200

        response = await client.post(
            f"/api/v1/integrations/{integration_id}/test",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        test_result = response.json()
        assert test_result["status"] == "ok"

        # SSO authorize + callback
        response = await client.post(
            f"/api/v1/integrations/{integration_id}/sso/authorize",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        authorize = response.json()
        assert authorize["provider"] == "okta"
        assert "authorize" in authorize["authorization_url"]

        response = await client.post(
            f"/api/v1/integrations/{integration_id}/sso/callback",
            headers=auth_headers,
            json={"code": "sample-code"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_integration_sync_and_webhook(self, client: AsyncClient, auth_headers: dict):
        # Create SharePoint integration
        response = await client.post(
            "/api/v1/integrations",
            headers=auth_headers,
            json={
                "provider": "sharepoint",
                "name": "SharePoint",
                "config": {
                    "site_url": "https://example.sharepoint.com/sites/demo",
                    "tenant_id": "tenant",
                    "client_id": "client",
                    "client_secret": "secret",
                },
            },
        )
        assert response.status_code == 200
        integration_id = response.json()["id"]

        response = await client.post(
            f"/api/v1/integrations/{integration_id}/sync",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        sync_result = response.json()
        assert sync_result["status"] == "success"
        assert sync_result["items_synced"] > 0

        response = await client.get(
            f"/api/v1/integrations/{integration_id}/syncs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        syncs = response.json()
        assert len(syncs) >= 1

        response = await client.post(
            f"/api/v1/integrations/{integration_id}/webhook",
            headers=auth_headers,
            json={"event_type": "file.created", "document_id": "doc-1"},
        )
        assert response.status_code == 200
        webhook_event = response.json()
        assert webhook_event["event_type"] == "file.created"

        response = await client.get(
            f"/api/v1/integrations/{integration_id}/webhooks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
