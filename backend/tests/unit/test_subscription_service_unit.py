"""
Subscription Service Unit Tests
=================================
Tests for plan definitions, feature access, usage stats, and subscription
status helpers. All DB and Stripe calls are mocked.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import User, UserTier
from app.services.subscription_service import (
    PLAN_DEFINITIONS,
    check_feature_access,
    get_all_plans,
    get_plan_details,
    get_subscription_status,
    get_usage_stats,
    is_subscription_active,
)

# =============================================================================
# Helpers
# =============================================================================


def make_user(
    tier: UserTier = UserTier.FREE,
    subscription_expires_at: datetime | None = None,
    api_calls_today: int = 0,
) -> User:
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.tier = tier
    user.subscription_expires_at = subscription_expires_at
    user.stripe_customer_id = None
    user.stripe_subscription_id = None
    user.api_calls_today = api_calls_today
    return user


# =============================================================================
# Plan definitions
# =============================================================================


class TestPlanDefinitions:
    def test_all_four_tiers_defined(self):
        for tier in [UserTier.FREE, UserTier.STARTER, UserTier.PROFESSIONAL, UserTier.ENTERPRISE]:
            assert tier.value in PLAN_DEFINITIONS

    def test_free_plan_limits(self):
        plan = PLAN_DEFINITIONS[UserTier.FREE.value]
        assert plan.limits["rfps"] == 10
        assert plan.limits["proposals"] == 5

    def test_starter_plan_price_monthly(self):
        plan = PLAN_DEFINITIONS[UserTier.STARTER.value]
        assert plan.price_monthly == 9900

    def test_professional_plan_unlimited_proposals(self):
        plan = PLAN_DEFINITIONS[UserTier.PROFESSIONAL.value]
        assert plan.limits["proposals"] == -1

    def test_enterprise_plan_unlimited_everything(self):
        plan = PLAN_DEFINITIONS[UserTier.ENTERPRISE.value]
        assert plan.limits["rfps"] == -1
        assert plan.limits["proposals"] == -1

    def test_all_plans_have_api_calls_limit(self):
        for plan in PLAN_DEFINITIONS.values():
            assert "api_calls_per_day" in plan.limits


class TestGetPlanDetails:
    def test_returns_plan_for_valid_tier(self):
        plan = get_plan_details(UserTier.STARTER.value)
        assert plan is not None
        assert plan.tier == UserTier.STARTER.value

    def test_returns_none_for_unknown_tier(self):
        plan = get_plan_details("platinum")
        assert plan is None


class TestGetAllPlans:
    def test_returns_four_plans_in_order(self):
        plans = get_all_plans()
        assert len(plans) == 4
        tiers = [p.tier for p in plans]
        assert tiers[0] == UserTier.FREE.value
        assert tiers[-1] == UserTier.ENTERPRISE.value

    def test_plans_sorted_free_to_enterprise(self):
        plans = get_all_plans()
        assert plans[0].tier == "free"
        assert plans[1].tier == "starter"
        assert plans[2].tier == "professional"
        assert plans[3].tier == "enterprise"


# =============================================================================
# Feature access checks
# =============================================================================


class TestCheckFeatureAccess:
    def test_free_user_denied_ai_drafting(self):
        user = make_user(tier=UserTier.FREE)
        with (
            patch("app.services.subscription_service.FEATURE_GATES") as mock_gates,
            patch("app.services.subscription_service.TIER_LEVELS") as mock_levels,
        ):
            mock_gates.get.return_value = UserTier.STARTER
            mock_levels.get.side_effect = lambda t, default=0: {
                "free": 0,
                "starter": 1,
                "professional": 2,
                "enterprise": 3,
            }.get(t, default)
            result = check_feature_access(user, "ai_drafting")
        assert result is False

    def test_starter_user_has_ai_drafting(self):
        user = make_user(tier=UserTier.STARTER)
        with (
            patch("app.services.subscription_service.FEATURE_GATES") as mock_gates,
            patch("app.services.subscription_service.TIER_LEVELS") as mock_levels,
        ):
            mock_gates.get.return_value = UserTier.STARTER
            mock_levels.get.side_effect = lambda t, default=0: {
                "free": 0,
                "starter": 1,
                "professional": 2,
                "enterprise": 3,
            }.get(t, default)
            result = check_feature_access(user, "ai_drafting")
        assert result is True

    def test_professional_user_has_all_starter_features(self):
        user = make_user(tier=UserTier.PROFESSIONAL)
        with (
            patch("app.services.subscription_service.FEATURE_GATES") as mock_gates,
            patch("app.services.subscription_service.TIER_LEVELS") as mock_levels,
        ):
            mock_gates.get.return_value = UserTier.STARTER
            mock_levels.get.side_effect = lambda t, default=0: {
                "free": 0,
                "starter": 1,
                "professional": 2,
                "enterprise": 3,
            }.get(t, default)
            result = check_feature_access(user, "any_starter_feature")
        assert result is True

    def test_unknown_feature_returns_true(self):
        user = make_user(tier=UserTier.FREE)
        with (
            patch("app.services.subscription_service.FEATURE_GATES") as mock_gates,
            patch("app.services.subscription_service.TIER_LEVELS"),
        ):
            mock_gates.get.return_value = None
            result = check_feature_access(user, "completely_unknown_feature")
        assert result is True


# =============================================================================
# get_usage_stats
# =============================================================================


class TestGetUsageStats:
    @pytest.mark.asyncio
    async def test_returns_zero_stats_for_unknown_user(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        stats = await get_usage_stats(999, mock_session)

        assert stats.rfps_used == 0
        assert stats.proposals_used == 0
        assert stats.api_calls_used == 0

    @pytest.mark.asyncio
    async def test_returns_correct_counts_for_existing_user(self):
        mock_session = AsyncMock()
        user = make_user(tier=UserTier.STARTER, api_calls_today=42)

        # Mock three sequential execute calls: user, rfp count, proposal count
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        rfp_result = MagicMock()
        rfp_result.scalar.return_value = 7

        proposal_result = MagicMock()
        proposal_result.scalar.return_value = 3

        mock_session.execute = AsyncMock(side_effect=[user_result, rfp_result, proposal_result])

        stats = await get_usage_stats(1, mock_session)

        assert stats.rfps_used == 7
        assert stats.proposals_used == 3
        assert stats.api_calls_used == 42
        assert stats.rfps_limit == PLAN_DEFINITIONS[UserTier.STARTER.value].limits["rfps"]

    @pytest.mark.asyncio
    async def test_limits_reflect_plan_for_free_tier(self):
        mock_session = AsyncMock()
        user = make_user(tier=UserTier.FREE, api_calls_today=5)

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        rfp_result = MagicMock()
        rfp_result.scalar.return_value = 2
        proposal_result = MagicMock()
        proposal_result.scalar.return_value = 1

        mock_session.execute = AsyncMock(side_effect=[user_result, rfp_result, proposal_result])

        stats = await get_usage_stats(1, mock_session)

        assert stats.rfps_limit == 10
        assert stats.proposals_limit == 5


# =============================================================================
# is_subscription_active
# =============================================================================


class TestIsSubscriptionActive:
    def test_free_tier_not_active(self):
        user = make_user(tier=UserTier.FREE)
        assert is_subscription_active(user) is False

    def test_paid_tier_with_future_expiry_is_active(self):
        expires = datetime.now(UTC) + timedelta(days=30)
        user = make_user(tier=UserTier.STARTER, subscription_expires_at=expires)
        assert is_subscription_active(user) is True

    def test_paid_tier_with_no_expiry_not_active(self):
        user = make_user(tier=UserTier.STARTER, subscription_expires_at=None)
        assert is_subscription_active(user) is False

    def test_expired_subscription_within_grace_period_is_active(self):
        # 1 day past expiry is within 3-day grace window
        expires = datetime.now(UTC) - timedelta(days=1)
        user = make_user(tier=UserTier.PROFESSIONAL, subscription_expires_at=expires)
        assert is_subscription_active(user) is True

    def test_expired_subscription_outside_grace_period_not_active(self):
        # 5 days past expiry is outside 3-day grace window
        expires = datetime.now(UTC) - timedelta(days=5)
        user = make_user(tier=UserTier.PROFESSIONAL, subscription_expires_at=expires)
        assert is_subscription_active(user) is False


# =============================================================================
# get_subscription_status
# =============================================================================


class TestGetSubscriptionStatus:
    def test_free_tier_returns_free(self):
        user = make_user(tier=UserTier.FREE)
        assert get_subscription_status(user) == "free"

    def test_paid_with_no_expiry_returns_free(self):
        user = make_user(tier=UserTier.STARTER, subscription_expires_at=None)
        assert get_subscription_status(user) == "free"

    def test_active_subscription_returns_active(self):
        expires = datetime.now(UTC) + timedelta(days=30)
        user = make_user(tier=UserTier.STARTER, subscription_expires_at=expires)
        assert get_subscription_status(user) == "active"

    def test_within_grace_period_returns_grace_period(self):
        expires = datetime.now(UTC) - timedelta(days=1)
        user = make_user(tier=UserTier.PROFESSIONAL, subscription_expires_at=expires)
        assert get_subscription_status(user) == "grace_period"

    def test_outside_grace_period_returns_expired(self):
        expires = datetime.now(UTC) - timedelta(days=10)
        user = make_user(tier=UserTier.PROFESSIONAL, subscription_expires_at=expires)
        assert get_subscription_status(user) == "expired"
