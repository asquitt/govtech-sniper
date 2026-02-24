"""
Tests for health routes - Basic health, readiness, liveness.
"""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Tests for GET /api/v1/health."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data
        assert "timestamp" in data


class TestReadinessCheck:
    """Tests for GET /api/v1/health/ready."""

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert data["checks"]["database"] is True
        assert "timestamp" in data


class TestLivenessCheck:
    """Tests for GET /api/v1/health/live."""

    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
