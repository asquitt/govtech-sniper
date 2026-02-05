"""
RFP Sniper - User Models
========================
User authentication and profile data.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel, Column, JSON

if TYPE_CHECKING:
    from app.models.rfp import RFP
    from app.models.proposal import Proposal
    from app.models.knowledge_base import KnowledgeBaseDocument


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
    full_name: Optional[str] = Field(default=None, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
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

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)
    
    # API Usage Tracking
    api_calls_today: int = Field(default=0)
    api_calls_limit: int = Field(default=100)  # Based on tier
    last_api_reset: datetime = Field(default_factory=datetime.utcnow)

    # MFA
    mfa_enabled: bool = Field(default=False)
    mfa_secret: Optional[str] = Field(default=None, max_length=255)
    mfa_enabled_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    profile: Optional["UserProfile"] = Relationship(back_populates="user")
    rfps: List["RFP"] = Relationship(back_populates="user")
    proposals: List["Proposal"] = Relationship(back_populates="user")
    documents: List["KnowledgeBaseDocument"] = Relationship(back_populates="user")


# =============================================================================
# User Profile Model (Qualification Criteria for Filtering)
# =============================================================================

class UserProfileBase(SQLModel):
    """User profile for RFP qualification filtering."""
    
    # NAICS codes the user can bid on (e.g., ["541512", "541511"])
    naics_codes: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Security clearance level
    clearance_level: ClearanceLevel = Field(default=ClearanceLevel.NONE)
    
    # Set-aside eligibility (e.g., ["8a", "WOSB", "SDVOSB", "HUBZone"])
    set_aside_types: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Geographic preferences (state abbreviations)
    preferred_states: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Contract value preferences
    min_contract_value: Optional[int] = Field(default=None)
    max_contract_value: Optional[int] = Field(default=None)
    
    # Keywords to always match/exclude
    include_keywords: List[str] = Field(default=[], sa_column=Column(JSON))
    exclude_keywords: List[str] = Field(default=[], sa_column=Column(JSON))


class UserProfile(UserProfileBase, table=True):
    """
    Extended user profile storing qualification criteria.
    Used by the "Killer Filter" to determine RFP eligibility.
    """
    __tablename__ = "user_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    user: Optional[User] = Relationship(back_populates="profile")
