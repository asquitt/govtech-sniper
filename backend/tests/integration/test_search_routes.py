"""
Search Routes Integration Tests
=================================
Tests for semantic search and saved searches CRUD/execution.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# =============================================================================
# POST /search/ — semantic search
# =============================================================================


class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_search_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/search/", json={"query": "cybersecurity"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_search_returns_results(self, client: AsyncClient, auth_headers: dict):
        with patch(
            "app.api.routes.search.search",
            new=AsyncMock(return_value=[]),
        ):
            resp = await client.post(
                "/api/v1/search/",
                json={"query": "cybersecurity services"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "cybersecurity services"
        assert "results" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_search_with_entity_types(self, client: AsyncClient, auth_headers: dict):
        with patch(
            "app.api.routes.search.search",
            new=AsyncMock(return_value=[]),
        ):
            resp = await client.post(
                "/api/v1/search/",
                json={"query": "cloud", "entity_types": ["rfp"]},
                headers=auth_headers,
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_empty_query_fails(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/search/",
            json={"query": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# =============================================================================
# Saved Searches CRUD
# =============================================================================


class TestSavedSearches:
    @pytest.mark.asyncio
    async def test_create_saved_search(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/saved-searches",
            json={
                "name": "DoD Cyber",
                "filters": {"keyword": "cybersecurity", "agencies": ["DoD"]},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "DoD Cyber"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_saved_searches(self, client: AsyncClient, auth_headers: dict):
        # Create one first
        await client.post(
            "/api/v1/saved-searches",
            json={"name": "Test Search", "filters": {}},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/saved-searches", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_update_saved_search(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/saved-searches",
            json={"name": "Original", "filters": {}},
            headers=auth_headers,
        )
        search_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/saved-searches/{search_id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_saved_search(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/saved-searches",
            json={"name": "To Delete", "filters": {}},
            headers=auth_headers,
        )
        search_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/saved-searches/{search_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_run_saved_search(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/saved-searches",
            json={"name": "Runnable", "filters": {"keyword": "test"}},
            headers=auth_headers,
        )
        search_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/saved-searches/{search_id}/run",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "match_count" in data
        assert "matches" in data

    @pytest.mark.asyncio
    async def test_delete_nonexistent_search_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete(
            "/api/v1/saved-searches/99999",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_saved_search_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/saved-searches")
        assert resp.status_code == 401
