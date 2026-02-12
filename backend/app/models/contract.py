"""
RFP Sniper - Contract Models
============================
Post-award contract tracking and CPARS preparation.
"""

from datetime import date, datetime
from enum import Enum

from sqlmodel import Column, Field, SQLModel, Text


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


class ContractType(str, Enum):
    PRIME = "prime"
    SUBCONTRACT = "subcontract"
    IDIQ = "idiq"
    TASK_ORDER = "task_order"
    BPA = "bpa"


class ModType(str, Enum):
    ADMINISTRATIVE = "administrative"
    FUNDING = "funding"
    SCOPE = "scope"
    PERIOD_OF_PERFORMANCE = "period_of_performance"
    OTHER = "other"


class CLINType(str, Enum):
    FFP = "ffp"
    T_AND_M = "t_and_m"
    COST_PLUS = "cost_plus"


class ContractAward(SQLModel, table=True):
    """
    Awarded contract record.
    """

    __tablename__ = "contract_awards"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)
    parent_contract_id: int | None = Field(
        default=None, foreign_key="contract_awards.id", index=True
    )

    # Data classification for CUI/FCI policy enforcement
    classification: str = Field(default="internal", max_length=20)

    contract_number: str = Field(max_length=255)
    title: str = Field(max_length=500)
    agency: str | None = Field(default=None, max_length=255)
    contract_type: str | None = Field(default=None, max_length=50)

    start_date: date | None = None
    end_date: date | None = None
    value: float | None = None
    status: ContractStatus = Field(default=ContractStatus.ACTIVE)

    summary: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContractDeliverable(SQLModel, table=True):
    """
    Deliverable tracking for a contract.
    """

    __tablename__ = "contract_deliverables"

    id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    title: str = Field(max_length=500)
    due_date: date | None = None
    status: DeliverableStatus = Field(default=DeliverableStatus.PENDING)
    notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContractTask(SQLModel, table=True):
    """
    Task tracking for a contract.
    """

    __tablename__ = "contract_tasks"

    id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    title: str = Field(max_length=500)
    due_date: date | None = None
    is_complete: bool = Field(default=False)
    notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CPARSReview(SQLModel, table=True):
    """
    CPARS review preparation record.
    """

    __tablename__ = "cpars_reviews"

    id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    period_start: date | None = None
    period_end: date | None = None
    overall_rating: str | None = Field(default=None, max_length=100)
    notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class CPARSEvidence(SQLModel, table=True):
    """
    Evidence links for CPARS preparation.
    """

    __tablename__ = "cpars_evidence_links"

    id: int | None = Field(default=None, primary_key=True)
    cpars_id: int = Field(foreign_key="cpars_reviews.id", index=True)
    document_id: int = Field(foreign_key="knowledge_base_documents.id", index=True)

    citation: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContractStatusReport(SQLModel, table=True):
    """
    Monthly status report for a contract.
    """

    __tablename__ = "contract_status_reports"

    id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    period_start: date | None = None
    period_end: date | None = None

    summary: str | None = Field(default=None, sa_column=Column(Text))
    accomplishments: str | None = Field(default=None, sa_column=Column(Text))
    risks: str | None = Field(default=None, sa_column=Column(Text))
    next_steps: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContractModification(SQLModel, table=True):
    """
    Contract modification record.
    """

    __tablename__ = "contract_modifications"

    id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    modification_number: str = Field(max_length=50)
    mod_type: str | None = Field(default=None, max_length=50)
    description: str | None = None
    effective_date: date | None = None
    value_change: float | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContractCLIN(SQLModel, table=True):
    """
    Contract Line Item Number.
    """

    __tablename__ = "contract_clins"

    id: int | None = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract_awards.id", index=True)

    clin_number: str = Field(max_length=50)
    description: str | None = None
    clin_type: str | None = Field(default=None, max_length=20)
    unit_price: float | None = None
    quantity: int | None = None
    total_value: float | None = None
    funded_amount: float | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
