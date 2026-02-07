"""
RFP Sniper - Outline Schemas
==============================
Request/Response models for outline endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.outline import OutlineStatus


class OutlineSectionRead(BaseModel):
    """Schema for reading an outline section."""
    id: int
    outline_id: int
    parent_id: Optional[int]
    title: str
    description: Optional[str]
    mapped_requirement_ids: List[str]
    display_order: int
    estimated_pages: Optional[float]
    created_at: datetime
    updated_at: datetime
    children: List["OutlineSectionRead"] = []

    model_config = {"from_attributes": True}


class OutlineSectionCreate(BaseModel):
    """Schema for manually adding an outline section."""
    title: str = Field(max_length=255)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    mapped_requirement_ids: List[str] = []
    display_order: int = 0
    estimated_pages: Optional[float] = None


class OutlineSectionUpdate(BaseModel):
    """Schema for updating an outline section."""
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    mapped_requirement_ids: Optional[List[str]] = None
    display_order: Optional[int] = None
    estimated_pages: Optional[float] = None


class OutlineRead(BaseModel):
    """Schema for reading a proposal outline with nested sections."""
    id: int
    proposal_id: int
    status: OutlineStatus
    created_at: datetime
    updated_at: datetime
    sections: List[OutlineSectionRead]

    model_config = {"from_attributes": True}


class OutlineReorderItem(BaseModel):
    """Single item in a reorder request."""
    section_id: int
    parent_id: Optional[int] = None
    display_order: int


class OutlineReorderRequest(BaseModel):
    """Bulk reorder request."""
    items: List[OutlineReorderItem]
