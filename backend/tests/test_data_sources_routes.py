"""
Integration tests for data_sources.py — /api/v1/data-sources/
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestListDataSources:
    """Tests for GET /api/v1/data-sources."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/data-sources")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_providers(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/data-sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Each provider should have required fields
        if data:
            assert "provider_name" in data[0]
            assert "display_name" in data[0]
            assert "is_active" in data[0]


class TestSearchProvider:
    """Tests for POST /api/v1/data-sources/{provider_name}/search."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/data-sources/sam_gov/search",
            json={"keywords": "cybersecurity"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_provider_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/data-sources/nonexistent_provider/search",
            headers=auth_headers,
            json={"keywords": "test"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.routes.data_sources.get_provider")
    async def test_inactive_provider(
        self, mock_get: MagicMock, client: AsyncClient, auth_headers: dict
    ):
        """Searching an inactive provider returns 400."""
        mock_provider = MagicMock()
        mock_provider.is_active = False
        mock_get.return_value = mock_provider

        response = await client.post(
            "/api/v1/data-sources/inactive_prov/search",
            headers=auth_headers,
            json={"keywords": "test"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.routes.data_sources.get_provider")
    async def test_search_success(
        self, mock_get: MagicMock, client: AsyncClient, auth_headers: dict
    ):
        """Search with an active provider returns results."""
        mock_provider = MagicMock()
        mock_provider.is_active = True
        mock_provider.search = AsyncMock(return_value=[])
        mock_get.return_value = mock_provider

        response = await client.post(
            "/api/v1/data-sources/test_prov/search",
            headers=auth_headers,
            json={"keywords": "IT services"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "test_prov"
        assert data["count"] == 0


class TestIngestProvider:
    """Tests for POST /api/v1/data-sources/{provider_name}/ingest."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/data-sources/sam_gov/ingest",
            json={"keywords": "test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_provider_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/data-sources/nonexistent/ingest",
            headers=auth_headers,
            json={"keywords": "test"},
        )
        assert response.status_code == 404


class TestProviderHealth:
    """Tests for GET /api/v1/data-sources/{provider_name}/health."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/data-sources/sam_gov/health")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_health_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/data-sources/nonexistent/health", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.routes.data_sources.get_provider")
    async def test_health_check(self, mock_get: MagicMock, client: AsyncClient, auth_headers: dict):
        mock_provider = MagicMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        mock_get.return_value = mock_provider

        response = await client.get("/api/v1/data-sources/test_prov/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "test_prov"
        assert data["healthy"] is True
