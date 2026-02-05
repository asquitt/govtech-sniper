"""
RFP Sniper - Award Intelligence Models
======================================
Award and contract intelligence records.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, Text


class AwardRecord(SQLModel, table=True):
    """
    Award intelligence record tied to an opportunity or standalone.
    """
    __tablename__ = "award_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: Optional[int] = Field(default=None, foreign_key="rfps.id", index=True)

    notice_id: Optional[str] = Field(default=None, max_length=128)
    solicitation_number: Optional[str] = Field(default=None, max_length=100)
    contract_number: Optional[str] = Field(default=None, max_length=128)
    agency: Optional[str] = Field(default=None, max_length=255)

    awardee_name: str = Field(max_length=255)
    award_amount: Optional[int] = None
    award_date: Optional[datetime] = None
    contract_vehicle: Optional[str] = Field(default=None, max_length=255)
    naics_code: Optional[str] = Field(default=None, max_length=10)
    set_aside: Optional[str] = Field(default=None, max_length=100)
    place_of_performance: Optional[str] = Field(default=None, max_length=255)

    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    source_url: Optional[str] = Field(default=None, max_length=1000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
