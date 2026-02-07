"""
RFP Sniper - Award Intelligence Models
======================================
Award and contract intelligence records.
"""

from datetime import datetime

from sqlmodel import Column, Field, SQLModel, Text


class AwardRecord(SQLModel, table=True):
    """
    Award intelligence record tied to an opportunity or standalone.
    """

    __tablename__ = "award_records"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)

    notice_id: str | None = Field(default=None, max_length=128)
    solicitation_number: str | None = Field(default=None, max_length=100)
    contract_number: str | None = Field(default=None, max_length=128)
    agency: str | None = Field(default=None, max_length=255)

    awardee_name: str = Field(max_length=255)
    award_amount: int | None = None
    award_date: datetime | None = None
    contract_vehicle: str | None = Field(default=None, max_length=255)
    naics_code: str | None = Field(default=None, max_length=10)
    set_aside: str | None = Field(default=None, max_length=100)
    place_of_performance: str | None = Field(default=None, max_length=255)

    description: str | None = Field(default=None, sa_column=Column(Text))
    source_url: str | None = Field(default=None, max_length=1000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
