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
