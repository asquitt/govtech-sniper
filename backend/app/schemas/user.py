"""
RFP Sniper - User Schemas
=========================
Request/Response models for user endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import ClearanceLevel, UserTier


# =============================================================================
# User Schemas
# =============================================================================

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)


class UserRead(BaseModel):
    """Schema for reading user data (excludes password)."""
    id: int
    email: EmailStr
    full_name: Optional[str]
    company_name: Optional[str]
    is_active: bool
    tier: UserTier
    api_calls_today: int
    api_calls_limit: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user data."""
    full_name: Optional[str] = Field(default=None, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)


# =============================================================================
# User Profile Schemas
# =============================================================================

class UserProfileCreate(BaseModel):
    """Schema for creating user profile."""
    naics_codes: List[str] = Field(default=[])
    clearance_level: ClearanceLevel = Field(default=ClearanceLevel.NONE)
    set_aside_types: List[str] = Field(default=[])
    preferred_states: List[str] = Field(default=[])
    min_contract_value: Optional[int] = None
    max_contract_value: Optional[int] = None
    include_keywords: List[str] = Field(default=[])
    exclude_keywords: List[str] = Field(default=[])


class UserProfileRead(BaseModel):
    """Schema for reading user profile."""
    id: int
    user_id: int
    naics_codes: List[str]
    clearance_level: ClearanceLevel
    set_aside_types: List[str]
    preferred_states: List[str]
    min_contract_value: Optional[int]
    max_contract_value: Optional[int]
    include_keywords: List[str]
    exclude_keywords: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    naics_codes: Optional[List[str]] = None
    clearance_level: Optional[ClearanceLevel] = None
    set_aside_types: Optional[List[str]] = None
    preferred_states: Optional[List[str]] = None
    min_contract_value: Optional[int] = None
    max_contract_value: Optional[int] = None
    include_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None


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

