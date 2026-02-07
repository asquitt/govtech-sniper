"""
RFP Sniper - Salesforce Schemas
================================
Request/response models for Salesforce integration endpoints.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class SalesforceFieldMappingCreate(BaseModel):
    sniper_field: str
    salesforce_field: str
    direction: str = "both"
    transform: Optional[str] = None


class SalesforceFieldMappingRead(BaseModel):
    id: int
    integration_id: int
    sniper_field: str
    salesforce_field: str
    direction: str
    transform: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SalesforceOpportunityRead(BaseModel):
    sf_id: str
    name: str
    amount: Optional[float] = None
    stage: Optional[str] = None
    close_date: Optional[str] = None


class SalesforceSyncResult(BaseModel):
    status: str  # success | failed
    pushed: int = 0
    pulled: int = 0
    errors: List[str] = []
    completed_at: datetime
