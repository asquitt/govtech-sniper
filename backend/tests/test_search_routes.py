"""
Integration tests for search.py — POST /search/
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestSemanticSearch:
    """Tests for POST /api/v1/search/."""

    @pytest.mark.asyncio
    async def test_search_requires_auth(self, client: AsyncClient):
        """Search endpoint returns 401 without auth token."""
        response = await client.post(
            "/api/v1/search/",
            json={"query": "cybersecurity services"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_valid_query(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Search with a valid query returns structured results."""
        mock_search.return_value = [
            {
                "entity_type": "rfp",
                "entity_id": 1,
                "title": "Cybersecurity RFP",
                "snippet": "DoD cybersecurity services contract",
                "score": 0.92,
            }
        ]
        response = await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"query": "cybersecurity services"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "cybersecurity services"
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["entity_type"] == "rfp"

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_empty_results(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Search returning no results returns empty list."""
        mock_search.return_value = []
        response = await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"query": "nonexistent xyzzy topic"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_with_entity_type_filter(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Search accepts entity_types filter and passes it to the service."""
        mock_search.return_value = [
            {
                "entity_type": "proposal",
                "entity_id": 5,
                "title": "My Proposal",
                "snippet": "Proposal content",
                "score": 0.85,
            }
        ]
        response = await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"query": "proposal", "entity_types": ["proposal"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        # Verify the service was called with the correct entity_types
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["entity_types"] == ["proposal"]

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_with_limit(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Search accepts a custom limit parameter."""
        mock_search.return_value = []
        response = await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"query": "test", "limit": 5},
        )
        assert response.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_missing_query_field(self, client: AsyncClient, auth_headers: dict):
        """Search without the required 'query' field returns 422."""
        response = await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"entity_types": ["rfp"]},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_multiple_entity_types(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Search with multiple entity_types is passed through correctly."""
        mock_search.return_value = []
        response = await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={
                "query": "cloud services",
                "entity_types": ["rfp", "proposal", "document"],
            },
        )
        assert response.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert set(call_kwargs["entity_types"]) == {"rfp", "proposal", "document"}

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_user_scoped(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Search is scoped to the authenticated user's ID."""
        mock_search.return_value = []
        await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"query": "test query"},
        )
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["user_id"] == test_user.id

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_result_schema(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Search results include all expected fields."""
        mock_search.return_value = [
            {
                "entity_type": "document",
                "entity_id": 10,
                "title": "Capability Statement",
                "snippet": "Our core capabilities include...",
                "score": 0.77,
            }
        ]
        response = await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"query": "capability"},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert "entity_type" in result
        assert "entity_id" in result
        assert "title" in result
        assert "snippet" in result
        assert "score" in result

    @pytest.mark.asyncio
    @patch("app.api.routes.search.search", new_callable=AsyncMock)
    async def test_search_no_entity_types_passes_none(
        self,
        mock_search: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """When entity_types is omitted, None is passed to the service."""
        mock_search.return_value = []
        await client.post(
            "/api/v1/search/",
            headers=auth_headers,
            json={"query": "anything"},
        )
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["entity_types"] is None
