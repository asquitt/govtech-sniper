"""
Subscription Service Unit Tests
================================
Tests for pure helpers: plan definitions, feature access, subscription status,
Stripe price resolution, and tier mapping.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from app.models.user import UserTier
from app.services.subscription_service import (
    PLAN_DEFINITIONS,
    _build_price_to_tier_map,
    _get_stripe_price_id,
    _resolve_tier_from_subscription,
    check_feature_access,
    get_all_plans,
    get_plan_details,
    get_subscription_status,
    is_subscription_active,
)

# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------


class TestPlanDefinitions:
    def test_all_tiers_present(self):
        for tier in [UserTier.FREE, UserTier.STARTER, UserTier.PROFESSIONAL, UserTier.ENTERPRISE]:
            assert tier.value in PLAN_DEFINITIONS

    def test_free_plan_zero_cost(self):
        free = PLAN_DEFINITIONS[UserTier.FREE.value]
        assert free.price_monthly == 0
        assert free.price_yearly == 0

    def test_starter_has_limits(self):
        starter = PLAN_DEFINITIONS[UserTier.STARTER.value]
        assert starter.limits["rfps"] == 50
        assert starter.limits["proposals"] == 20

    def test_professional_unlimited_proposals(self):
        pro = PLAN_DEFINITIONS[UserTier.PROFESSIONAL.value]
        assert pro.limits["proposals"] == -1


class TestGetPlanDetails:
    def test_known_tier(self):
        result = get_plan_details("free")
        assert result is not None
        assert result.tier == "free"

    def test_unknown_tier(self):
        assert get_plan_details("nonexistent") is None


class TestGetAllPlans:
    def test_returns_all_four(self):
        plans = get_all_plans()
        assert len(plans) == 4

    def test_order(self):
        plans = get_all_plans()
        assert plans[0].tier == "free"
        assert plans[1].tier == "starter"
        assert plans[2].tier == "professional"
        assert plans[3].tier == "enterprise"


# ---------------------------------------------------------------------------
# Feature access
# ---------------------------------------------------------------------------


class TestCheckFeatureAccess:
    def _make_user(self, tier: str):
        return SimpleNamespace(tier=UserTier(tier))

    def test_free_user_basic_access(self):
        user = self._make_user("free")
        # Unknown features default to allowed
        assert check_feature_access(user, "nonexistent_feature") is True

    def test_feature_gate_respected(self):
        user = self._make_user("free")
        # Patch FEATURE_GATES to require starter for "ai_drafting"
        with patch(
            "app.services.subscription_service.FEATURE_GATES",
            {"ai_drafting": UserTier.STARTER},
        ):
            assert check_feature_access(user, "ai_drafting") is False

    def test_higher_tier_grants_access(self):
        user = self._make_user("professional")
        with patch(
            "app.services.subscription_service.FEATURE_GATES",
            {"ai_drafting": UserTier.STARTER},
        ):
            assert check_feature_access(user, "ai_drafting") is True


# ---------------------------------------------------------------------------
# Subscription status helpers
# ---------------------------------------------------------------------------


class TestIsSubscriptionActive:
    def _make_user(self, tier: str, expires_at=None, **kwargs):
        return SimpleNamespace(
            tier=UserTier(tier),
            subscription_expires_at=expires_at,
            **kwargs,
        )

    def test_free_user_inactive(self):
        user = self._make_user("free")
        assert is_subscription_active(user) is False

    def test_no_expiry_inactive(self):
        user = self._make_user("starter", expires_at=None)
        assert is_subscription_active(user) is False

    def test_future_expiry_active(self):
        user = self._make_user("starter", expires_at=datetime.now(UTC) + timedelta(days=30))
        assert is_subscription_active(user) is True

    def test_recently_expired_grace_period(self):
        # Expired 1 day ago — within 3-day grace
        user = self._make_user("starter", expires_at=datetime.now(UTC) - timedelta(days=1))
        assert is_subscription_active(user) is True

    def test_expired_beyond_grace(self):
        user = self._make_user("starter", expires_at=datetime.now(UTC) - timedelta(days=5))
        assert is_subscription_active(user) is False


class TestGetSubscriptionStatus:
    def _make_user(self, tier: str, expires_at=None):
        return SimpleNamespace(tier=UserTier(tier), subscription_expires_at=expires_at)

    def test_free_user(self):
        assert get_subscription_status(self._make_user("free")) == "free"

    def test_no_expiry(self):
        assert get_subscription_status(self._make_user("starter", None)) == "free"

    def test_active(self):
        user = self._make_user("starter", datetime.now(UTC) + timedelta(days=10))
        assert get_subscription_status(user) == "active"

    def test_grace_period(self):
        user = self._make_user("starter", datetime.now(UTC) - timedelta(days=2))
        assert get_subscription_status(user) == "grace_period"

    def test_expired(self):
        user = self._make_user("starter", datetime.now(UTC) - timedelta(days=10))
        assert get_subscription_status(user) == "expired"


# ---------------------------------------------------------------------------
# Stripe helpers
# ---------------------------------------------------------------------------


class TestGetStripePriceId:
    def test_known_tier_monthly(self):
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.stripe_starter_monthly_price_id = "price_starter_m"
            result = _get_stripe_price_id("starter", annual=False)
            assert result == "price_starter_m"

    def test_known_tier_yearly(self):
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.stripe_professional_yearly_price_id = "price_pro_y"
            result = _get_stripe_price_id("professional", annual=True)
            assert result == "price_pro_y"

    def test_unknown_tier(self):
        result = _get_stripe_price_id("nonexistent", annual=False)
        assert result is None

    def test_free_tier_not_in_map(self):
        result = _get_stripe_price_id("free", annual=False)
        assert result is None


class TestBuildPriceToTierMap:
    def test_builds_map(self):
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.stripe_starter_monthly_price_id = "price_sm"
            mock_settings.stripe_starter_yearly_price_id = "price_sy"
            mock_settings.stripe_professional_monthly_price_id = None
            mock_settings.stripe_professional_yearly_price_id = "price_py"
            mock_settings.stripe_enterprise_monthly_price_id = None
            mock_settings.stripe_enterprise_yearly_price_id = None
            result = _build_price_to_tier_map()
            assert result["price_sm"] == "starter"
            assert result["price_sy"] == "starter"
            assert result["price_py"] == "professional"
            assert len(result) == 3


class TestResolveTierFromSubscription:
    def test_from_items(self):
        with patch("app.services.subscription_service.TIER_FROM_PRICE", {"price_123": "starter"}):
            sub = {"items": {"data": [{"price": {"id": "price_123"}}]}}
            assert _resolve_tier_from_subscription(sub) == "starter"

    def test_from_metadata_fallback(self):
        with patch("app.services.subscription_service.TIER_FROM_PRICE", {}):
            sub = {
                "items": {"data": []},
                "metadata": {"tier": "professional"},
            }
            assert _resolve_tier_from_subscription(sub) == "professional"

    def test_defaults_to_free(self):
        with patch("app.services.subscription_service.TIER_FROM_PRICE", {}):
            sub = {"items": {"data": []}, "metadata": {}}
            assert _resolve_tier_from_subscription(sub) == "free"

    def test_no_items_key(self):
        with patch("app.services.subscription_service.TIER_FROM_PRICE", {}):
            sub = {"metadata": {"tier": "starter"}}
            assert _resolve_tier_from_subscription(sub) == "starter"
