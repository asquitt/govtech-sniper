"""
RFP Sniper - Outline Schemas
==============================
Request/Response models for outline endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.outline import OutlineStatus


class OutlineSectionRead(BaseModel):
    """Schema for reading an outline section."""

    id: int
    outline_id: int
    parent_id: int | None
    title: str
    description: str | None
    mapped_requirement_ids: list[str]
    display_order: int
    estimated_pages: float | None
    created_at: datetime
    updated_at: datetime
    children: list["OutlineSectionRead"] = []

    model_config = {"from_attributes": True}


class OutlineSectionCreate(BaseModel):
    """Schema for manually adding an outline section."""

    title: str = Field(max_length=255)
    parent_id: int | None = None
    description: str | None = None
    mapped_requirement_ids: list[str] = []
    display_order: int = 0
    estimated_pages: float | None = None


class OutlineSectionUpdate(BaseModel):
    """Schema for updating an outline section."""

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    mapped_requirement_ids: list[str] | None = None
    display_order: int | None = None
    estimated_pages: float | None = None


class OutlineRead(BaseModel):
    """Schema for reading a proposal outline with nested sections."""

    id: int
    proposal_id: int
    status: OutlineStatus
    created_at: datetime
    updated_at: datetime
    sections: list[OutlineSectionRead]

    model_config = {"from_attributes": True}


class OutlineReorderItem(BaseModel):
    """Single item in a reorder request."""

    section_id: int
    parent_id: int | None = None
    display_order: int


class OutlineReorderRequest(BaseModel):
    """Bulk reorder request."""

    items: list[OutlineReorderItem]
