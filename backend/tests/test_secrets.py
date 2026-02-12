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

        response = await client.get(
            "/api/v1/secrets/okta_client_secret?reveal=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["value"] == "super-secret"

        response = await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "okta_client_secret", "value": "rotated-secret"},
        )
        assert response.status_code == 200
        assert response.json()["key"] == "okta_client_secret"

        reveal_rotated = await client.get(
            "/api/v1/secrets/okta_client_secret?reveal=true",
            headers=auth_headers,
        )
        assert reveal_rotated.status_code == 200
        assert reveal_rotated.json()["value"] == "rotated-secret"

        delete_response = await client.delete(
            "/api/v1/secrets/okta_client_secret",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200

        not_found = await client.get(
            "/api/v1/secrets/okta_client_secret",
            headers=auth_headers,
        )
        assert not_found.status_code == 404
