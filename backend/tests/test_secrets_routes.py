"""
Integration tests for secrets.py — /api/v1/secrets/
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestListSecrets:
    """Tests for GET /api/v1/secrets."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/secrets")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/secrets", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateSecret:
    """Tests for POST /api/v1/secrets."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/secrets",
            json={"key": "API_KEY", "value": "secret123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_secret(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "SAM_GOV_API_KEY", "value": "abc123xyz"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "SAM_GOV_API_KEY"
        # Value should be redacted
        assert data["value"] == "********"

    @pytest.mark.asyncio
    async def test_create_updates_existing(self, client: AsyncClient, auth_headers: dict):
        """Creating with same key updates the existing secret."""
        await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "MY_KEY", "value": "v1"},
        )
        response = await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "MY_KEY", "value": "v2"},
        )
        assert response.status_code == 200
        # Should still only have one secret with that key
        list_resp = await client.get("/api/v1/secrets", headers=auth_headers)
        keys = [s["key"] for s in list_resp.json()]
        assert keys.count("MY_KEY") == 1

    @pytest.mark.asyncio
    async def test_create_validation(self, client: AsyncClient, auth_headers: dict):
        """Key must be at least 2 chars, value at least 1."""
        response = await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "A", "value": ""},
        )
        assert response.status_code == 422


class TestGetSecret:
    """Tests for GET /api/v1/secrets/{secret_key}."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/secrets/MY_KEY")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_secret_redacted(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "TEST_KEY", "value": "supersecret"},
        )
        response = await client.get("/api/v1/secrets/TEST_KEY", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["value"] == "********"

    @pytest.mark.asyncio
    async def test_get_secret_revealed(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "REVEAL_KEY", "value": "mysecretvalue"},
        )
        response = await client.get("/api/v1/secrets/REVEAL_KEY?reveal=true", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["value"] == "mysecretvalue"

    @pytest.mark.asyncio
    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/secrets/NOPE", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User B cannot access User A's secret."""
        await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "PRIVATE_KEY", "value": "hidden"},
        )

        user_b = User(
            email="other@example.com",
            hashed_password=hash_password("Pwd123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user_b)
        await db_session.commit()
        await db_session.refresh(user_b)
        tokens = create_token_pair(user_b.id, user_b.email, user_b.tier)
        headers_b = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/secrets/PRIVATE_KEY", headers=headers_b)
        assert response.status_code == 404


class TestDeleteSecret:
    """Tests for DELETE /api/v1/secrets/{secret_key}."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/secrets/MY_KEY")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_secret(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/secrets",
            headers=auth_headers,
            json={"key": "DELETE_ME", "value": "temp"},
        )
        response = await client.delete("/api/v1/secrets/DELETE_ME", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Secret deleted"

        # Verify gone
        get_resp = await client.get("/api/v1/secrets/DELETE_ME", headers=auth_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/secrets/NOPE", headers=auth_headers)
        assert response.status_code == 404
