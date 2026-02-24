"""
Integration tests for signals.py:
  - GET  /signals/feed
  - GET  /signals
  - POST /signals
  - PATCH /signals/{signal_id}/read
  - DELETE /signals/{signal_id}
  - GET  /signals/subscription
  - POST /signals/subscription
  - POST /signals/ingest/news
  - POST /signals/ingest/budget-analysis
  - POST /signals/rescore
  - GET  /signals/digest-preview
  - POST /signals/digest-send
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_signal import DigestFrequency, MarketSignal, SignalSubscription, SignalType
from app.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_signal(db_session: AsyncSession, test_user: User) -> MarketSignal:
    """Create a single MarketSignal for the test user."""
    signal = MarketSignal(
        user_id=test_user.id,
        title="DoD Acquisition Policy Update",
        signal_type=SignalType.NEWS,
        agency="Department of Defense",
        content="Policy changes for acquisition modernization.",
        source_url="https://federalnewsnetwork.com/article-1",
        relevance_score=72.5,
    )
    db_session.add(signal)
    await db_session.commit()
    await db_session.refresh(signal)
    return signal


@pytest_asyncio.fixture
async def test_subscription(db_session: AsyncSession, test_user: User) -> SignalSubscription:
    """Create a signal subscription for the test user."""
    sub = SignalSubscription(
        user_id=test_user.id,
        agencies=["Department of Defense"],
        naics_codes=["541512"],
        keywords=["cybersecurity", "cloud"],
        email_digest_enabled=True,
        digest_frequency=DigestFrequency.DAILY,
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# Signal listing tests
# ---------------------------------------------------------------------------


class TestSignalListing:
    """Tests for GET /signals and GET /signals/feed."""

    @pytest.mark.asyncio
    async def test_list_signals_requires_auth(self, client: AsyncClient):
        """Signal listing returns 401 without auth."""
        response = await client.get("/api/v1/signals")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_signals_empty(self, client: AsyncClient, auth_headers: dict):
        """No signals returns empty list."""
        response = await client.get("/api/v1/signals", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_signals_with_data(
        self, client: AsyncClient, auth_headers: dict, test_signal: MarketSignal
    ):
        """Returns signals for the authenticated user."""
        response = await client.get("/api/v1/signals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == test_signal.title
        assert data[0]["signal_type"] == "news"

    @pytest.mark.asyncio
    async def test_signal_feed_returns_paginated(
        self, client: AsyncClient, auth_headers: dict, test_signal: MarketSignal
    ):
        """Feed endpoint returns paginated results with total count."""
        response = await client.get("/api/v1/signals/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_signal_feed_filter_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        """Feed accepts signal_type filter."""
        response = await client.get("/api/v1/signals/feed?signal_type=news", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for sig in data["signals"]:
            assert sig["signal_type"] == "news"

    @pytest.mark.asyncio
    async def test_signal_feed_filter_by_agency(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        """Feed accepts agency filter."""
        response = await client.get(
            "/api/v1/signals/feed?agency=Department+of+Defense", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        for sig in data["signals"]:
            assert sig["agency"] == "Department of Defense"

    @pytest.mark.asyncio
    async def test_signal_feed_unread_only(
        self, client: AsyncClient, auth_headers: dict, test_signal: MarketSignal
    ):
        """Feed returns only unread signals when unread_only=true."""
        response = await client.get("/api/v1/signals/feed?unread_only=true", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for sig in data["signals"]:
            assert sig["is_read"] is False


# ---------------------------------------------------------------------------
# Signal creation tests
# ---------------------------------------------------------------------------


class TestSignalCreate:
    """Tests for POST /signals."""

    @pytest.mark.asyncio
    async def test_create_signal_success(self, client: AsyncClient, auth_headers: dict):
        """Admin can create a signal manually."""
        response = await client.post(
            "/api/v1/signals",
            headers=auth_headers,
            json={
                "title": "VA Cloud Recompete Alert",
                "signal_type": "recompete",
                "agency": "Department of Veterans Affairs",
                "content": "Recompete expected Q3.",
                "source_url": "https://sam.gov/opp/123",
                "relevance_score": 0.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "VA Cloud Recompete Alert"
        assert data["signal_type"] == "recompete"
        assert data["is_read"] is False

    @pytest.mark.asyncio
    async def test_create_signal_requires_auth(self, client: AsyncClient):
        """Signal creation returns 401 without auth."""
        response = await client.post(
            "/api/v1/signals",
            json={"title": "Test", "signal_type": "news", "relevance_score": 0.0},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_signal_missing_title(self, client: AsyncClient, auth_headers: dict):
        """Signal creation without title returns 422."""
        response = await client.post(
            "/api/v1/signals",
            headers=auth_headers,
            json={"signal_type": "news", "relevance_score": 0.0},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Signal acknowledgment tests
# ---------------------------------------------------------------------------


class TestSignalAcknowledgment:
    """Tests for PATCH /signals/{id}/read and DELETE /signals/{id}."""

    @pytest.mark.asyncio
    async def test_mark_signal_read(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        """PATCH marks a signal as read."""
        response = await client.patch(
            f"/api/v1/signals/{test_signal.id}/read", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_mark_signal_read_not_found(self, client: AsyncClient, auth_headers: dict):
        """PATCH on non-existent signal returns 404."""
        response = await client.patch("/api/v1/signals/999999/read", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_signal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        """DELETE removes the signal."""
        response = await client.delete(f"/api/v1/signals/{test_signal.id}", headers=auth_headers)
        assert response.status_code == 200

        # Confirm it's gone
        check = await client.get("/api/v1/signals", headers=auth_headers)
        assert all(s["id"] != test_signal.id for s in check.json())

    @pytest.mark.asyncio
    async def test_delete_signal_not_found(self, client: AsyncClient, auth_headers: dict):
        """DELETE on non-existent signal returns 404."""
        response = await client.delete("/api/v1/signals/999999", headers=auth_headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Subscription tests
# ---------------------------------------------------------------------------


class TestSignalSubscription:
    """Tests for GET /signals/subscription and POST /signals/subscription."""

    @pytest.mark.asyncio
    async def test_get_subscription_no_subscription(self, client: AsyncClient, auth_headers: dict):
        """GET returns null when user has no subscription."""
        response = await client.get("/api/v1/signals/subscription", headers=auth_headers)
        assert response.status_code == 200
        # Pydantic Optional returns null in JSON
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_get_subscription_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_subscription: SignalSubscription,
    ):
        """GET returns subscription details when one exists."""
        response = await client.get("/api/v1/signals/subscription", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email_digest_enabled"] is True
        assert "cybersecurity" in data["keywords"]

    @pytest.mark.asyncio
    async def test_upsert_subscription_create(self, client: AsyncClient, auth_headers: dict):
        """POST creates a new subscription when none exists."""
        response = await client.post(
            "/api/v1/signals/subscription",
            headers=auth_headers,
            json={
                "agencies": ["Department of Defense"],
                "naics_codes": ["541512"],
                "keywords": ["cloud", "cyber"],
                "email_digest_enabled": False,
                "digest_frequency": "daily",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "cybersecurity" not in data["keywords"]  # should be cloud/cyber
        assert "cloud" in data["keywords"]

    @pytest.mark.asyncio
    async def test_upsert_subscription_update(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_subscription: SignalSubscription,
    ):
        """POST updates existing subscription fields."""
        response = await client.post(
            "/api/v1/signals/subscription",
            headers=auth_headers,
            json={
                "agencies": ["Department of State"],
                "naics_codes": [],
                "keywords": ["diplomacy"],
                "email_digest_enabled": False,
                "digest_frequency": "weekly",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email_digest_enabled"] is False
        assert "diplomacy" in data["keywords"]


# ---------------------------------------------------------------------------
# Digest preview tests
# ---------------------------------------------------------------------------


class TestSignalDigest:
    """Tests for GET /signals/digest-preview and POST /signals/digest-send."""

    @pytest.mark.asyncio
    async def test_digest_preview_empty(self, client: AsyncClient, auth_headers: dict):
        """Digest preview with no signals returns zeros."""
        response = await client.get("/api/v1/signals/digest-preview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_unread" in data
        assert "period_days" in data
        assert data["total_unread"] == 0

    @pytest.mark.asyncio
    async def test_digest_send_no_subscription(self, client: AsyncClient, auth_headers: dict):
        """Digest send returns 400 when user has no subscription."""
        response = await client.post("/api/v1/signals/digest-send", headers=auth_headers)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_digest_send_disabled_subscription(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        test_user: User,
    ):
        """Digest send returns 400 when digest is disabled on subscription."""
        sub = SignalSubscription(
            user_id=test_user.id,
            agencies=[],
            naics_codes=[],
            keywords=[],
            email_digest_enabled=False,
            digest_frequency=DigestFrequency.DAILY,
        )
        db_session.add(sub)
        await db_session.commit()

        response = await client.post("/api/v1/signals/digest-send", headers=auth_headers)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_digest_send_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_subscription: SignalSubscription,
    ):
        """Digest send returns payload when digest is enabled."""
        response = await client.post("/api/v1/signals/digest-send", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "recipient_email" in data
        assert data["simulated"] is True
