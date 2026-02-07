"""
RFP Sniper - Salesforce Field Mapping Model
=============================================
Maps fields between GovTech Sniper capture plans and Salesforce Opportunities.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SalesforceFieldMapping(SQLModel, table=True):
    """Bidirectional field mapping between Sniper and Salesforce."""
    __tablename__ = "salesforce_field_mappings"

    id: Optional[int] = Field(default=None, primary_key=True)
    integration_id: int = Field(foreign_key="integrations.id", index=True)
    sniper_field: str = Field(max_length=255)
    salesforce_field: str = Field(max_length=255)
    direction: str = Field(default="both", max_length=10)  # push | pull | both
    transform: Optional[str] = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=datetime.utcnow)
