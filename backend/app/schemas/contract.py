"""
RFP Sniper - Contract Schemas
=============================
Request/response models for contract tracking.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.contract import ContractStatus, ContractType, DeliverableStatus
from app.models.proposal import DataClassification


class ContractCreate(BaseModel):
    contract_number: str = Field(max_length=255)
    title: str = Field(max_length=500)
    agency: str | None = None
    rfp_id: int | None = None
    parent_contract_id: int | None = None
    contract_type: ContractType | None = None
    start_date: date | None = None
    end_date: date | None = None
    value: float | None = None
    status: ContractStatus = ContractStatus.ACTIVE
    classification: DataClassification = DataClassification.INTERNAL
    summary: str | None = None


class ContractUpdate(BaseModel):
    title: str | None = None
    agency: str | None = None
    parent_contract_id: int | None = None
    contract_type: ContractType | None = None
    start_date: date | None = None
    end_date: date | None = None
    value: float | None = None
    status: ContractStatus | None = None
    classification: DataClassification | None = None
    summary: str | None = None


class ContractRead(BaseModel):
    id: int
    user_id: int
    rfp_id: int | None
    parent_contract_id: int | None
    contract_number: str
    title: str
    classification: DataClassification
    agency: str | None
    contract_type: ContractType | None
    start_date: date | None
    end_date: date | None
    value: float | None
    status: ContractStatus
    summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractListResponse(BaseModel):
    contracts: list[ContractRead]
    total: int


class DeliverableCreate(BaseModel):
    title: str = Field(max_length=500)
    due_date: date | None = None
    status: DeliverableStatus = DeliverableStatus.PENDING
    notes: str | None = None


class DeliverableUpdate(BaseModel):
    title: str | None = None
    due_date: date | None = None
    status: DeliverableStatus | None = None
    notes: str | None = None


class DeliverableRead(BaseModel):
    id: int
    contract_id: int
    title: str
    due_date: date | None
    status: DeliverableStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    risk_flag: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_risk_flag(self):
        if self.risk_flag:
            return self
        if self.status == DeliverableStatus.OVERDUE:
            self.risk_flag = "overdue"
            return self
        if self.due_date:
            days_left = (self.due_date - date.today()).days
            if days_left < 0:
                self.risk_flag = "overdue"
            elif days_left <= 7:
                self.risk_flag = "due_soon"
            else:
                self.risk_flag = "on_track"
        else:
            self.risk_flag = "on_track"
        return self


class TaskCreate(BaseModel):
    title: str = Field(max_length=500)
    due_date: date | None = None
    notes: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    due_date: date | None = None
    is_complete: bool | None = None
    notes: str | None = None


class TaskRead(BaseModel):
    id: int
    contract_id: int
    title: str
    due_date: date | None
    is_complete: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CPARSCreate(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    overall_rating: str | None = None
    notes: str | None = None


class CPARSRead(BaseModel):
    id: int
    contract_id: int
    period_start: date | None
    period_end: date | None
    overall_rating: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CPARSEvidenceCreate(BaseModel):
    document_id: int
    citation: str | None = None
    notes: str | None = None


class CPARSEvidenceRead(BaseModel):
    id: int
    cpars_id: int
    document_id: int
    citation: str | None
    notes: str | None
    created_at: datetime
    document_title: str | None = None
    document_type: str | None = None


class StatusReportCreate(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    summary: str | None = None
    accomplishments: str | None = None
    risks: str | None = None
    next_steps: str | None = None


class StatusReportUpdate(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    summary: str | None = None
    accomplishments: str | None = None
    risks: str | None = None
    next_steps: str | None = None


class StatusReportRead(BaseModel):
    id: int
    contract_id: int
    period_start: date | None
    period_end: date | None
    summary: str | None
    accomplishments: str | None
    risks: str | None
    next_steps: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
