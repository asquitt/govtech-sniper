"""
RFP Sniper - Analytics Schemas
===============================
Request/response models for analytics reporting endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Win Rate
# =============================================================================

class WinRateTrend(BaseModel):
    month: str
    won: int
    lost: int
    rate: float


class WinRateResponse(BaseModel):
    win_rate: float
    total_won: int
    total_lost: int
    trend: List[WinRateTrend]


# =============================================================================
# Pipeline by Stage
# =============================================================================

class PipelineStage(BaseModel):
    stage: str
    count: int
    total_value: float


class PipelineByStageResponse(BaseModel):
    stages: List[PipelineStage]
    total_pipeline_value: float


# =============================================================================
# Conversion Rates
# =============================================================================

class StageConversion(BaseModel):
    from_stage: str
    to_stage: str
    count_from: int
    count_to: int
    rate: float


class ConversionRatesResponse(BaseModel):
    conversions: List[StageConversion]
    overall_rate: float


# =============================================================================
# Proposal Turnaround
# =============================================================================

class TurnaroundPoint(BaseModel):
    month: str
    avg_days: float
    count: int


class ProposalTurnaroundResponse(BaseModel):
    overall_avg_days: float
    trend: List[TurnaroundPoint]


# =============================================================================
# NAICS Performance
# =============================================================================

class NAICSPerformance(BaseModel):
    naics_code: str
    total: int
    won: int
    lost: int
    win_rate: float


class NAICSPerformanceResponse(BaseModel):
    entries: List[NAICSPerformance]


# =============================================================================
# Export
# =============================================================================

class ExportRequest(BaseModel):
    report_type: str = Field(
        ..., description="One of: win-rate, pipeline, conversion, turnaround, naics"
    )
    format: str = Field(default="csv", description="Export format (csv)")
