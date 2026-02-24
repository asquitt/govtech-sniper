"""
Integration tests for intelligence.py:
  - GET  /intelligence/win-loss
  - POST /intelligence/debriefs
  - GET  /intelligence/budget
  - GET  /intelligence/pipeline-forecast
  - GET  /intelligence/kpis
  - GET  /intelligence/resource-allocation
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.award import AwardRecord
from app.models.capture import CapturePlan, CaptureStage, DebriefSource, WinLossDebrief
from app.models.contract import ContractAward, ContractStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.rfp import RFP
from app.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def rfp_won(db_session: AsyncSession, test_user: User) -> RFP:
    """RFP for a won capture plan."""
    rfp = RFP(
        user_id=test_user.id,
        title="Won Opportunity",
        solicitation_number="INTEL-WON-001",
        agency="Department of Defense",
        naics_code="541512",
        estimated_value=1_000_000,
        posted_date=datetime.utcnow() - timedelta(days=90),
        response_deadline=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)
    return rfp


@pytest_asyncio.fixture
async def rfp_lost(db_session: AsyncSession, test_user: User) -> RFP:
    """RFP for a lost capture plan."""
    rfp = RFP(
        user_id=test_user.id,
        title="Lost Opportunity",
        solicitation_number="INTEL-LOST-001",
        agency="Department of Defense",
        naics_code="541512",
        estimated_value=500_000,
        posted_date=datetime.utcnow() - timedelta(days=60),
        response_deadline=datetime.utcnow() - timedelta(days=10),
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)
    return rfp


@pytest_asyncio.fixture
async def rfp_active(db_session: AsyncSession, test_user: User) -> RFP:
    """RFP for an active capture plan (not won/lost)."""
    rfp = RFP(
        user_id=test_user.id,
        title="Active Pursuit",
        solicitation_number="INTEL-ACTIVE-001",
        agency="GSA",
        naics_code="541511",
        estimated_value=2_000_000,
        posted_date=datetime.utcnow() - timedelta(days=30),
        response_deadline=datetime.utcnow() + timedelta(days=15),
    )
    db_session.add(rfp)
    await db_session.commit()
    await db_session.refresh(rfp)
    return rfp


@pytest_asyncio.fixture
async def capture_won(db_session: AsyncSession, test_user: User, rfp_won: RFP) -> CapturePlan:
    """Won capture plan."""
    cp = CapturePlan(
        rfp_id=rfp_won.id,
        owner_id=test_user.id,
        stage=CaptureStage.WON,
        win_probability=90,
    )
    db_session.add(cp)
    await db_session.commit()
    await db_session.refresh(cp)
    return cp


@pytest_asyncio.fixture
async def capture_lost(db_session: AsyncSession, test_user: User, rfp_lost: RFP) -> CapturePlan:
    """Lost capture plan."""
    cp = CapturePlan(
        rfp_id=rfp_lost.id,
        owner_id=test_user.id,
        stage=CaptureStage.LOST,
        win_probability=30,
    )
    db_session.add(cp)
    await db_session.commit()
    await db_session.refresh(cp)
    return cp


@pytest_asyncio.fixture
async def capture_active(db_session: AsyncSession, test_user: User, rfp_active: RFP) -> CapturePlan:
    """Active capture plan (pursuit stage)."""
    cp = CapturePlan(
        rfp_id=rfp_active.id,
        owner_id=test_user.id,
        stage=CaptureStage.PURSUIT,
        win_probability=60,
    )
    db_session.add(cp)
    await db_session.commit()
    await db_session.refresh(cp)
    return cp


@pytest_asyncio.fixture
async def debrief_won(
    db_session: AsyncSession, test_user: User, capture_won: CapturePlan
) -> WinLossDebrief:
    """Debrief for a won capture plan."""
    d = WinLossDebrief(
        capture_plan_id=capture_won.id,
        user_id=test_user.id,
        outcome=CaptureStage.WON,
        source=DebriefSource.INTERNAL_REVIEW,
        win_themes=["technical_excellence", "past_performance"],
        loss_factors=[],
        agency_feedback="Strong technical approach",
        winning_vendor="Test Company",
        winning_price=950_000,
        our_price=950_000,
        num_offerors=3,
        technical_score=92.5,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest_asyncio.fixture
async def award_record(db_session: AsyncSession, test_user: User) -> AwardRecord:
    """Award record for budget intelligence."""
    ar = AwardRecord(
        user_id=test_user.id,
        agency="Department of Defense",
        awardee_name="Acme Corp",
        award_amount=750_000,
        award_date=datetime.utcnow() - timedelta(days=30),
        naics_code="541512",
    )
    db_session.add(ar)
    await db_session.commit()
    await db_session.refresh(ar)
    return ar


@pytest_asyncio.fixture
async def active_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    """Active contract award."""
    ca = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0001",
        title="Cybersecurity Support",
        agency="Department of Defense",
        value=1_500_000.0,
        status=ContractStatus.ACTIVE,
    )
    db_session.add(ca)
    await db_session.commit()
    await db_session.refresh(ca)
    return ca


@pytest_asyncio.fixture
async def draft_proposal(db_session: AsyncSession, test_user: User, rfp_active: RFP) -> Proposal:
    """Draft proposal for resource allocation."""
    p = Proposal(
        user_id=test_user.id,
        rfp_id=rfp_active.id,
        title="Active Draft Proposal",
        status=ProposalStatus.DRAFT,
        total_sections=5,
        completed_sections=0,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Win/Loss Analysis tests
# ---------------------------------------------------------------------------


class TestWinLossAnalysis:
    """Tests for GET /api/v1/intelligence/win-loss."""

    @pytest.mark.asyncio
    async def test_win_loss_requires_auth(self, client: AsyncClient):
        """Win-loss endpoint returns 401 without auth."""
        response = await client.get("/api/v1/intelligence/win-loss")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_win_loss_empty(self, client: AsyncClient, auth_headers: dict):
        """Win-loss with no data returns sensible empty defaults."""
        response = await client.get("/api/v1/intelligence/win-loss", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["by_agency"] == []
        assert data["by_size"] == []
        assert data["debriefs"] == []
        assert data["top_win_themes"] == []
        assert data["top_loss_factors"] == []
        assert data["recommendations"] == []

    @pytest.mark.asyncio
    async def test_win_loss_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        capture_won: CapturePlan,
        capture_lost: CapturePlan,
        debrief_won: WinLossDebrief,
    ):
        """Win-loss with populated data returns agency stats and debriefs."""
        response = await client.get("/api/v1/intelligence/win-loss", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Should have agency data (both captures are DoD)
        assert len(data["by_agency"]) >= 1
        dod = data["by_agency"][0]
        assert dod["agency"] == "Department of Defense"
        assert dod["won"] == 1
        assert dod["lost"] == 1
        assert dod["win_rate"] == 50.0

        # Should have size bucket data
        assert len(data["by_size"]) >= 1

        # Should have the debrief
        assert len(data["debriefs"]) == 1
        assert data["debriefs"][0]["outcome"] == "won"

        # Should have win themes from the debrief
        assert len(data["top_win_themes"]) >= 1


# ---------------------------------------------------------------------------
# Create Debrief tests
# ---------------------------------------------------------------------------


class TestCreateDebrief:
    """Tests for POST /api/v1/intelligence/debriefs."""

    @pytest.mark.asyncio
    async def test_create_debrief_requires_auth(self, client: AsyncClient):
        """Debrief creation returns 401 without auth."""
        response = await client.post(
            "/api/v1/intelligence/debriefs",
            params={"capture_plan_id": 1, "outcome": "won"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_debrief_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        capture_lost: CapturePlan,
    ):
        """Authenticated user can create a debrief."""
        response = await client.post(
            "/api/v1/intelligence/debriefs",
            headers=auth_headers,
            params={
                "capture_plan_id": capture_lost.id,
                "outcome": "lost",
                "source": "internal_review",
                "winning_vendor": "Competitor Inc",
                "winning_price": 400_000,
                "our_price": 450_000,
                "num_offerors": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_debrief_missing_required(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Debrief creation without capture_plan_id returns 422."""
        response = await client.post(
            "/api/v1/intelligence/debriefs",
            headers=auth_headers,
            params={"outcome": "won"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Budget Intelligence tests
# ---------------------------------------------------------------------------


class TestBudgetIntelligence:
    """Tests for GET /api/v1/intelligence/budget."""

    @pytest.mark.asyncio
    async def test_budget_requires_auth(self, client: AsyncClient):
        """Budget endpoint returns 401 without auth."""
        response = await client.get("/api/v1/intelligence/budget")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_budget_empty(self, client: AsyncClient, auth_headers: dict):
        """Budget with no data returns sensible empty defaults."""
        response = await client.get("/api/v1/intelligence/budget", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["top_agencies"] == []
        assert data["top_naics"] == []
        assert data["budget_season"] == []
        assert data["top_competitors"] == []

    @pytest.mark.asyncio
    async def test_budget_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        award_record: AwardRecord,
        test_rfp: RFP,
    ):
        """Budget with populated data returns agency and competitor info."""
        response = await client.get("/api/v1/intelligence/budget", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Award record should show up in agencies and competitors
        assert len(data["top_agencies"]) >= 1
        assert data["top_agencies"][0]["agency"] == "Department of Defense"

        assert len(data["top_competitors"]) >= 1
        assert data["top_competitors"][0]["vendor"] == "Acme Corp"

        # NAICS should have data
        assert len(data["top_naics"]) >= 1

        # Budget season from test_rfp posted_date
        assert len(data["budget_season"]) >= 1


# ---------------------------------------------------------------------------
# Pipeline Forecast tests
# ---------------------------------------------------------------------------


class TestPipelineForecast:
    """Tests for GET /api/v1/intelligence/pipeline-forecast."""

    @pytest.mark.asyncio
    async def test_forecast_requires_auth(self, client: AsyncClient):
        """Pipeline forecast returns 401 without auth."""
        response = await client.get("/api/v1/intelligence/pipeline-forecast")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_forecast_empty(self, client: AsyncClient, auth_headers: dict):
        """Forecast with no data returns empty forecast."""
        response = await client.get("/api/v1/intelligence/pipeline-forecast", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "quarterly"
        assert data["forecast"] == []
        assert data["total_weighted"] == 0.0
        assert data["total_unweighted"] == 0.0

    @pytest.mark.asyncio
    async def test_forecast_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        capture_active: CapturePlan,
    ):
        """Forecast with active captures returns weighted pipeline values."""
        response = await client.get("/api/v1/intelligence/pipeline-forecast", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "quarterly"
        assert len(data["forecast"]) >= 1
        assert data["total_weighted"] > 0
        assert data["total_unweighted"] > 0

        # Check forecast entry shape
        entry = data["forecast"][0]
        assert "period" in entry
        assert "weighted_value" in entry
        assert "optimistic_value" in entry
        assert "pessimistic_value" in entry
        assert "opportunity_count" in entry
        assert "unweighted_value" in entry

    @pytest.mark.asyncio
    async def test_forecast_monthly_granularity(
        self,
        client: AsyncClient,
        auth_headers: dict,
        capture_active: CapturePlan,
    ):
        """Forecast with monthly granularity uses month-based periods."""
        response = await client.get(
            "/api/v1/intelligence/pipeline-forecast?granularity=monthly",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "monthly"
        if data["forecast"]:
            # Monthly period format: YYYY-MM
            period = data["forecast"][0]["period"]
            assert len(period) == 7
            assert "-" in period

    @pytest.mark.asyncio
    async def test_forecast_invalid_granularity(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Forecast with invalid granularity returns 422."""
        response = await client.get(
            "/api/v1/intelligence/pipeline-forecast?granularity=yearly",
            headers=auth_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# KPIs tests
# ---------------------------------------------------------------------------


class TestKPIs:
    """Tests for GET /api/v1/intelligence/kpis."""

    @pytest.mark.asyncio
    async def test_kpis_requires_auth(self, client: AsyncClient):
        """KPIs endpoint returns 401 without auth."""
        response = await client.get("/api/v1/intelligence/kpis")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_kpis_empty(self, client: AsyncClient, auth_headers: dict):
        """KPIs with no data returns zero defaults."""
        response = await client.get("/api/v1/intelligence/kpis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["win_rate"] == 0.0
        assert data["total_won"] == 0
        assert data["total_lost"] == 0
        assert data["active_pipeline"]["count"] == 0
        assert data["active_pipeline"]["unweighted_value"] == 0.0
        assert data["active_pipeline"]["weighted_value"] == 0.0
        assert data["won_revenue"]["count"] == 0
        assert data["won_revenue"]["value"] == 0.0
        assert data["active_proposals"] == 0
        assert data["avg_turnaround_days"] == 0.0
        assert data["upcoming_deadlines"] == 0

    @pytest.mark.asyncio
    async def test_kpis_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        capture_won: CapturePlan,
        capture_lost: CapturePlan,
        capture_active: CapturePlan,
        active_contract: ContractAward,
        draft_proposal: Proposal,
    ):
        """KPIs with populated data returns computed metrics."""
        response = await client.get("/api/v1/intelligence/kpis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Win rate: 1 won, 1 lost = 50%
        assert data["win_rate"] == 50.0
        assert data["total_won"] == 1
        assert data["total_lost"] == 1

        # Active pipeline: 1 active capture
        assert data["active_pipeline"]["count"] == 1
        assert data["active_pipeline"]["unweighted_value"] == 2_000_000.0

        # Won revenue: 1 active contract
        assert data["won_revenue"]["count"] == 1
        assert data["won_revenue"]["value"] == 1_500_000.0

        # 1 draft proposal
        assert data["active_proposals"] == 1


# ---------------------------------------------------------------------------
# Resource Allocation tests
# ---------------------------------------------------------------------------


class TestResourceAllocation:
    """Tests for GET /api/v1/intelligence/resource-allocation."""

    @pytest.mark.asyncio
    async def test_resource_allocation_requires_auth(self, client: AsyncClient):
        """Resource allocation returns 401 without auth."""
        response = await client.get("/api/v1/intelligence/resource-allocation")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_resource_allocation_empty(self, client: AsyncClient, auth_headers: dict):
        """Resource allocation with no data returns empty workloads."""
        response = await client.get(
            "/api/v1/intelligence/resource-allocation", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["proposal_workload"] == []
        assert data["capture_workload"] == []

    @pytest.mark.asyncio
    async def test_resource_allocation_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        capture_active: CapturePlan,
        draft_proposal: Proposal,
    ):
        """Resource allocation with data returns workload breakdown."""
        response = await client.get(
            "/api/v1/intelligence/resource-allocation", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should have proposal workload
        assert len(data["proposal_workload"]) >= 1
        statuses = [w["status"] for w in data["proposal_workload"]]
        assert "draft" in statuses

        # Should have capture workload (active only, not won/lost)
        assert len(data["capture_workload"]) >= 1
        stages = [w["stage"] for w in data["capture_workload"]]
        assert "pursuit" in stages
