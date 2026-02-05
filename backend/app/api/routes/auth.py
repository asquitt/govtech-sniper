"""
RFP Sniper - Authentication Routes
===================================
User registration, login, and token management.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel, EmailStr, Field
import structlog

from app.database import get_session
from app.models.user import User, UserProfile, UserTier, ClearanceLevel
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_token_pair,
    decode_refresh_token,
    validate_password_strength,
    TokenPair,
    UserAuth,
)
from app.api.deps import get_current_user
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    full_name: str = Field(..., min_length=2, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    """User information response."""
    id: int
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    tier: str
    is_active: bool
    api_calls_today: int
    api_calls_limit: int
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    """Profile update request."""
    naics_codes: Optional[list[str]] = None
    clearance_level: Optional[ClearanceLevel] = None
    set_aside_types: Optional[list[str]] = None
    preferred_states: Optional[list[str]] = None
    min_contract_value: Optional[int] = None
    max_contract_value: Optional[int] = None
    include_keywords: Optional[list[str]] = None
    exclude_keywords: Optional[list[str]] = None


# =============================================================================
# Registration & Login
# =============================================================================

@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """
    Register a new user account.

    Returns JWT tokens upon successful registration.
    """
    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == request.email.lower())
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password strength
    is_valid, error_msg = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Create user
    user = User(
        email=request.email.lower(),
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        company_name=request.company_name,
        tier=UserTier.FREE,
        is_active=True,
        api_calls_limit=100,  # Free tier limit
    )
    session.add(user)
    await session.flush()  # Get the user ID

    # Create empty profile
    profile = UserProfile(
        user_id=user.id,
        naics_codes=[],
        clearance_level=ClearanceLevel.NONE,
        set_aside_types=[],
        preferred_states=[],
    )
    session.add(profile)
    await log_audit_event(
        session,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        action="user.registered",
        metadata={"email": user.email},
    )

    await session.commit()
    await session.refresh(user)

    logger.info("New user registered", user_id=user.id, email=user.email)

    # Generate tokens
    return create_token_pair(user.id, user.email, user.tier.value)


@router.post("/login", response_model=TokenPair)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """
    Login with email and password.

    Returns JWT tokens upon successful authentication.
    """
    # Find user
    result = await session.execute(
        select(User).where(User.email == request.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    logger.info("User logged in", user_id=user.id, email=user.email)
    await log_audit_event(
        session,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        action="user.login",
        metadata={"email": user.email},
    )
    await session.commit()

    # Generate tokens
    return create_token_pair(user.id, user.email, user.tier.value)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """
    Refresh access token using refresh token.
    """
    user_id = decode_refresh_token(request.refresh_token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Fetch user
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    logger.info("Token refreshed", user_id=user.id)

    # Generate new tokens
    return create_token_pair(user.id, user.email, user.tier.value)


@router.post("/logout")
async def logout(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """
    Logout current user.

    Note: JWT tokens are stateless, so we can't truly invalidate them.
    The client should discard the tokens.
    For production, consider token blacklisting with Redis.
    """
    logger.info("User logged out", user_id=current_user.id)

    return {
        "message": "Successfully logged out",
        "note": "Please discard your tokens on the client side",
    }


# =============================================================================
# User Management
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Get current user's information.
    """
    result = await session.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        tier=user.tier.value,
        is_active=user.is_active,
        api_calls_today=user.api_calls_today,
        api_calls_limit=user.api_calls_limit,
        created_at=user.created_at,
    )


@router.put("/me")
async def update_current_user(
    full_name: Optional[str] = None,
    company_name: Optional[str] = None,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Update current user's basic information.
    """
    result = await session.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if full_name is not None:
        user.full_name = full_name
    if company_name is not None:
        user.company_name = company_name

    user.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        tier=user.tier.value,
        is_active=user.is_active,
        api_calls_today=user.api_calls_today,
        api_calls_limit=user.api_calls_limit,
        created_at=user.created_at,
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Change current user's password.
    """
    result = await session.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    is_valid, error_msg = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Update password
    user.hashed_password = hash_password(request.new_password)
    user.updated_at = datetime.utcnow()
    await session.commit()

    logger.info("Password changed", user_id=user.id)

    return {"message": "Password changed successfully"}


# =============================================================================
# Profile Management
# =============================================================================

@router.get("/profile")
async def get_profile(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get current user's qualification profile.
    """
    result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        # Create default profile if missing
        profile = UserProfile(
            user_id=current_user.id,
            naics_codes=[],
            clearance_level=ClearanceLevel.NONE,
            set_aside_types=[],
            preferred_states=[],
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

    return {
        "id": profile.id,
        "naics_codes": profile.naics_codes,
        "clearance_level": profile.clearance_level.value,
        "set_aside_types": profile.set_aside_types,
        "preferred_states": profile.preferred_states,
        "min_contract_value": profile.min_contract_value,
        "max_contract_value": profile.max_contract_value,
        "include_keywords": profile.include_keywords,
        "exclude_keywords": profile.exclude_keywords,
        "updated_at": profile.updated_at,
    }


@router.put("/profile")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Update current user's qualification profile.
    """
    result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)

    # Update fields if provided
    if request.naics_codes is not None:
        profile.naics_codes = request.naics_codes
    if request.clearance_level is not None:
        profile.clearance_level = request.clearance_level
    if request.set_aside_types is not None:
        profile.set_aside_types = request.set_aside_types
    if request.preferred_states is not None:
        profile.preferred_states = request.preferred_states
    if request.min_contract_value is not None:
        profile.min_contract_value = request.min_contract_value
    if request.max_contract_value is not None:
        profile.max_contract_value = request.max_contract_value
    if request.include_keywords is not None:
        profile.include_keywords = request.include_keywords
    if request.exclude_keywords is not None:
        profile.exclude_keywords = request.exclude_keywords

    profile.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(profile)

    logger.info("Profile updated", user_id=current_user.id)

    return {
        "message": "Profile updated successfully",
        "profile": {
            "naics_codes": profile.naics_codes,
            "clearance_level": profile.clearance_level.value,
            "set_aside_types": profile.set_aside_types,
            "preferred_states": profile.preferred_states,
            "min_contract_value": profile.min_contract_value,
            "max_contract_value": profile.max_contract_value,
            "include_keywords": profile.include_keywords,
            "exclude_keywords": profile.exclude_keywords,
        },
    }
