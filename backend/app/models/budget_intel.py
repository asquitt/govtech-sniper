"""
RFP Sniper - Budget Intelligence Models
=======================================
Tracks budget documents and funding intel tied to opportunities.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class BudgetIntelligence(SQLModel, table=True):
    __tablename__ = "budget_intelligence"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)

    title: str = Field(max_length=255)
    fiscal_year: int | None = Field(default=None)
    amount: float | None = Field(default=None)
    source_url: str | None = Field(default=None, max_length=500)
    notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
