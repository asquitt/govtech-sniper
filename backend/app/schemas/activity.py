"""
RFP Sniper - Activity Feed Schemas
=====================================
Response models for activity feed entries.
"""

from datetime import datetime

from pydantic import BaseModel


class ActivityFeedRead(BaseModel):
    id: int
    proposal_id: int
    user_id: int
    activity_type: str
    summary: str
    section_id: int | None = None
    metadata_json: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
