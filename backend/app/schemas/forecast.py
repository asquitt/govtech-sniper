"""
Procurement forecast schemas.
"""

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel


class ForecastCreate(BaseModel):
    title: str
    agency: Optional[str] = None
    naics_code: Optional[str] = None
    estimated_value: Optional[float] = None
    expected_solicitation_date: Optional[date] = None
    expected_award_date: Optional[date] = None
    fiscal_year: Optional[int] = None
    source: str = "manual"
    source_url: Optional[str] = None
    description: Optional[str] = None


class ForecastUpdate(BaseModel):
    title: Optional[str] = None
    agency: Optional[str] = None
    naics_code: Optional[str] = None
    estimated_value: Optional[float] = None
    expected_solicitation_date: Optional[date] = None
    expected_award_date: Optional[date] = None
    fiscal_year: Optional[int] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None


class ForecastRead(BaseModel):
    id: int
    user_id: int
    title: str
    agency: Optional[str]
    naics_code: Optional[str]
    estimated_value: Optional[float]
    expected_solicitation_date: Optional[date]
    expected_award_date: Optional[date]
    fiscal_year: Optional[int]
    source: str
    source_url: Optional[str]
    description: Optional[str]
    linked_rfp_id: Optional[int]
    match_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ForecastAlertRead(BaseModel):
    id: int
    user_id: int
    forecast_id: int
    rfp_id: int
    match_score: float
    match_reason: Optional[str]
    is_dismissed: bool
    created_at: datetime
    forecast_title: Optional[str] = None
    rfp_title: Optional[str] = None

    model_config = {"from_attributes": True}
