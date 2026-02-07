"""
RFP Sniper - Subscription Service
===================================
Plan definitions, feature access checks, usage stats, and Stripe integration.
"""

from datetime import UTC, datetime, timedelta

import stripe
import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.deps import FEATURE_GATES, TIER_LEVELS
from app.config import get_settings
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User, UserTier

logger = structlog.get_logger(__name__)
settings = get_settings()


# =============================================================================
# Plan Definitions — matches PRODUCTION_PLAN.md pricing
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
            PlanFeature(name="SAM.gov opportunity tracking", included=True),
            PlanFeature(name="Basic filtering & search", included=True),
            PlanFeature(name="5 proposals/month", included=True),
            PlanFeature(name="Deep Read analysis", included=False),
            PlanFeature(name="AI drafting", included=False),
            PlanFeature(name="DOCX/PDF export", included=False),
            PlanFeature(name="Word add-in", included=False),
            PlanFeature(name="Collaboration", included=False),
        ],
        limits={"rfps": 10, "proposals": 5, "api_calls_per_day": 100},
    ),
    UserTier.STARTER.value: PlanDefinition(
        tier=UserTier.STARTER.value,
        label="Starter",
        price_monthly=9900,
        price_yearly=95000,  # ~20% off
        description="AI-powered analysis and drafting for solo BD managers",
        features=[
            PlanFeature(name="SAM.gov opportunity tracking", included=True),
            PlanFeature(name="Basic filtering & search", included=True),
            PlanFeature(name="5 proposals/month", included=True),
            PlanFeature(name="Deep Read analysis", included=True),
            PlanFeature(name="AI drafting", included=True),
            PlanFeature(name="DOCX export", included=True),
            PlanFeature(name="Word add-in", included=False),
            PlanFeature(name="Collaboration", included=False),
        ],
        limits={"rfps": 50, "proposals": 20, "api_calls_per_day": 500},
    ),
    UserTier.PROFESSIONAL.value: PlanDefinition(
        tier=UserTier.PROFESSIONAL.value,
        label="Professional",
        price_monthly=19900,
        price_yearly=191000,  # ~20% off
        description="Full proposal workflow with collaboration and all data sources",
        features=[
            PlanFeature(name="All data sources (SAM, eBuy, SEWP)", included=True),
            PlanFeature(name="Unlimited proposals", included=True),
            PlanFeature(name="Deep Read analysis", included=True),
            PlanFeature(name="Full AI suite", included=True),
            PlanFeature(name="DOCX + PDF export", included=True),
            PlanFeature(name="Word add-in", included=True),
            PlanFeature(name="Color team reviews", included=True),
            PlanFeature(name="Real-time collaboration", included=True),
        ],
        limits={"rfps": 500, "proposals": -1, "api_calls_per_day": 2000},
    ),
    UserTier.ENTERPRISE.value: PlanDefinition(
        tier=UserTier.ENTERPRISE.value,
        label="Enterprise",
        price_monthly=0,  # custom pricing
        price_yearly=0,
        description="Custom pricing with SSO, SharePoint sync, and dedicated support",
        features=[
            PlanFeature(name="Everything in Professional", included=True),
            PlanFeature(name="SSO (Okta, Azure AD)", included=True),
            PlanFeature(name="SharePoint deep sync", included=True),
            PlanFeature(name="Salesforce integration", included=True),
            PlanFeature(name="Dedicated support + SLA", included=True),
            PlanFeature(name="Custom branding", included=True),
            PlanFeature(name="Admin console", included=True),
            PlanFeature(name="Audit & compliance tools", included=True),
        ],
        limits={"rfps": -1, "proposals": -1, "api_calls_per_day": 10000},
    ),
}

# Map tier+annual → Stripe Price ID setting names
PRICE_ID_MAP: dict[str, str] = {
    "starter_monthly": "stripe_starter_monthly_price_id",
    "starter_yearly": "stripe_starter_yearly_price_id",
    "professional_monthly": "stripe_professional_monthly_price_id",
    "professional_yearly": "stripe_professional_yearly_price_id",
    "enterprise_monthly": "stripe_enterprise_monthly_price_id",
    "enterprise_yearly": "stripe_enterprise_yearly_price_id",
}


def _get_stripe_price_id(tier: str, annual: bool) -> str | None:
    """Resolve the Stripe Price ID for a given tier + billing interval."""
    interval = "yearly" if annual else "monthly"
    attr = PRICE_ID_MAP.get(f"{tier}_{interval}")
    if attr:
        return getattr(settings, attr, None)
    return None


