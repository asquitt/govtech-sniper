"""
RFP Sniper - Contract Schemas
=============================
Request/response models for contract tracking.
"""

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.contract import ContractStatus, DeliverableStatus


class ContractCreate(BaseModel):
    contract_number: str = Field(max_length=255)
    title: str = Field(max_length=500)
    agency: Optional[str] = None
    rfp_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    value: Optional[float] = None
    status: ContractStatus = ContractStatus.ACTIVE
    summary: Optional[str] = None


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    value: Optional[float] = None
    status: Optional[ContractStatus] = None
    summary: Optional[str] = None


class ContractRead(BaseModel):
    id: int
    user_id: int
    rfp_id: Optional[int]
    contract_number: str
    title: str
    agency: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    value: Optional[float]
    status: ContractStatus
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractListResponse(BaseModel):
    contracts: List[ContractRead]
    total: int


class DeliverableCreate(BaseModel):
    title: str = Field(max_length=500)
    due_date: Optional[date] = None
    status: DeliverableStatus = DeliverableStatus.PENDING
    notes: Optional[str] = None


class DeliverableUpdate(BaseModel):
    title: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[DeliverableStatus] = None
    notes: Optional[str] = None


class DeliverableRead(BaseModel):
    id: int
    contract_id: int
    title: str
    due_date: Optional[date]
    status: DeliverableStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str = Field(max_length=500)
    due_date: Optional[date] = None
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    due_date: Optional[date] = None
    is_complete: Optional[bool] = None
    notes: Optional[str] = None


class TaskRead(BaseModel):
    id: int
    contract_id: int
    title: str
    due_date: Optional[date]
    is_complete: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CPARSCreate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    overall_rating: Optional[str] = None
    notes: Optional[str] = None


class CPARSRead(BaseModel):
    id: int
    contract_id: int
    period_start: Optional[date]
    period_end: Optional[date]
    overall_rating: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusReportCreate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    summary: Optional[str] = None
    accomplishments: Optional[str] = None
    risks: Optional[str] = None
    next_steps: Optional[str] = None


class StatusReportUpdate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    summary: Optional[str] = None
    accomplishments: Optional[str] = None
    risks: Optional[str] = None
    next_steps: Optional[str] = None


class StatusReportRead(BaseModel):
    id: int
    contract_id: int
    period_start: Optional[date]
    period_end: Optional[date]
    summary: Optional[str]
    accomplishments: Optional[str]
    risks: Optional[str]
    next_steps: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
