"""
RFP Sniper - Subscription Service
===================================
Plan definitions, feature access checks, usage stats, and Stripe stubs.
"""

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.deps import FEATURE_GATES, TIER_LEVELS
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User, UserTier

logger = structlog.get_logger(__name__)


# =============================================================================
# Plan Definitions
# =============================================================================


class PlanFeature(BaseModel):
    name: str
    included: bool


class PlanDefinition(BaseModel):
    tier: str
    label: str
    price_monthly: int  # cents
    price_yearly: int  # cents
    description: str
    features: list[PlanFeature]
    limits: dict[str, int]


PLAN_DEFINITIONS: dict[str, PlanDefinition] = {
    UserTier.FREE.value: PlanDefinition(
        tier=UserTier.FREE.value,
        label="Free",
        price_monthly=0,
        price_yearly=0,
        description="Get started with basic opportunity tracking",
        features=[
            PlanFeature(name="Opportunity tracking", included=True),
            PlanFeature(name="Basic filtering", included=True),
            PlanFeature(name="Deep Read analysis", included=False),
            PlanFeature(name="AI drafting", included=False),
            PlanFeature(name="DOCX/PDF export", included=False),
            PlanFeature(name="Color team reviews", included=False),
            PlanFeature(name="Salesforce sync", included=False),
        ],
        limits={"rfps": 10, "proposals": 3, "api_calls_per_day": 100},
    ),
    UserTier.STARTER.value: PlanDefinition(
        tier=UserTier.STARTER.value,
        label="Starter",
        price_monthly=4900,
        price_yearly=47000,
        description="AI-powered analysis and drafting for solo consultants",
        features=[
            PlanFeature(name="Opportunity tracking", included=True),
            PlanFeature(name="Basic filtering", included=True),
            PlanFeature(name="Deep Read analysis", included=True),
            PlanFeature(name="AI drafting", included=True),
            PlanFeature(name="DOCX/PDF export", included=False),
            PlanFeature(name="Color team reviews", included=False),
            PlanFeature(name="Salesforce sync", included=False),
        ],
        limits={"rfps": 50, "proposals": 20, "api_calls_per_day": 500},
    ),
    UserTier.PROFESSIONAL.value: PlanDefinition(
        tier=UserTier.PROFESSIONAL.value,
        label="Professional",
        price_monthly=14900,
        price_yearly=143000,
        description="Full proposal workflow with exports and reviews",
        features=[
            PlanFeature(name="Opportunity tracking", included=True),
            PlanFeature(name="Basic filtering", included=True),
            PlanFeature(name="Deep Read analysis", included=True),
            PlanFeature(name="AI drafting", included=True),
            PlanFeature(name="DOCX/PDF export", included=True),
            PlanFeature(name="Color team reviews", included=True),
            PlanFeature(name="Salesforce sync", included=False),
        ],
        limits={"rfps": 500, "proposals": 200, "api_calls_per_day": 2000},
    ),
    UserTier.ENTERPRISE.value: PlanDefinition(
        tier=UserTier.ENTERPRISE.value,
        label="Enterprise",
        price_monthly=49900,
        price_yearly=479000,
        description="Unlimited access with CRM integrations and custom workflows",
        features=[
            PlanFeature(name="Opportunity tracking", included=True),
            PlanFeature(name="Basic filtering", included=True),
            PlanFeature(name="Deep Read analysis", included=True),
            PlanFeature(name="AI drafting", included=True),
            PlanFeature(name="DOCX/PDF export", included=True),
            PlanFeature(name="Color team reviews", included=True),
            PlanFeature(name="Salesforce sync", included=True),
        ],
        limits={"rfps": -1, "proposals": -1, "api_calls_per_day": 10000},
    ),
}


# =============================================================================
# Public Helpers
# =============================================================================


def get_plan_details(tier: str) -> PlanDefinition | None:
    """Return plan definition for a tier, or None if unknown."""
    return PLAN_DEFINITIONS.get(tier)


def get_all_plans() -> list[PlanDefinition]:
    """Return all plans in tier order."""
    order = [
        UserTier.FREE.value,
        UserTier.STARTER.value,
        UserTier.PROFESSIONAL.value,
        UserTier.ENTERPRISE.value,
    ]
    return [PLAN_DEFINITIONS[t] for t in order]


def check_feature_access(user: User, feature: str) -> bool:
    """Return True if the user's tier grants access to the named feature."""
    min_tier = FEATURE_GATES.get(feature)
    if min_tier is None:
        return True  # unknown feature → allow
    user_level = TIER_LEVELS.get(user.tier.value, 0)
    required_level = TIER_LEVELS.get(min_tier.value, 0)
    return user_level >= required_level


class UsageStats(BaseModel):
    rfps_used: int
    rfps_limit: int
    proposals_used: int
    proposals_limit: int
    api_calls_used: int
    api_calls_limit: int


async def get_usage_stats(user_id: int, session: AsyncSession) -> UsageStats:
    """Build usage counters for the subscription page."""
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return UsageStats(
            rfps_used=0,
            rfps_limit=0,
            proposals_used=0,
            proposals_limit=0,
            api_calls_used=0,
            api_calls_limit=0,
        )

    plan = PLAN_DEFINITIONS.get(user.tier.value, PLAN_DEFINITIONS[UserTier.FREE.value])

    rfp_count_result = await session.execute(
        select(func.count()).select_from(RFP).where(RFP.user_id == user_id)
    )
    rfp_count = rfp_count_result.scalar() or 0

    proposal_count_result = await session.execute(
        select(func.count()).select_from(Proposal).where(Proposal.user_id == user_id)
    )
    proposal_count = proposal_count_result.scalar() or 0

    return UsageStats(
        rfps_used=rfp_count,
        rfps_limit=plan.limits["rfps"],
        proposals_used=proposal_count,
        proposals_limit=plan.limits["proposals"],
        api_calls_used=user.api_calls_today,
        api_calls_limit=plan.limits["api_calls_per_day"],
    )


# =============================================================================
# Stripe Stubs
# =============================================================================


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


async def create_checkout_session(
    user: User,
    tier: str,
    annual: bool = False,
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout session. Stub implementation."""
    try:
        import stripe  # noqa: F401
        # In production: create a real checkout session via stripe.checkout.Session.create(...)
    except ImportError:
        pass

    logger.info("stripe_checkout_stub", user_id=user.id, tier=tier, annual=annual)
    return CheckoutSessionResponse(
        checkout_url=f"https://checkout.stripe.com/stub?tier={tier}&annual={annual}",
        session_id="cs_stub_placeholder",
    )


async def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Handle a Stripe webhook event. Stub implementation."""
    try:
        import stripe  # noqa: F401
        # In production: stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ImportError:
        pass

    logger.info("stripe_webhook_stub", payload_size=len(payload))
    return {"status": "stub", "message": "Webhook handling not yet implemented"}
