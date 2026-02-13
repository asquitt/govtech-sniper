"""
Template database model and Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel
from sqlmodel import JSON, Column, Field, SQLModel, Text

# =============================================================================
# Template Models
# =============================================================================


class ProposalTemplate(SQLModel, table=True):
    """
    Pre-built response templates for common proposal requirements.
    """

    __tablename__ = "proposal_templates"

    id: int | None = Field(default=None, primary_key=True)

    # Template identification
    name: str = Field(max_length=255, index=True)
    category: str = Field(max_length=100, index=True)  # "Past Performance", "Technical", etc.
    subcategory: str | None = Field(default=None, max_length=100)

    # Template content
    description: str = Field(max_length=1000)
    template_text: str = Field(sa_column=Column(Text))

    # Placeholders that need to be filled
    # Format: {"company_name": "Your company name", "project_name": "Relevant project"}
    placeholders: dict = Field(default={}, sa_column=Column(JSON))

    # Metadata
    is_system: bool = Field(default=True)  # System templates vs user-created
    user_id: int | None = Field(default=None, foreign_key="users.id")  # For user templates
    usage_count: int = Field(default=0)

    # Keywords for matching
    keywords: list[str] = Field(default=[], sa_column=Column(JSON))

    # Marketplace fields
    is_public: bool = Field(default=False, index=True)
    rating_sum: int = Field(default=0)
    rating_count: int = Field(default=0)
    forked_from_id: int | None = Field(default=None, foreign_key="proposal_templates.id")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class TemplateCreate(BaseModel):
    """Create a new template."""

    name: str
    category: str
    subcategory: str | None = None
    description: str
    template_text: str
    placeholders: dict = {}
    keywords: list[str] = []


class TemplateUpdate(BaseModel):
    """Update a template."""

    name: str | None = None
    category: str | None = None
    subcategory: str | None = None
    description: str | None = None
    template_text: str | None = None
    placeholders: dict | None = None
    keywords: list[str] | None = None


class TemplateResponse(BaseModel):
    """Template response."""

    id: int
    name: str
    category: str
    subcategory: str | None
    description: str
    template_text: str
    placeholders: dict
    keywords: list[str]
    is_system: bool
    is_public: bool
    rating_sum: int
    rating_count: int
    forked_from_id: int | None
    user_id: int | None
    usage_count: int
    created_at: datetime
    updated_at: datetime
