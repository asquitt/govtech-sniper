"""
RFP Sniper - Opportunity Contact Models
=======================================
Buyer and stakeholder contacts for opportunities,
plus agency-level contact directory.
"""

from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel, Text


class OpportunityContact(SQLModel, table=True):
    """
    Contact record associated with an opportunity.
    """

    __tablename__ = "opportunity_contacts"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)

    name: str = Field(max_length=255)
    role: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, sa_column=Column(Text))

    # Contact intelligence fields
    agency: str | None = Field(default=None, max_length=255, index=True)
    title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default="manual", max_length=50)  # manual|ai_extracted|imported
    extraction_confidence: float | None = Field(default=None)
    linked_rfp_ids: list | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgencyContactDatabase(SQLModel, table=True):
    """
    Agency-level directory entry with primary contact linkage.
    """

    __tablename__ = "agency_contact_database"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    agency_name: str = Field(max_length=255, index=True)
    office: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, sa_column=Column(Text))
    website: str | None = Field(default=None, max_length=500)
    primary_contact_id: int | None = Field(default=None, foreign_key="opportunity_contacts.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
