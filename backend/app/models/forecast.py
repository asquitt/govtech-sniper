"""
Procurement forecast models.
"""

from datetime import date, datetime
from typing import Optional
from enum import Enum

from sqlmodel import Field, SQLModel


class ForecastSource(str, Enum):
    SAM_GOV = "sam_gov"
    AGENCY_PLAN = "agency_plan"
    BUDGET_DOC = "budget_doc"
    MANUAL = "manual"


class ProcurementForecast(SQLModel, table=True):
    """
    Procurement forecast record — anticipated future solicitations.
    """
    __tablename__ = "procurement_forecasts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    title: str = Field(max_length=500)
    agency: Optional[str] = Field(default=None, max_length=255, index=True)
    naics_code: Optional[str] = Field(default=None, max_length=10, index=True)
    estimated_value: Optional[float] = None
    expected_solicitation_date: Optional[date] = None
    expected_award_date: Optional[date] = None
    fiscal_year: Optional[int] = Field(default=None, index=True)
    source: ForecastSource = Field(default=ForecastSource.MANUAL)
    source_url: Optional[str] = None
    description: Optional[str] = None
    linked_rfp_id: Optional[int] = Field(
        default=None, foreign_key="rfps.id", index=True
    )
    match_score: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ForecastAlert(SQLModel, table=True):
    """
    Auto-generated alert when a forecast matches an existing RFP.
    """
    __tablename__ = "forecast_alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    forecast_id: int = Field(foreign_key="procurement_forecasts.id", index=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)

    match_score: float = Field(default=0.0)
    match_reason: Optional[str] = None
    is_dismissed: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
