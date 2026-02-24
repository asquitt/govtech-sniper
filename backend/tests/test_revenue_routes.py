"""
Integration tests for revenue.py — /api/v1/revenue/
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CapturePlan, CaptureStage
from app.models.rfp import RFP
from app.models.user import User


class TestPipelineSummary:
    """Tests for GET /api/v1/revenue/pipeline-summary."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/revenue/pipeline-summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_pipeline(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/revenue/pipeline-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_opportunities"] == 0
        assert data["total_unweighted"] == 0
        assert data["total_weighted"] == 0
        assert data["stages"] == []

    @pytest.mark.asyncio
    async def test_pipeline_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_rfp: RFP,
    ):
        """Pipeline summary includes capture plans with estimated values."""
        plan = CapturePlan(
            rfp_id=test_rfp.id,
            owner_id=test_user.id,
            stage=CaptureStage.PURSUIT,
            win_probability=70,
        )
        db_session.add(plan)
        await db_session.commit()

        response = await client.get("/api/v1/revenue/pipeline-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_opportunities"] >= 1
        assert data["total_unweighted"] > 0


class TestRevenueTimeline:
    """Tests for GET /api/v1/revenue/timeline."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/revenue/timeline")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_timeline_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/revenue/timeline", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "monthly"
        assert data["points"] == []

    @pytest.mark.asyncio
    async def test_timeline_quarterly(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/revenue/timeline?granularity=quarterly", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["granularity"] == "quarterly"

    @pytest.mark.asyncio
    async def test_timeline_invalid_granularity(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/revenue/timeline?granularity=yearly", headers=auth_headers
        )
        assert response.status_code == 422


class TestRevenueByAgency:
    """Tests for GET /api/v1/revenue/by-agency."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/revenue/by-agency")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_by_agency_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/revenue/by-agency", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["agencies"] == []
        assert data["total_agencies"] == 0

    @pytest.mark.asyncio
    async def test_by_agency_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_rfp: RFP,
    ):
        plan = CapturePlan(
            rfp_id=test_rfp.id,
            owner_id=test_user.id,
            stage=CaptureStage.PURSUIT,
            win_probability=60,
        )
        db_session.add(plan)
        await db_session.commit()

        response = await client.get("/api/v1/revenue/by-agency", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_agencies"] >= 1
        assert data["agencies"][0]["agency"] == "Department of Defense"

    @pytest.mark.asyncio
    async def test_by_agency_custom_limit(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/revenue/by-agency?limit=5", headers=auth_headers)
        assert response.status_code == 200
