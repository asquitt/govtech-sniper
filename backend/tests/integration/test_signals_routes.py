"""
Signals Routes Integration Tests
===================================
Tests for market signal CRUD, feed, subscriptions, ingestion, and digest.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_signal import MarketSignal, SignalType
from app.models.user import User

# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture
async def test_signal(db_session: AsyncSession, test_user: User) -> MarketSignal:
    signal = MarketSignal(
        user_id=test_user.id,
        title="DoD Budget Increase for Cyber",
        signal_type=SignalType.NEWS,
        agency="DoD",
        content="Budget allocation increased by 15%.",
        source_url="https://example.com/news/1",
        relevance_score=75.0,
        is_read=False,
    )
    db_session.add(signal)
    await db_session.commit()
    await db_session.refresh(signal)
    return signal


# =============================================================================
# GET /signals — list signals
# =============================================================================


class TestListSignals:
    @pytest.mark.asyncio
    async def test_list_signals_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/signals")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_signals_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/signals", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_list_signals_returns_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        resp = await client.get("/api/v1/signals", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["title"] == "DoD Budget Increase for Cyber"


# =============================================================================
# POST /signals — create signal
# =============================================================================


class TestCreateSignal:
    @pytest.mark.asyncio
    async def test_create_signal_success(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/signals",
            json={
                "title": "New Opportunity",
                "signal_type": "news",
                "agency": "GSA",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New Opportunity"
        assert data["signal_type"] == "news"


# =============================================================================
# GET /signals/feed — filtered feed
# =============================================================================


class TestSignalFeed:
    @pytest.mark.asyncio
    async def test_feed_returns_list(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/signals/feed", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_feed_filter_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        resp = await client.get(
            "/api/v1/signals/feed?signal_type=news",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_feed_filter_unread_only(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/signals/feed?unread_only=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200


# =============================================================================
# PATCH /signals/{id}/read — mark read
# =============================================================================


class TestMarkSignalRead:
    @pytest.mark.asyncio
    async def test_mark_read_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        resp = await client.patch(
            f"/api/v1/signals/{test_signal.id}/read",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_read_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.patch("/api/v1/signals/99999/read", headers=auth_headers)
        assert resp.status_code == 404


# =============================================================================
# DELETE /signals/{id} — delete signal
# =============================================================================


class TestDeleteSignal:
    @pytest.mark.asyncio
    async def test_delete_signal_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_signal: MarketSignal,
    ):
        resp = await client.delete(
            f"/api/v1/signals/{test_signal.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_signal_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete("/api/v1/signals/99999", headers=auth_headers)
        assert resp.status_code == 404


# =============================================================================
# Subscription (signal preferences)
# =============================================================================


class TestSignalSubscription:
    @pytest.mark.asyncio
    async def test_get_subscription_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/signals/subscription", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_upsert_subscription(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/signals/subscription",
            json={
                "agencies": ["DoD", "GSA"],
                "naics_codes": ["541512"],
                "keywords": ["cybersecurity"],
                "email_digest_enabled": True,
                "digest_frequency": "daily",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "DoD" in data["agencies"]
        assert data["email_digest_enabled"] is True


# =============================================================================
# POST /signals/rescore — rescore signals
# =============================================================================


class TestRescoreSignals:
    @pytest.mark.asyncio
    async def test_rescore_returns_summary(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/signals/rescore", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "updated" in data
        assert "average_score" in data
