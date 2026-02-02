"""
RFP Sniper - API Dependencies
==============================
FastAPI dependencies for authentication, database sessions, and rate limiting.
"""

from datetime import datetime
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import structlog

from app.database import get_session
from app.models.user import User, UserProfile
from app.services.auth_service import decode_token, TokenData, UserAuth

logger = structlog.get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    session: AsyncSession = Depends(get_session),
) -> Optional[UserAuth]:
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
    result = await session.execute(
        select(User).where(User.id == token_data.user_id)
    )
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
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
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
    result = await session.execute(
        select(User).where(User.id == token_data.user_id)
    )
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
) -> tuple[UserAuth, Optional[UserProfile]]:
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

class RateLimiter:
    """
    Simple in-memory rate limiter.
    For production, use Redis-based rate limiting.
    """

    def __init__(self):
        self.requests: dict[str, list[datetime]] = {}

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (user_id, IP, etc.)
            max_requests: Maximum requests in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = datetime.utcnow()
        window_start = now.timestamp() - window_seconds

        # Get existing requests for this key
        if key not in self.requests:
            self.requests[key] = []

        # Filter to only requests within window
        self.requests[key] = [
            req for req in self.requests[key]
            if req.timestamp() > window_start
        ]

        # Check if under limit
        current_count = len(self.requests[key])
        remaining = max_requests - current_count

        if current_count >= max_requests:
            return False, 0

        # Add this request
        self.requests[key].append(now)

        return True, remaining - 1


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    request: Request,
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
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
        # Rate limit by IP for unauthenticated requests
        key = f"ip:{request.client.host if request.client else 'unknown'}"
        max_requests = 50  # Very limited for unauthenticated

    is_allowed, remaining = rate_limiter.is_allowed(
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
    user_id: Optional[int],
    current_user: Optional[UserAuth],
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
# Tier-Based Access Control
# =============================================================================

def require_tier(minimum_tier: str):
    """
    Dependency factory to require minimum subscription tier.

    Usage:
        @router.get("/premium-feature", dependencies=[Depends(require_tier("professional"))])
    """
    tier_levels = {
        "free": 0,
        "starter": 1,
        "professional": 2,
        "enterprise": 3,
    }

    async def tier_checker(current_user: UserAuth = Depends(get_current_user)):
        user_level = tier_levels.get(current_user.tier, 0)
        required_level = tier_levels.get(minimum_tier, 0)

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
    result = await session.execute(
        select(User).where(User.id == current_user.id)
    )
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
