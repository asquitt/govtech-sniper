"""
RFP Sniper - User Schemas
=========================
Request/Response models for user endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import ClearanceLevel, UserTier

# =============================================================================
# User Schemas
# =============================================================================


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)


class UserRead(BaseModel):
    """Schema for reading user data (excludes password)."""

    id: int
    email: EmailStr
    full_name: str | None
    company_name: str | None
    is_active: bool
    tier: UserTier
    api_calls_today: int
    api_calls_limit: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user data."""

    full_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=100)


# =============================================================================
# User Profile Schemas
# =============================================================================


class UserProfileCreate(BaseModel):
    """Schema for creating user profile."""

    naics_codes: list[str] = Field(default=[])
    clearance_level: ClearanceLevel = Field(default=ClearanceLevel.NONE)
    set_aside_types: list[str] = Field(default=[])
    preferred_states: list[str] = Field(default=[])
    min_contract_value: int | None = None
    max_contract_value: int | None = None
    include_keywords: list[str] = Field(default=[])
    exclude_keywords: list[str] = Field(default=[])


class UserProfileRead(BaseModel):
    """Schema for reading user profile."""

    id: int
    user_id: int
    naics_codes: list[str]
    clearance_level: ClearanceLevel
    set_aside_types: list[str]
    preferred_states: list[str]
    min_contract_value: int | None
    max_contract_value: int | None
    include_keywords: list[str]
    exclude_keywords: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    naics_codes: list[str] | None = None
    clearance_level: ClearanceLevel | None = None
    set_aside_types: list[str] | None = None
    preferred_states: list[str] | None = None
    min_contract_value: int | None = None
    max_contract_value: int | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None


# =============================================================================
# Auth Schemas
# =============================================================================


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: datetime
    iat: datetime
