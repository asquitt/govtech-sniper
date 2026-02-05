"""
RFP Sniper - Secrets Vault Tests
================================
Tests for secrets storage endpoints.
"""

import pytest
from httpx import AsyncClient


class TestSecrets:
    @pytest.mark.asyncio
    async def test_secret_crud(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "okta_client_secret", "value": "super-secret"},
        )
        assert response.status_code == 200
        created = response.json()
        assert created["key"] == "okta_client_secret"
        assert created["value"] != "super-secret"

        response = await client.get("/api/v1/secrets", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        assert len(items) >= 1
