"""
RFP Sniper - API Dependencies
==============================
FastAPI dependencies for authentication, database sessions, and rate limiting.
"""

from datetime import datetime
from typing import Annotated, Any

import pyotp
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import get_session
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User, UserProfile, UserTier
from app.services.auth_service import UserAuth, decode_token

logger = structlog.get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: AsyncSession = Depends(get_session),
) -> UserAuth | None:
    """
    Get current user if authenticated, None otherwise.
    Use this for endpoints that work with or without auth.
    """
    if not credentials:
        return None

    token_data = decode_token(credentials.credentials)
    if not token_data:
        return None

    # Fetch user from database
    result = await session.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        return None

    return UserAuth(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        tier=user.tier.value,
        is_active=user.is_active,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: AsyncSession = Depends(get_session),
) -> UserAuth:
    """
    Get current authenticated user.
    Raises 401 if not authenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise credentials_exception

    # Fetch user from database
    result = await session.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return UserAuth(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        tier=user.tier.value,
        is_active=user.is_active,
    )


async def get_current_user_with_profile(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> tuple[UserAuth, UserProfile | None]:
    """
    Get current user and their profile.
    """
    result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    return current_user, profile


# =============================================================================
# Rate Limiting Dependencies
# =============================================================================


class RedisRateLimiter:
    """
    Redis-backed rate limiter using INCR + EXPIRE pattern.
    Supports horizontal scaling — all instances share state via Redis.
    Fails open if Redis is unavailable (availability over strictness).
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self._redis_url, decode_responses=True, socket_connect_timeout=1
            )
        return self._redis

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        try:
            r = await self._get_redis()
            redis_key = f"rate:{key}"
            current = await r.incr(redis_key)
            if current == 1:
                await r.expire(redis_key, window_seconds)
            remaining = max(0, max_requests - current)
            return current <= max_requests, remaining
        except Exception:
            # Fail open — allow request if Redis is down
            logger.warning("rate_limiter_redis_unavailable", key=key)
            return True, max_requests


# Global rate limiter instance
rate_limiter = RedisRateLimiter(settings.redis_url)


async def check_rate_limit(
    request: Request,
    current_user: UserAuth | None = Depends(get_current_user_optional),
) -> None:
    """
    Check rate limit for the current request.

    Limits vary by user tier:
    - Free: 100 requests/hour
    - Starter: 500 requests/hour
    - Professional: 2000 requests/hour
    - Enterprise: 10000 requests/hour
    """
    # Determine rate limit based on tier
    tier_limits = {
        "free": 100,
        "starter": 500,
        "professional": 2000,
        "enterprise": 10000,
    }

    if current_user:
        key = f"user:{current_user.id}"
        max_requests = tier_limits.get(current_user.tier, 100)
    else:
        # Rate limit by IP + path for unauthenticated requests so one high-churn
        # endpoint (like auth during E2E) doesn't starve other anonymous traffic.
        client_ip = request.client.host if request.client else "unknown"
        key = f"ip:{client_ip}:{request.url.path}"
        max_requests = 200 if settings.debug else 50

    is_allowed, remaining = await rate_limiter.is_allowed(
        key=key,
        max_requests=max_requests,
        window_seconds=3600,  # 1 hour
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "3600"},
        )


# =============================================================================
# User ID Resolution
# =============================================================================


def resolve_user_id(
    user_id: int | None,
    current_user: UserAuth | None,
) -> int:
    """
    Resolve a user ID from either an explicit parameter or the auth token.

    - If both are provided, they must match.
    - If neither is provided, raise 401.
    """
    if user_id is None and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required or user_id must be provided",
        )

    if user_id is not None and current_user and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id does not match authenticated user",
        )

    return user_id if user_id is not None else current_user.id


# =============================================================================
# Organization Role Lookup (for Policy Engine)
# =============================================================================

# Maps OrgRole → policy engine role string
_ORG_ROLE_TO_POLICY: dict[str, str] = {
    OrgRole.OWNER.value: "owner",
    OrgRole.ADMIN.value: "admin",
    OrgRole.MEMBER.value: "editor",
    OrgRole.VIEWER.value: "viewer",
}

STEP_UP_REQUIRED_HEADER = "X-Step-Up-Required"
STEP_UP_CODE_HEADER = "X-Step-Up-Code"
STEP_UP_FALLBACK_HEADERS = ("X-MFA-Code",)

_ORG_SECURITY_DEFAULTS: dict[str, bool] = {
    "require_step_up_for_sensitive_exports": True,
    "require_step_up_for_sensitive_shares": True,
    "apply_cui_watermark_to_sensitive_exports": True,
    "apply_cui_redaction_to_sensitive_exports": False,
}


def get_org_security_policy_from_settings(settings_payload: Any) -> dict[str, bool]:
    """Resolve org security policy flags from organization settings JSON."""
    settings_obj = settings_payload if isinstance(settings_payload, dict) else {}
    return {
        key: bool(settings_obj.get(key, default)) for key, default in _ORG_SECURITY_DEFAULTS.items()
    }


