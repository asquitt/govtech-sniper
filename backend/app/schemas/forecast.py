"""
Procurement forecast schemas.
"""

from datetime import date, datetime

from pydantic import BaseModel


class ForecastCreate(BaseModel):
    title: str
    agency: str | None = None
    naics_code: str | None = None
    estimated_value: float | None = None
    expected_solicitation_date: date | None = None
    expected_award_date: date | None = None
    fiscal_year: int | None = None
    source: str = "manual"
    source_url: str | None = None
    description: str | None = None


class ForecastUpdate(BaseModel):
    title: str | None = None
    agency: str | None = None
    naics_code: str | None = None
    estimated_value: float | None = None
    expected_solicitation_date: date | None = None
    expected_award_date: date | None = None
    fiscal_year: int | None = None
    source: str | None = None
    source_url: str | None = None
    description: str | None = None


class ForecastRead(BaseModel):
    id: int
    user_id: int
    title: str
    agency: str | None
    naics_code: str | None
    estimated_value: float | None
    expected_solicitation_date: date | None
    expected_award_date: date | None
    fiscal_year: int | None
    source: str
    source_url: str | None
    description: str | None
    linked_rfp_id: int | None
    match_score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ForecastAlertRead(BaseModel):
    id: int
    user_id: int
    forecast_id: int
    rfp_id: int
    match_score: float
    match_reason: str | None
    is_dismissed: bool
    created_at: datetime
    forecast_title: str | None = None
    rfp_title: str | None = None

    model_config = {"from_attributes": True}
