"""
RFP Sniper - Opportunity Contact Models
=======================================
Buyer and stakeholder contacts for opportunities,
plus agency-level contact directory.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, Text, JSON


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

    # Contact intelligence fields
    agency: Optional[str] = Field(default=None, max_length=255, index=True)
    title: Optional[str] = Field(default=None, max_length=255)
    department: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=255)
    source: Optional[str] = Field(default="manual", max_length=50)  # manual|ai_extracted|imported
    extraction_confidence: Optional[float] = Field(default=None)
    linked_rfp_ids: Optional[list] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgencyContactDatabase(SQLModel, table=True):
    """
    Agency-level directory entry with primary contact linkage.
    """
    __tablename__ = "agency_contact_database"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agency_name: str = Field(max_length=255, index=True)
    office: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None, sa_column=Column(Text))
    website: Optional[str] = Field(default=None, max_length=500)
    primary_contact_id: Optional[int] = Field(
        default=None, foreign_key="opportunity_contacts.id"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
