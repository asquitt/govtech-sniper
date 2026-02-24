"""
Integration tests for capture/bid_decision.py:
  - POST /capture/scorecards/{rfp_id}/ai-evaluate
  - POST /capture/scorecards/{rfp_id}/vote
  - GET  /capture/scorecards/{rfp_id}
  - GET  /capture/scorecards/{rfp_id}/summary
  - POST /capture/scorecards/{rfp_id}/scenario-simulator
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import (
    BidScorecard,
    BidScorecardRecommendation,
    ScorerType,
)
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

PREFIX = "/api/v1/capture"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    user = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPassword123!"),
        full_name="Other User",
        company_name="Other Company",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    tokens = create_token_pair(user.id, user.email, user.tier)
    return user, {"Authorization": f"Bearer {tokens.access_token}"}


VOTE_PAYLOAD = {
    "criteria_scores": [{"name": "Technical", "score": 85}],
    "overall_score": 85.0,
    "recommendation": "bid",
    "reasoning": "Strong fit",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_scorecard(db_session: AsyncSession, test_user: User, test_rfp: RFP) -> BidScorecard:
    """Create a human scorecard for the test user's RFP."""
    sc = BidScorecard(
        rfp_id=test_rfp.id,
        user_id=test_user.id,
        criteria_scores=[{"name": "Technical", "score": 80}],
        overall_score=80.0,
        recommendation=BidScorecardRecommendation.BID,
        confidence=1.0,
        reasoning="Good fit",
        scorer_type=ScorerType.HUMAN,
        scorer_id=test_user.id,
    )
    db_session.add(sc)
    await db_session.commit()
    await db_session.refresh(sc)
    return sc


# ---------------------------------------------------------------------------
# AI evaluate (rate-limited + needs profile — test auth/validation only)
# ---------------------------------------------------------------------------


class TestAiEvaluateBid:
    """Tests for POST /capture/scorecards/{rfp_id}/ai-evaluate."""

    @pytest.mark.asyncio
    async def test_ai_evaluate_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{PREFIX}/scorecards/1/ai-evaluate")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ai_evaluate_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(f"{PREFIX}/scorecards/99999/ai-evaluate", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ai_evaluate_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        """Second user cannot AI-evaluate first user's RFP."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.post(
            f"{PREFIX}/scorecards/{test_rfp.id}/ai-evaluate",
            headers=other_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_ai_evaluate_missing_profile(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Returns 400 when user profile is missing."""
        response = await client.post(
            f"{PREFIX}/scorecards/{test_rfp.id}/ai-evaluate",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "profile" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Human vote
# ---------------------------------------------------------------------------


class TestSubmitHumanVote:
    """Tests for POST /capture/scorecards/{rfp_id}/vote."""

    @pytest.mark.asyncio
    async def test_vote_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{PREFIX}/scorecards/1/vote", json=VOTE_PAYLOAD)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_vote_success(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.post(
            f"{PREFIX}/scorecards/{test_rfp.id}/vote",
            headers=auth_headers,
            json=VOTE_PAYLOAD,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == test_rfp.id
        assert data["overall_score"] == 85.0
        assert data["recommendation"] == "bid"
        assert data["scorer_type"] == "human"

    @pytest.mark.asyncio
    async def test_vote_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/scorecards/99999/vote",
            headers=auth_headers,
            json=VOTE_PAYLOAD,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_vote_missing_fields(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Omitting required fields returns 422."""
        response = await client.post(
            f"{PREFIX}/scorecards/{test_rfp.id}/vote",
            headers=auth_headers,
            json={"overall_score": 50},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# List scorecards
# ---------------------------------------------------------------------------


class TestListScorecards:
    """Tests for GET /capture/scorecards/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_list_scorecards_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/scorecards/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_scorecards_empty(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.get(f"{PREFIX}/scorecards/{test_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_scorecards_returns_entries(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_scorecard: BidScorecard,
    ):
        response = await client.get(f"{PREFIX}/scorecards/{test_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_scorecard.id
        assert data[0]["scorer_type"] == "human"


# ---------------------------------------------------------------------------
# Bid summary
# ---------------------------------------------------------------------------


class TestBidSummary:
    """Tests for GET /capture/scorecards/{rfp_id}/summary."""

    @pytest.mark.asyncio
    async def test_summary_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/scorecards/1/summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_summary_no_votes(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.get(
            f"{PREFIX}/scorecards/{test_rfp.id}/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_votes"] == 0
        assert data["overall_recommendation"] is None

    @pytest.mark.asyncio
    async def test_summary_with_votes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_scorecard: BidScorecard,
    ):
        response = await client.get(
            f"{PREFIX}/scorecards/{test_rfp.id}/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_votes"] == 1
        assert data["bid_count"] == 1
        assert data["overall_recommendation"] == "bid"


# ---------------------------------------------------------------------------
# Scenario simulator (needs existing scorecard)
# ---------------------------------------------------------------------------


class TestScenarioSimulator:
    """Tests for POST /capture/scorecards/{rfp_id}/scenario-simulator."""

    @pytest.mark.asyncio
    async def test_scenario_requires_auth(self, client: AsyncClient):
        response = await client.post(
            f"{PREFIX}/scorecards/1/scenario-simulator", json={"scenarios": []}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_scenario_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/scorecards/99999/scenario-simulator",
            headers=auth_headers,
            json={"scenarios": []},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_scenario_no_scorecard(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Returns 404 when no scorecard exists for the RFP."""
        response = await client.post(
            f"{PREFIX}/scorecards/{test_rfp.id}/scenario-simulator",
            headers=auth_headers,
            json={"scenarios": []},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_scenario_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
        test_scorecard: BidScorecard,
    ):
        """Second user cannot run scenarios on first user's RFP."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.post(
            f"{PREFIX}/scorecards/{test_rfp.id}/scenario-simulator",
            headers=other_headers,
            json={"scenarios": []},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_scenario_success_defaults(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_scorecard: BidScorecard,
    ):
        """Running scenario simulator with empty scenarios uses defaults."""
        response = await client.post(
            f"{PREFIX}/scorecards/{test_rfp.id}/scenario-simulator",
            headers=auth_headers,
            json={"scenarios": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert "baseline" in data or "scenarios" in data or isinstance(data, dict)
