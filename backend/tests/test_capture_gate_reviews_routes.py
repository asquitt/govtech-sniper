"""
Integration tests for capture/gate_reviews.py:
  - POST /capture/gate-reviews
  - GET  /capture/gate-reviews?rfp_id=
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import BidDecision, CaptureStage, GateReview
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_review(db_session: AsyncSession, test_user: User, test_rfp: RFP) -> GateReview:
    review = GateReview(
        rfp_id=test_rfp.id,
        reviewer_id=test_user.id,
        stage=CaptureStage.QUALIFIED,
        decision=BidDecision.BID,
        notes="Approved at gate",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


# ---------------------------------------------------------------------------
# Create gate review
# ---------------------------------------------------------------------------


class TestCreateGateReview:
    """Tests for POST /capture/gate-reviews."""

    @pytest.mark.asyncio
    async def test_create_review_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{PREFIX}/gate-reviews", json={"rfp_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_review_success(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(
            f"{PREFIX}/gate-reviews",
            headers=auth_headers,
            json={
                "rfp_id": test_rfp.id,
                "stage": "qualified",
                "decision": "bid",
                "notes": "Looks good",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == test_rfp.id
        assert data["stage"] == "qualified"
        assert data["decision"] == "bid"
        assert data["notes"] == "Looks good"

    @pytest.mark.asyncio
    async def test_create_review_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{PREFIX}/gate-reviews",
            headers=auth_headers,
            json={"rfp_id": 99999},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_review_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
    ):
        """Second user cannot create a gate review for first user's RFP."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.post(
            f"{PREFIX}/gate-reviews",
            headers=other_headers,
            json={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_review_defaults(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        """Defaults for stage and decision are applied."""
        response = await client.post(
            f"{PREFIX}/gate-reviews",
            headers=auth_headers,
            json={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "qualified"
        assert data["decision"] == "pending"


# ---------------------------------------------------------------------------
# List gate reviews
# ---------------------------------------------------------------------------


class TestListGateReviews:
    """Tests for GET /capture/gate-reviews?rfp_id=."""

    @pytest.mark.asyncio
    async def test_list_reviews_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{PREFIX}/gate-reviews", params={"rfp_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_reviews_empty(self, client: AsyncClient, auth_headers: dict, test_rfp: RFP):
        response = await client.get(
            f"{PREFIX}/gate-reviews",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_reviews_returns_entries(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_review: GateReview,
    ):
        response = await client.get(
            f"{PREFIX}/gate-reviews",
            headers=auth_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_review.id

    @pytest.mark.asyncio
    async def test_list_reviews_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            f"{PREFIX}/gate-reviews",
            headers=auth_headers,
            params={"rfp_id": 99999},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_reviews_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_rfp: RFP,
        test_review: GateReview,
    ):
        """Second user cannot list first user's gate reviews."""
        _, other_headers = await _create_second_user(db_session)
        response = await client.get(
            f"{PREFIX}/gate-reviews",
            headers=other_headers,
            params={"rfp_id": test_rfp.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_reviews_missing_rfp_id(self, client: AsyncClient, auth_headers: dict):
        """Missing required rfp_id query param returns 422."""
        response = await client.get(f"{PREFIX}/gate-reviews", headers=auth_headers)
        assert response.status_code == 422
