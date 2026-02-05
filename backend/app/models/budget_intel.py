"""
RFP Sniper - Budget Intelligence Models
=======================================
Tracks budget documents and funding intel tied to opportunities.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BudgetIntelligence(SQLModel, table=True):
    __tablename__ = "budget_intelligence"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rfp_id: Optional[int] = Field(default=None, foreign_key="rfps.id", index=True)

    title: str = Field(max_length=255)
    fiscal_year: Optional[int] = Field(default=None)
    amount: Optional[float] = Field(default=None)
    source_url: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
