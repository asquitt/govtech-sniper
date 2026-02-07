"""
RFP Sniper - Salesforce Schemas
================================
Request/response models for Salesforce integration endpoints.
"""

from datetime import datetime

from pydantic import BaseModel


class SalesforceFieldMappingCreate(BaseModel):
    sniper_field: str
    salesforce_field: str
    direction: str = "both"
    transform: str | None = None


class SalesforceFieldMappingRead(BaseModel):
    id: int
    integration_id: int
    sniper_field: str
    salesforce_field: str
    direction: str
    transform: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SalesforceOpportunityRead(BaseModel):
    sf_id: str
    name: str
    amount: float | None = None
    stage: str | None = None
    close_date: str | None = None


class SalesforceSyncResult(BaseModel):
    status: str  # success | failed
    pushed: int = 0
    pulled: int = 0
    errors: list[str] = []
    completed_at: datetime