def merge_org_security_policy_settings(
    current_settings: Any,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge org security policy updates into settings JSON payload."""
    settings_obj: dict[str, Any] = (
        dict(current_settings) if isinstance(current_settings, dict) else {}
    )
    security_policy = get_org_security_policy_from_settings(settings_obj)
    for key in _ORG_SECURITY_DEFAULTS:
        if key in updates and updates[key] is not None:
            security_policy[key] = bool(updates[key])
    settings_obj.update(security_policy)
    return settings_obj


def get_step_up_code(
    request: Request | None = None,
    explicit_code: str | None = None,
) -> str | None:
    """Extract step-up code from explicit payload value or request headers."""
    if explicit_code and explicit_code.strip():
        return explicit_code.strip()
    if not request:
        return None
    header_code = request.headers.get(STEP_UP_CODE_HEADER)
    if header_code and header_code.strip():
        return header_code.strip()
    for header_name in STEP_UP_FALLBACK_HEADERS:
        fallback = request.headers.get(header_name)
        if fallback and fallback.strip():
            return fallback.strip()
    return None


async def verify_step_up_code(
    user_id: int,
    session: AsyncSession,
    code: str | None,
) -> bool:
    """Verify MFA TOTP code for step-up authorization checks."""
    if not code:
        return False
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.mfa_enabled or not user.mfa_secret:
        return False
    totp = pyotp.TOTP(user.mfa_secret)
    return bool(totp.verify(code, valid_window=1))


async def get_user_org_security_policy(
    user_id: int,
    session: AsyncSession,
) -> dict[str, bool]:
    """Load effective org security policy flags for the current user."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.organization_id:
        return dict(_ORG_SECURITY_DEFAULTS)
    organization = (
        await session.execute(select(Organization).where(Organization.id == user.organization_id))
    ).scalar_one_or_none()
    if not organization:
        return dict(_ORG_SECURITY_DEFAULTS)
    return get_org_security_policy_from_settings(organization.settings)


async def get_user_policy_role(user_id: int, session: AsyncSession) -> str:
    """
    Resolve user's organization role to a policy engine role string.

    Returns "editor" as default if user has no org membership (solo users).
    """
    result = await session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return "editor"  # Solo users default to editor-level access
    return _ORG_ROLE_TO_POLICY.get(member.role.value, "viewer")


# =============================================================================
# Feature Gates
# =============================================================================

TIER_LEVELS: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "professional": 2,
    "enterprise": 3,
}

FEATURE_GATES: dict[str, UserTier] = {
    "deep_read": UserTier.STARTER,
    "ai_draft": UserTier.STARTER,
    "export_docx": UserTier.PROFESSIONAL,
    "export_pdf": UserTier.PROFESSIONAL,
    "color_reviews": UserTier.PROFESSIONAL,
    "salesforce_sync": UserTier.ENTERPRISE,
    "semantic_search": UserTier.PROFESSIONAL,
    "custom_workflows": UserTier.ENTERPRISE,
}


def require_feature(feature_name: str):
    """
    Dependency factory that checks if the user's tier grants access to a feature.

    Usage:
        @router.get("/deep-read", dependencies=[Depends(require_feature("deep_read"))])
    """
    min_tier = FEATURE_GATES.get(feature_name)
    if min_tier is None:
        raise ValueError(f"Unknown feature: {feature_name}")

    async def feature_checker(current_user: UserAuth = Depends(get_current_user)):
        user_level = TIER_LEVELS.get(current_user.tier, 0)
        required_level = TIER_LEVELS.get(min_tier.value, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' requires {min_tier.value} tier or higher. Current tier: {current_user.tier}",
            )

        return current_user

    return feature_checker


# =============================================================================
# Tier-Based Access Control
# =============================================================================


def require_tier(minimum_tier: str):
    """
    Dependency factory to require minimum subscription tier.

    Usage:
        @router.get("/premium-feature", dependencies=[Depends(require_tier("professional"))])
    """

    async def tier_checker(current_user: UserAuth = Depends(get_current_user)):
        user_level = TIER_LEVELS.get(current_user.tier, 0)
        required_level = TIER_LEVELS.get(minimum_tier, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {minimum_tier} tier or higher",
            )

        return current_user

    return tier_checker


# =============================================================================
# API Usage Tracking
# =============================================================================


async def track_api_usage(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserAuth:
    """
    Track API usage for the current user.
    Updates daily counters in the database.
    """
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if user:
        # Check if we need to reset daily counter
        if user.last_api_reset.date() < datetime.utcnow().date():
            user.api_calls_today = 0
            user.last_api_reset = datetime.utcnow()

        # Check if user has exceeded daily limit
        if user.api_calls_today >= user.api_calls_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily API limit of {user.api_calls_limit} calls exceeded",
            )

        # Increment counter
        user.api_calls_today += 1
        await session.commit()

    return current_user