def _configure_stripe() -> bool:
    """Configure Stripe SDK. Returns True if properly configured."""
    if not settings.stripe_secret_key:
        return False
    stripe.api_key = settings.stripe_secret_key
    return True


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
# Stripe Integration
# =============================================================================


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


async def create_checkout_session(
    user: User,
    tier: str,
    annual: bool = False,
    session: AsyncSession | None = None,
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout Session for the given tier."""
    if not _configure_stripe():
        logger.warning("stripe_not_configured", user_id=user.id)
        return CheckoutSessionResponse(
            checkout_url=f"{settings.app_url}/settings/subscription?error=stripe_not_configured",
            session_id="",
        )

    # Enterprise is custom — redirect to contact
    if tier == UserTier.ENTERPRISE.value:
        return CheckoutSessionResponse(
            checkout_url=f"{settings.app_url}/contact?plan=enterprise",
            session_id="",
        )

    price_id = _get_stripe_price_id(tier, annual)
    if not price_id:
        logger.error("stripe_price_id_missing", tier=tier, annual=annual)
        return CheckoutSessionResponse(
            checkout_url=f"{settings.app_url}/settings/subscription?error=price_not_configured",
            session_id="",
        )

    # Get or create Stripe Customer
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name or user.email,
            metadata={"user_id": str(user.id)},
        )
        customer_id = customer.id
        if session:
            user.stripe_customer_id = customer_id
            session.add(user)
            await session.commit()

    # Build checkout session params
    checkout_params: dict = {
        "customer": customer_id,
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{settings.app_url}/settings/subscription?checkout=success",
        "cancel_url": f"{settings.app_url}/settings/subscription?checkout=cancelled",
        "metadata": {"user_id": str(user.id), "tier": tier},
        "allow_promotion_codes": True,
    }

    # Add free trial if user has never subscribed
    if not user.stripe_subscription_id and settings.stripe_free_trial_days > 0:
        checkout_params["subscription_data"] = {
            "trial_period_days": settings.stripe_free_trial_days,
            "metadata": {"user_id": str(user.id), "tier": tier},
        }

    checkout_session = stripe.checkout.Session.create(**checkout_params)
    logger.info(
        "stripe_checkout_created",
        user_id=user.id,
        tier=tier,
        annual=annual,
        session_id=checkout_session.id,
    )
    return CheckoutSessionResponse(
        checkout_url=checkout_session.url or "",
        session_id=checkout_session.id,
    )


async def create_customer_portal_session(user: User) -> str:
    """Create a Stripe Customer Portal session for self-service billing management."""
    if not _configure_stripe() or not user.stripe_customer_id:
        return f"{settings.app_url}/settings/subscription"

    portal_session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.app_url}/settings/subscription",
    )
    return portal_session.url or f"{settings.app_url}/settings/subscription"


# =============================================================================
# Webhook Handling
# =============================================================================

TIER_FROM_PRICE: dict[str, str] | None = None


def _build_price_to_tier_map() -> dict[str, str]:
    """Build a reverse map from Stripe Price ID → tier name."""
    mapping: dict[str, str] = {}
    for key, attr in PRICE_ID_MAP.items():
        price_id = getattr(settings, attr, None)
        if price_id:
            tier = key.split("_")[0]  # "starter_monthly" → "starter"
            mapping[price_id] = tier
    return mapping


def _resolve_tier_from_subscription(subscription: dict) -> str:
    """Determine which tier a Stripe Subscription maps to."""
    global TIER_FROM_PRICE
    if TIER_FROM_PRICE is None:
        TIER_FROM_PRICE = _build_price_to_tier_map()

    if subscription.get("items") and subscription["items"].get("data"):
        for item in subscription["items"]["data"]:
            price_id = item.get("price", {}).get("id", "")
            if price_id in TIER_FROM_PRICE:
                return TIER_FROM_PRICE[price_id]

    # Fallback: check metadata
    meta_tier = subscription.get("metadata", {}).get("tier")
    if meta_tier and meta_tier in PLAN_DEFINITIONS:
        return meta_tier

    return UserTier.FREE.value


async def handle_webhook(payload: bytes, sig_header: str, db: AsyncSession) -> dict:
    """Handle incoming Stripe webhook events."""
    if not _configure_stripe() or not settings.stripe_webhook_secret:
        logger.warning("stripe_webhook_not_configured")
        return {"status": "skipped", "reason": "not_configured"}

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        logger.error("stripe_webhook_signature_invalid")
        return {"status": "error", "reason": "invalid_signature"}

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("stripe_webhook_received", event_type=event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)
    elif event_type == "customer.subscription.trial_will_end":
        await _handle_trial_ending(data, db)
    else:
        logger.debug("stripe_webhook_unhandled", event_type=event_type)

    return {"status": "ok", "event_type": event_type}


async def _handle_checkout_completed(checkout_session: dict, db: AsyncSession) -> None:
    """Process successful checkout — assign tier + subscription ID to user."""
    user_id = checkout_session.get("metadata", {}).get("user_id")
    subscription_id = checkout_session.get("subscription")
    customer_id = checkout_session.get("customer")

    if not user_id:
        logger.error("checkout_no_user_id", session_id=checkout_session.get("id"))
        return

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        logger.error("checkout_user_not_found", user_id=user_id)
        return

    # Retrieve subscription from Stripe to get tier + period end
    if subscription_id:
        sub = stripe.Subscription.retrieve(subscription_id)
        tier = _resolve_tier_from_subscription(sub)
        user.tier = UserTier(tier)
        user.stripe_subscription_id = subscription_id
        user.subscription_expires_at = datetime.fromtimestamp(sub["current_period_end"], tz=UTC)

    if customer_id:
        user.stripe_customer_id = customer_id

    db.add(user)
    await db.commit()
    logger.info("checkout_completed", user_id=user.id, tier=user.tier.value)


async def _handle_subscription_updated(subscription: dict, db: AsyncSession) -> None:
    """Handle subscription changes (upgrade, downgrade, renewal)."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("subscription_update_no_user", customer_id=customer_id)
        return

    sub_status = subscription.get("status")
    tier = _resolve_tier_from_subscription(subscription)

    if sub_status in ("active", "trialing"):
        user.tier = UserTier(tier)
        user.stripe_subscription_id = subscription.get("id")
        user.subscription_expires_at = datetime.fromtimestamp(
            subscription["current_period_end"], tz=UTC
        )
    elif sub_status in ("past_due", "unpaid"):
        # Keep current tier but log warning — give grace period
        logger.warning("subscription_past_due", user_id=user.id, status=sub_status)
    elif sub_status == "canceled":
        user.tier = UserTier.FREE
        user.stripe_subscription_id = None
        user.subscription_expires_at = None

    db.add(user)
    await db.commit()
    logger.info(
        "subscription_updated",
        user_id=user.id,
        tier=user.tier.value,
        status=sub_status,
    )


async def _handle_subscription_deleted(subscription: dict, db: AsyncSession) -> None:
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.tier = UserTier.FREE
    user.stripe_subscription_id = None
    user.subscription_expires_at = None
    db.add(user)
    await db.commit()
    logger.info("subscription_deleted", user_id=user.id)


async def _handle_payment_failed(invoice: dict, db: AsyncSession) -> None:
    """Log payment failure for follow-up. Don't downgrade immediately."""
    customer_id = invoice.get("customer")
    logger.warning(
        "payment_failed",
        customer_id=customer_id,
        invoice_id=invoice.get("id"),
        amount_due=invoice.get("amount_due"),
    )


async def _handle_trial_ending(subscription: dict, db: AsyncSession) -> None:
    """Log trial ending event. Could trigger email notification."""
    customer_id = subscription.get("customer")
    trial_end = subscription.get("trial_end")
    logger.info(
        "trial_ending_soon",
        customer_id=customer_id,
        trial_end=trial_end,
    )


# =============================================================================
# Subscription Status Helpers
# =============================================================================


def is_subscription_active(user: User) -> bool:
    """Check if user has an active paid subscription."""
    if user.tier == UserTier.FREE:
        return False
    if user.subscription_expires_at is None:
        return False
    now = datetime.now(UTC)
    # Add 3-day grace period
    return user.subscription_expires_at + timedelta(days=3) > now


def get_subscription_status(user: User) -> str:
    """Return human-readable subscription status."""
    if user.tier == UserTier.FREE:
        return "free"
    if user.subscription_expires_at is None:
        return "free"
    now = datetime.now(UTC)
    if user.subscription_expires_at > now:
        return "active"
    if user.subscription_expires_at + timedelta(days=3) > now:
        return "grace_period"
    return "expired"
