"""
RFP Sniper - Opportunity Contact Models
=======================================
Buyer and stakeholder contacts for opportunities.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, Text


class OpportunityContact(SQLModel, table=True):
    """
    Contact record associated with an opportunity.
    """
    __tablename__ = "opportunity_contacts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: Optional[int] = Field(default=None, foreign_key="rfps.id", index=True)

    name: str = Field(max_length=255)
    role: Optional[str] = Field(default=None, max_length=255)
    organization: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
