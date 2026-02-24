"""
Integration tests for analytics_reporting.py routes:
  - GET  /api/v1/analytics/win-rate
  - GET  /api/v1/analytics/pipeline-by-stage
  - GET  /api/v1/analytics/conversion-rates
  - GET  /api/v1/analytics/proposal-turnaround
  - GET  /api/v1/analytics/naics-performance
  - POST /api/v1/analytics/export
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CapturePlan, CaptureStage
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    user = User(
        email="reporting-second@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Second User",
        company_name="Other Co",
        tier="free",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_headers(second_user: User) -> dict:
    tokens = create_token_pair(second_user.id, second_user.email, second_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def capture_plan_won(db_session: AsyncSession, test_user: User, test_rfp: RFP) -> CapturePlan:
    plan = CapturePlan(
        rfp_id=test_rfp.id,
        owner_id=test_user.id,
        stage=CaptureStage.WON,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/win-rate
# ---------------------------------------------------------------------------


class TestWinRate:
    """GET /api/v1/analytics/win-rate"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/analytics/win-rate")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_win_rate_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/analytics/win-rate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "win_rate" in data
        assert "total_won" in data
        assert "total_lost" in data
        assert "trend" in data

    @pytest.mark.asyncio
    async def test_empty_win_rate(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/analytics/win-rate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["win_rate"] == 0
        assert data["total_won"] == 0

    @pytest.mark.asyncio
    async def test_with_won_capture(
        self, client: AsyncClient, auth_headers: dict, capture_plan_won: CapturePlan
    ):
        response = await client.get("/api/v1/analytics/win-rate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_won"] >= 1

    @pytest.mark.asyncio
    async def test_idor_isolation(
        self,
        client: AsyncClient,
        second_headers: dict,
        capture_plan_won: CapturePlan,
    ):
        response = await client.get("/api/v1/analytics/win-rate", headers=second_headers)
        assert response.status_code == 200
        assert response.json()["total_won"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/pipeline-by-stage
# ---------------------------------------------------------------------------


class TestPipelineByStage:
    """GET /api/v1/analytics/pipeline-by-stage"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/analytics/pipeline-by-stage")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_pipeline_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/analytics/pipeline-by-stage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert "total_pipeline_value" in data


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/conversion-rates
# ---------------------------------------------------------------------------


class TestConversionRates:
    """GET /api/v1/analytics/conversion-rates"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/analytics/conversion-rates")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_conversion_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/analytics/conversion-rates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "conversions" in data
        assert "overall_rate" in data
        assert isinstance(data["conversions"], list)


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/proposal-turnaround
# ---------------------------------------------------------------------------


class TestProposalTurnaround:
    """GET /api/v1/analytics/proposal-turnaround"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/analytics/proposal-turnaround")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_turnaround_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/analytics/proposal-turnaround", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "overall_avg_days" in data
        assert "trend" in data


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/naics-performance
# ---------------------------------------------------------------------------


class TestNaicsPerformance:
    """GET /api/v1/analytics/naics-performance"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/analytics/naics-performance")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_naics_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/analytics/naics-performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert isinstance(data["entries"], list)


# ---------------------------------------------------------------------------
# POST /api/v1/analytics/export
# ---------------------------------------------------------------------------


class TestAnalyticsExport:
    """POST /api/v1/analytics/export"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/analytics/export",
            json={"report_type": "win-rate"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_win_rate_csv(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/analytics/export",
            headers=auth_headers,
            json={"report_type": "win-rate"},
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_export_pipeline_csv(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/analytics/export",
            headers=auth_headers,
            json={"report_type": "pipeline"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_conversion_csv(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/analytics/export",
            headers=auth_headers,
            json={"report_type": "conversion"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_turnaround_csv(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/analytics/export",
            headers=auth_headers,
            json={"report_type": "turnaround"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_naics_csv(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/analytics/export",
            headers=auth_headers,
            json={"report_type": "naics"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_unknown_type_400(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/analytics/export",
            headers=auth_headers,
            json={"report_type": "nonexistent"},
        )
        assert response.status_code == 400
