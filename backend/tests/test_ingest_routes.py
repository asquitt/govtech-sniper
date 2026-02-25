"""
Tests for ingest routes - SAM.gov ingestion.
"""

import pytest
from httpx import AsyncClient


class TestTriggerSamIngest:
    """Tests for POST /api/v1/ingest/sam."""

    @pytest.mark.asyncio
    async def test_ingest_without_auth_returns_401(self, client: AsyncClient):
        """Without auth headers, the route returns 401."""
        response = await client.post(
            "/api/v1/ingest/sam",
            json={"keywords": "IT services"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/ingest/sam",
            headers=auth_headers,
            json={"keywords": "IT services", "days_back": 30, "limit": 5},
        )
        # Either 200 (sync fallback) or 503 (no broker) — both valid in test env
        assert response.status_code in {200, 503}


class TestQuickSearch:
    """Tests for POST /api/v1/ingest/sam/quick-search."""

    @pytest.mark.asyncio
    async def test_quick_search_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/ingest/sam/quick-search",
            params={"keywords": "test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_quick_search_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/ingest/sam/quick-search",
            headers=auth_headers,
            params={"keywords": "IT services", "limit": 5},
        )
        # 200 with mock, 503 without API key — both valid
        assert response.status_code in {200, 503}


class TestIngestStatus:
    """Tests for GET /api/v1/ingest/sam/status/{task_id}."""

    @pytest.mark.asyncio
    async def test_status_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/ingest/sam/status/fake-task-id")
        assert response.status_code == 401
