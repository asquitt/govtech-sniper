"""
Subscription Routes Integration Tests
========================================
Tests for plan listing, current plan, usage stats, status, checkout, and portal.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# =============================================================================
# GET /subscription/plans — public
# =============================================================================


class TestListPlans:
    @pytest.mark.asyncio
    async def test_plans_returns_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/subscription/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 4

    @pytest.mark.asyncio
    async def test_plans_contain_free_tier(self, client: AsyncClient):
        resp = await client.get("/api/v1/subscription/plans")
        tiers = [p["tier"] for p in resp.json()]
        assert "free" in tiers

    @pytest.mark.asyncio
    async def test_plans_sorted_by_price(self, client: AsyncClient):
        resp = await client.get("/api/v1/subscription/plans")
        plans = resp.json()
        prices = [p["price_monthly"] for p in plans]
        assert prices == sorted(prices)


# =============================================================================
# GET /subscription/current — current user plan
# =============================================================================


class TestCurrentPlan:
    @pytest.mark.asyncio
    async def test_current_plan_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/subscription/current")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_current_plan_returns_plan(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/subscription/current", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tier" in data
        assert "limits" in data


# =============================================================================
# GET /subscription/usage
# =============================================================================


class TestUsage:
    @pytest.mark.asyncio
    async def test_usage_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/subscription/usage")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_usage_returns_stats(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/subscription/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "rfps_used" in data
        assert "proposals_used" in data
        assert "api_calls_used" in data


# =============================================================================
# GET /subscription/status
# =============================================================================


class TestSubscriptionStatus:
    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/subscription/status")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_status_returns_tier_and_status(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/subscription/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tier" in data
        assert "status" in data
        assert "has_stripe_customer" in data
        assert "has_subscription" in data


# =============================================================================
# POST /subscription/checkout
# =============================================================================


class TestCheckout:
    @pytest.mark.asyncio
    async def test_checkout_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/subscription/checkout")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_checkout_calls_stripe(self, client: AsyncClient, auth_headers: dict):
        with patch(
            "app.api.routes.subscription.create_checkout_session",
            new=AsyncMock(return_value={"checkout_url": "https://checkout.stripe.com/test"}),
        ):
            resp = await client.post(
                "/api/v1/subscription/checkout?tier=starter",
                headers=auth_headers,
            )
        assert resp.status_code == 200


# =============================================================================
# POST /subscription/portal
# =============================================================================


class TestCustomerPortal:
    @pytest.mark.asyncio
    async def test_portal_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/subscription/portal")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_portal_returns_url(self, client: AsyncClient, auth_headers: dict):
        with patch(
            "app.api.routes.subscription.create_customer_portal_session",
            new=AsyncMock(return_value="https://billing.stripe.com/test"),
        ):
            resp = await client.post("/api/v1/subscription/portal", headers=auth_headers)
        assert resp.status_code == 200
        assert "portal_url" in resp.json()
