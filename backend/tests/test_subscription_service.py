"""
Unit + integration tests for subscription_service.py
=====================================================
Tests plan definitions, feature access checks, usage stats,
subscription status helpers, and Stripe integration (mocked).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User, UserTier
from app.services.auth_service import hash_password
from app.services.subscription_service import (
    PLAN_DEFINITIONS,
    CheckoutSessionResponse,
    PlanDefinition,
    PlanFeature,
    UsageStats,
    _get_stripe_price_id,
    _resolve_tier_from_subscription,
    check_feature_access,
    create_checkout_session,
    create_customer_portal_session,
    get_all_plans,
    get_plan_details,
    get_subscription_status,
    get_usage_stats,
    is_subscription_active,
)

# =============================================================================
# Plan Definitions
# =============================================================================


class TestPlanDefinitions:
    def test_all_tiers_have_definitions(self):
        for tier in UserTier:
            assert tier.value in PLAN_DEFINITIONS

    def test_free_plan_has_zero_prices(self):
        free = PLAN_DEFINITIONS[UserTier.FREE.value]
        assert free.price_monthly == 0
        assert free.price_yearly == 0

    def test_starter_plan_has_nonzero_prices(self):
        starter = PLAN_DEFINITIONS[UserTier.STARTER.value]
        assert starter.price_monthly > 0
        assert starter.price_yearly > 0
        assert starter.price_yearly < starter.price_monthly * 12  # discount

    def test_professional_limits_are_higher_than_starter(self):
        starter = PLAN_DEFINITIONS[UserTier.STARTER.value]
        pro = PLAN_DEFINITIONS[UserTier.PROFESSIONAL.value]
        assert pro.limits["rfps"] > starter.limits["rfps"]
        assert pro.limits["api_calls_per_day"] > starter.limits["api_calls_per_day"]

    def test_enterprise_has_unlimited_rfps(self):
        ent = PLAN_DEFINITIONS[UserTier.ENTERPRISE.value]
        assert ent.limits["rfps"] == -1
        assert ent.limits["proposals"] == -1

    def test_plan_features_are_list_of_plan_feature(self):
        for tier, plan in PLAN_DEFINITIONS.items():
            assert isinstance(plan.features, list)
            for feat in plan.features:
                assert isinstance(feat, PlanFeature)
                assert isinstance(feat.name, str)
                assert isinstance(feat.included, bool)


class TestGetPlanDetails:
    def test_returns_plan_for_valid_tier(self):
        plan = get_plan_details("professional")
        assert plan is not None
        assert plan.tier == "professional"
        assert plan.label == "Professional"

    def test_returns_none_for_invalid_tier(self):
        assert get_plan_details("nonexistent") is None


class TestGetAllPlans:
    def test_returns_all_four_plans(self):
        plans = get_all_plans()
        assert len(plans) == 4

    def test_plans_in_tier_order(self):
        plans = get_all_plans()
        tiers = [p.tier for p in plans]
        assert tiers == ["free", "starter", "professional", "enterprise"]


# =============================================================================
# Feature Access
# =============================================================================


class TestCheckFeatureAccess:
    def _make_user(self, tier: UserTier) -> User:
        mock_user = MagicMock(spec=User)
        mock_user.tier = tier
        return mock_user

    def test_free_user_cannot_access_deep_read(self):
        user = self._make_user(UserTier.FREE)
        assert check_feature_access(user, "deep_read") is False

    def test_starter_user_can_access_deep_read(self):
        user = self._make_user(UserTier.STARTER)
        assert check_feature_access(user, "deep_read") is True

    def test_professional_user_can_access_export_docx(self):
        user = self._make_user(UserTier.PROFESSIONAL)
        assert check_feature_access(user, "export_docx") is True

    def test_starter_cannot_access_export_docx(self):
        user = self._make_user(UserTier.STARTER)
        assert check_feature_access(user, "export_docx") is False

    def test_unknown_feature_allowed(self):
        user = self._make_user(UserTier.FREE)
        assert check_feature_access(user, "nonexistent_feature") is True

    def test_enterprise_can_access_everything(self):
        user = self._make_user(UserTier.ENTERPRISE)
        for feature in ["deep_read", "ai_draft", "export_docx"]:
            assert check_feature_access(user, feature) is True


# =============================================================================
# Usage Stats (DB integration)
# =============================================================================


@pytest_asyncio.fixture
async def sub_user(db_session: AsyncSession) -> User:
    user = User(
        email="sub@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Sub User",
        company_name="Sub Co",
        tier="professional",
        is_active=True,
        api_calls_today=42,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestGetUsageStats:
    @pytest.mark.asyncio
    async def test_usage_stats_empty_user(self, db_session: AsyncSession, sub_user: User):
        stats = await get_usage_stats(sub_user.id, db_session)
        assert isinstance(stats, UsageStats)
        assert stats.rfps_used == 0
        assert stats.proposals_used == 0
        assert stats.api_calls_used == 42

    @pytest.mark.asyncio
    async def test_usage_stats_with_rfps_and_proposals(
        self, db_session: AsyncSession, sub_user: User
    ):
        # Add RFPs
        for i in range(3):
            rfp = RFP(
                user_id=sub_user.id,
                title=f"RFP {i}",
                solicitation_number=f"SOL-{i}",
                notice_id=f"notice-{i}",
                agency="DoD",
                naics_code="541512",
                rfp_type="solicitation",
                status="new",
            )
            db_session.add(rfp)
        await db_session.flush()

        # Get first RFP for proposal FK
        from sqlmodel import select

        result = await db_session.execute(select(RFP).where(RFP.user_id == sub_user.id))
        first_rfp = result.scalars().first()

        for i in range(2):
            proposal = Proposal(
                user_id=sub_user.id,
                rfp_id=first_rfp.id,
                title=f"Proposal {i}",
                status="draft",
                total_sections=1,
                completed_sections=0,
            )
            db_session.add(proposal)
        await db_session.commit()

        stats = await get_usage_stats(sub_user.id, db_session)
        assert stats.rfps_used == 3
        assert stats.proposals_used == 2
        # professional tier limits
        assert stats.rfps_limit == 500
        assert stats.proposals_limit == -1  # unlimited

    @pytest.mark.asyncio
    async def test_usage_stats_nonexistent_user(self, db_session: AsyncSession):
        stats = await get_usage_stats(99999, db_session)
        assert stats.rfps_used == 0
        assert stats.rfps_limit == 0

    @pytest.mark.asyncio
    async def test_usage_stats_api_calls_limit(self, db_session: AsyncSession, sub_user: User):
        stats = await get_usage_stats(sub_user.id, db_session)
        pro_plan = PLAN_DEFINITIONS["professional"]
        assert stats.api_calls_limit == pro_plan.limits["api_calls_per_day"]


# =============================================================================
# Subscription Status Helpers
# =============================================================================


class TestIsSubscriptionActive:
    def _make_user(self, tier: UserTier, expires_at: datetime | None) -> User:
        mock_user = MagicMock(spec=User)
        mock_user.tier = tier
        mock_user.subscription_expires_at = expires_at
        return mock_user

    def test_free_user_not_active(self):
        user = self._make_user(UserTier.FREE, None)
        assert is_subscription_active(user) is False

    def test_active_subscription(self):
        user = self._make_user(
            UserTier.PROFESSIONAL,
            datetime.now(UTC) + timedelta(days=30),
        )
        assert is_subscription_active(user) is True

    def test_expired_subscription_within_grace(self):
        user = self._make_user(
            UserTier.PROFESSIONAL,
            datetime.now(UTC) - timedelta(days=1),  # expired 1 day ago
        )
        # 3-day grace period
        assert is_subscription_active(user) is True

    def test_expired_subscription_beyond_grace(self):
        user = self._make_user(
            UserTier.PROFESSIONAL,
            datetime.now(UTC) - timedelta(days=5),
        )
        assert is_subscription_active(user) is False

    def test_no_expiry_date(self):
        user = self._make_user(UserTier.STARTER, None)
        assert is_subscription_active(user) is False


class TestGetSubscriptionStatus:
    def _make_user(self, tier: UserTier, expires_at: datetime | None) -> User:
        mock_user = MagicMock(spec=User)
        mock_user.tier = tier
        mock_user.subscription_expires_at = expires_at
        return mock_user

    def test_free_returns_free(self):
        user = self._make_user(UserTier.FREE, None)
        assert get_subscription_status(user) == "free"

    def test_active_returns_active(self):
        user = self._make_user(
            UserTier.PROFESSIONAL,
            datetime.now(UTC) + timedelta(days=30),
        )
        assert get_subscription_status(user) == "active"

    def test_grace_period_returns_grace_period(self):
        user = self._make_user(
            UserTier.PROFESSIONAL,
            datetime.now(UTC) - timedelta(days=2),
        )
        assert get_subscription_status(user) == "grace_period"

    def test_expired_returns_expired(self):
        user = self._make_user(
            UserTier.PROFESSIONAL,
            datetime.now(UTC) - timedelta(days=10),
        )
        assert get_subscription_status(user) == "expired"

    def test_no_expiry_returns_free(self):
        user = self._make_user(UserTier.STARTER, None)
        assert get_subscription_status(user) == "free"


# =============================================================================
# Stripe Price ID Resolution
# =============================================================================


class TestGetStripePriceId:
    def test_valid_tier_monthly(self):
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.stripe_starter_monthly_price_id = "price_abc"
            result = _get_stripe_price_id("starter", annual=False)
            assert result == "price_abc"

    def test_valid_tier_yearly(self):
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.stripe_starter_yearly_price_id = "price_xyz"
            result = _get_stripe_price_id("starter", annual=True)
            assert result == "price_xyz"

    def test_free_tier_returns_none(self):
        result = _get_stripe_price_id("free", annual=False)
        assert result is None

    def test_unknown_tier_returns_none(self):
        result = _get_stripe_price_id("unknown", annual=False)
        assert result is None


# =============================================================================
# Resolve Tier from Subscription
# =============================================================================


class TestResolveTierFromSubscription:
    def setup_method(self):
        # Reset the global cache
        import app.services.subscription_service as mod

        mod.TIER_FROM_PRICE = None

    def test_resolves_from_metadata(self):
        sub = {
            "items": {"data": []},
            "metadata": {"tier": "professional"},
        }
        tier = _resolve_tier_from_subscription(sub)
        assert tier == "professional"

    def test_falls_back_to_free_if_unknown(self):
        sub = {
            "items": {"data": []},
            "metadata": {},
        }
        tier = _resolve_tier_from_subscription(sub)
        assert tier == "free"

    def test_resolves_from_price_id(self):
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.stripe_starter_monthly_price_id = "price_starter_m"
            mock_settings.stripe_starter_yearly_price_id = None
            mock_settings.stripe_professional_monthly_price_id = None
            mock_settings.stripe_professional_yearly_price_id = None
            mock_settings.stripe_enterprise_monthly_price_id = None
            mock_settings.stripe_enterprise_yearly_price_id = None

            import app.services.subscription_service as mod

            mod.TIER_FROM_PRICE = None

            sub = {
                "items": {"data": [{"price": {"id": "price_starter_m"}}]},
                "metadata": {},
            }
            tier = _resolve_tier_from_subscription(sub)
            assert tier == "starter"


# =============================================================================
# Checkout Session (mocked Stripe)
# =============================================================================


class TestCreateCheckoutSession:
    def _make_user(self, **overrides) -> User:
        defaults = {
            "id": 1,
            "email": "test@example.com",
            "full_name": "Test User",
            "tier": UserTier.PROFESSIONAL,
            "stripe_customer_id": "cus_abc",
            "stripe_subscription_id": None,
        }
        defaults.update(overrides)
        mock_user = MagicMock(spec=User)
        for k, v in defaults.items():
            setattr(mock_user, k, v)
        return mock_user

    @pytest.mark.asyncio
    async def test_enterprise_redirects_to_contact(self):
        user = self._make_user()
        with patch("app.services.subscription_service._configure_stripe", return_value=True):
            result = await create_checkout_session(user, tier="enterprise")
            assert isinstance(result, CheckoutSessionResponse)
            assert "contact" in result.checkout_url
            assert "enterprise" in result.checkout_url

    @pytest.mark.asyncio
    async def test_returns_error_when_stripe_not_configured(self):
        user = self._make_user()
        with patch("app.services.subscription_service._configure_stripe", return_value=False):
            result = await create_checkout_session(user, tier="starter")
            assert "error=stripe_not_configured" in result.checkout_url

    @pytest.mark.asyncio
    async def test_returns_error_when_price_id_missing(self):
        user = self._make_user()
        with (
            patch("app.services.subscription_service._configure_stripe", return_value=True),
            patch("app.services.subscription_service._get_stripe_price_id", return_value=None),
        ):
            result = await create_checkout_session(user, tier="starter")
            assert "error=price_not_configured" in result.checkout_url


# =============================================================================
# Customer Portal (mocked Stripe)
# =============================================================================


class TestCreateCustomerPortalSession:
    @pytest.mark.asyncio
    async def test_returns_fallback_when_not_configured(self):
        mock_user = MagicMock(spec=User)
        mock_user.stripe_customer_id = None
        with patch("app.services.subscription_service._configure_stripe", return_value=False):
            url = await create_customer_portal_session(mock_user)
            assert "subscription" in url

    @pytest.mark.asyncio
    async def test_returns_fallback_when_no_customer_id(self):
        mock_user = MagicMock(spec=User)
        mock_user.stripe_customer_id = None
        with patch("app.services.subscription_service._configure_stripe", return_value=True):
            url = await create_customer_portal_session(mock_user)
            assert "subscription" in url


# =============================================================================
# Pydantic Models
# =============================================================================


class TestPydanticModels:
    def test_plan_feature(self):
        feat = PlanFeature(name="Deep Read", included=True)
        assert feat.name == "Deep Read"
        assert feat.included is True

    def test_plan_definition(self):
        plan = PlanDefinition(
            tier="test",
            label="Test",
            price_monthly=100,
            price_yearly=1000,
            description="A test plan",
            features=[PlanFeature(name="Feature 1", included=True)],
            limits={"rfps": 10},
        )
        assert plan.tier == "test"
        assert len(plan.features) == 1

    def test_usage_stats(self):
        stats = UsageStats(
            rfps_used=5,
            rfps_limit=50,
            proposals_used=3,
            proposals_limit=20,
            api_calls_used=100,
            api_calls_limit=500,
        )
        assert stats.rfps_used == 5

    def test_checkout_session_response(self):
        resp = CheckoutSessionResponse(
            checkout_url="https://checkout.stripe.com/xxx",
            session_id="cs_abc",
        )
        assert resp.checkout_url.startswith("https://")
