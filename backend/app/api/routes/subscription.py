"""
RFP Sniper - Subscription Routes
==================================
Endpoints for plan information, usage tracking, and Stripe integration.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.services.auth_service import UserAuth
from app.services.subscription_service import (
    CheckoutSessionResponse,
    PlanDefinition,
    UsageStats,
    create_checkout_session,
    create_customer_portal_session,
    get_all_plans,
    get_plan_details,
    get_subscription_status,
    get_usage_stats,
    handle_webhook,
)

router = APIRouter(prefix="/subscription", tags=["Subscription"])


@router.get("/plans", response_model=list[PlanDefinition])
async def list_plans():
    """List all available subscription plans with features and pricing."""
    return get_all_plans()


@router.get("/current", response_model=PlanDefinition)
async def current_plan(
    current_user: UserAuth = Depends(get_current_user),
):
    """Get the current user's subscription plan details."""
    plan = get_plan_details(current_user.tier)
    if plan is None:
        plan = get_plan_details("free")
    return plan


@router.get("/usage", response_model=UsageStats)
async def usage(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get feature usage counters for the current user."""
    return await get_usage_stats(current_user.id, session)


@router.get("/status")
async def subscription_status(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current subscription status (free, active, grace_period, expired)."""
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    return {
        "tier": user.tier.value,
        "status": get_subscription_status(user),
        "expires_at": (
            user.subscription_expires_at.isoformat() if user.subscription_expires_at else None
        ),
        "has_stripe_customer": bool(user.stripe_customer_id),
        "has_subscription": bool(user.stripe_subscription_id),
    }


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def checkout(
    tier: str = "starter",
    annual: bool = False,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a Stripe checkout session to upgrade the user's plan."""
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    return await create_checkout_session(user, tier, annual, session)


@router.post("/portal")
async def customer_portal(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a Stripe Customer Portal session for billing management."""
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    portal_url = await create_customer_portal_session(user)
    return {"portal_url": portal_url}


@router.post("/webhook")
async def webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Handle incoming Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    return await handle_webhook(payload, sig_header, session)
