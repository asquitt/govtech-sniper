"""
Procurement forecast models.
"""

from datetime import date, datetime
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

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    title: str = Field(max_length=500)
    agency: str | None = Field(default=None, max_length=255, index=True)
    naics_code: str | None = Field(default=None, max_length=10, index=True)
    estimated_value: float | None = None
    expected_solicitation_date: date | None = None
    expected_award_date: date | None = None
    fiscal_year: int | None = Field(default=None, index=True)
    source: ForecastSource = Field(default=ForecastSource.MANUAL)
    source_url: str | None = None
    description: str | None = None
    linked_rfp_id: int | None = Field(default=None, foreign_key="rfps.id", index=True)
    match_score: float | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ForecastAlert(SQLModel, table=True):
    """
    Auto-generated alert when a forecast matches an existing RFP.
    """

    __tablename__ = "forecast_alerts"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    forecast_id: int = Field(foreign_key="procurement_forecasts.id", index=True)
    rfp_id: int = Field(foreign_key="rfps.id", index=True)

    match_score: float = Field(default=0.0)
    match_reason: str | None = None
    is_dismissed: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
