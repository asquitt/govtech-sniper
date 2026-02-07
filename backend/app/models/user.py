"""
RFP Sniper - User Models
========================
User authentication and profile data.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlmodel import JSON, Column, Field, Relationship, SQLModel, Text

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBaseDocument
    from app.models.proposal import Proposal
    from app.models.rfp import RFP


class UserTier(str, Enum):
    """Subscription tier for API usage limits."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class ClearanceLevel(str, Enum):
    """Security clearance levels for filtering RFPs."""

    NONE = "none"
    PUBLIC_TRUST = "public_trust"
    SECRET = "secret"
    TOP_SECRET = "top_secret"
    TS_SCI = "ts_sci"


# =============================================================================
# User Model
# =============================================================================


class UserBase(SQLModel):
    """Base user fields shared across create/update/read."""

    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    tier: UserTier = Field(default=UserTier.FREE)


class User(UserBase, table=True):
    """
    User account for authentication and authorization.

    Relationships:
    - One-to-One with UserProfile
    - One-to-Many with RFPs (saved/tracked)
    - One-to-Many with Proposals
    - One-to-Many with KnowledgeBaseDocuments
    """

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)

    # API Usage Tracking
    api_calls_today: int = Field(default=0)
    api_calls_limit: int = Field(default=100)  # Based on tier
    last_api_reset: datetime = Field(default_factory=datetime.utcnow)

    # Subscription / Billing
    subscription_expires_at: datetime | None = Field(default=None)
    stripe_customer_id: str | None = Field(default=None, max_length=255)
    stripe_subscription_id: str | None = Field(default=None, max_length=255)

    # Organization (multi-tenant)
    organization_id: int | None = Field(default=None, foreign_key="organizations.id", index=True)

    # MFA
    mfa_enabled: bool = Field(default=False)
    mfa_secret: str | None = Field(default=None, max_length=255)
    mfa_enabled_at: datetime | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    profile: Optional["UserProfile"] = Relationship(back_populates="user")
    rfps: list["RFP"] = Relationship(back_populates="user")
    proposals: list["Proposal"] = Relationship(back_populates="user")
    documents: list["KnowledgeBaseDocument"] = Relationship(back_populates="user")


# =============================================================================
# User Profile Model (Qualification Criteria for Filtering)
# =============================================================================


class CompanySize(str, Enum):
    """Company size classification."""

    SMALL = "small"
    MIDSIZE = "midsize"
    LARGE = "large"


class UserProfileBase(SQLModel):
    """User profile for RFP qualification filtering."""

    # NAICS codes the user can bid on (e.g., ["541512", "541511"])
    naics_codes: list[str] = Field(default=[], sa_column=Column(JSON))

    # Security clearance level
    clearance_level: ClearanceLevel = Field(default=ClearanceLevel.NONE)

    # Set-aside eligibility (e.g., ["8a", "WOSB", "SDVOSB", "HUBZone"])
    set_aside_types: list[str] = Field(default=[], sa_column=Column(JSON))

    # Geographic preferences (state abbreviations)
    preferred_states: list[str] = Field(default=[], sa_column=Column(JSON))

    # Contract value preferences
    min_contract_value: int | None = Field(default=None)
    max_contract_value: int | None = Field(default=None)

    # Keywords to always match/exclude
    include_keywords: list[str] = Field(default=[], sa_column=Column(JSON))
    exclude_keywords: list[str] = Field(default=[], sa_column=Column(JSON))

    # Company capability fields (for AI matching + bid/no-bid)
    company_size: CompanySize | None = Field(default=None)
    company_duns: str | None = Field(default=None, max_length=20)
    cage_code: str | None = Field(default=None, max_length=10)
    certifications: list[str] = Field(default=[], sa_column=Column(JSON))
    past_performance_summary: str | None = Field(default=None, sa_column=Column(Text))
    core_competencies: list[str] = Field(default=[], sa_column=Column(JSON))
    years_in_business: int | None = Field(default=None)
    annual_revenue: int | None = Field(default=None)
    employee_count: int | None = Field(default=None)
    enabled_sources: list[str] = Field(default=["sam_gov"], sa_column=Column(JSON))


class UserProfile(UserProfileBase, table=True):
    """
    Extended user profile storing qualification criteria.
    Used by the "Killer Filter" to determine RFP eligibility.
    """

    __tablename__ = "user_profiles"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    user: User | None = Relationship(back_populates="profile")
