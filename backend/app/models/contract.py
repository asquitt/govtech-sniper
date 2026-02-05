"""
RFP Sniper - Contract Models
============================
Post-award contract tracking and CPARS preparation.
"""

from datetime import datetime, date
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel


class ContractStatus(str, Enum):
    ACTIVE = "active"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class DeliverableStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    OVERDUE = "overdue"


class ContractAward(SQLModel, table=True):
    """
    Awarded contract record.
    """
    __tablename__ = "contract_awards"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: Optional[int] = Field(default=None, foreign_key="rfps.id", index=True)

    contract_number: str = Field(max_length=255)
    title: str = Field(max_length=500)
    agency: Optional[str] = Field(default=None, max_length=255)

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    value: Optional[float] = None
    status: ContractStatus = Field(default=ContractStatus.ACTIVE)

    summary: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContractDeliverable(SQLModel, table=True):
    """
    Deliverable tracking for a contract.
    """
    __tablename__ = "contract_deliverables"

    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    title: str = Field(max_length=500)
    due_date: Optional[date] = None
    status: DeliverableStatus = Field(default=DeliverableStatus.PENDING)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContractTask(SQLModel, table=True):
    """
    Task tracking for a contract.
    """
    __tablename__ = "contract_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    title: str = Field(max_length=500)
    due_date: Optional[date] = None
    is_complete: bool = Field(default=False)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CPARSReview(SQLModel, table=True):
    """
    CPARS review preparation record.
    """
    __tablename__ = "cpars_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    period_start: Optional[date] = None
    period_end: Optional[date] = None
    overall_rating: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
