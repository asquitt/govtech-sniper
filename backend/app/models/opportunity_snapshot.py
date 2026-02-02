"""
RFP Sniper - SAM.gov Opportunity Snapshots
===========================================
Persist raw opportunity payloads to enable change tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlmodel import SQLModel, Field, Column, JSON


class SAMOpportunitySnapshot(SQLModel, table=True):
    """Raw SAM.gov opportunity snapshot for versioning/diffing."""

    __tablename__ = "sam_opportunity_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    notice_id: str = Field(max_length=100, index=True)
    solicitation_number: Optional[str] = Field(default=None, max_length=100, index=True)
    rfp_id: Optional[int] = Field(default=None, foreign_key="rfps.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    fetched_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    posted_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    raw_hash: str = Field(max_length=64, index=True)
    raw_payload: Dict[str, Any] = Field(sa_column=Column(JSON))
