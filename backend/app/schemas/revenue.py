"""
Revenue forecasting schemas.
"""

from pydantic import BaseModel


class PipelineStageSummary(BaseModel):
    stage: str
    count: int
    unweighted_value: float
    weighted_value: float


class PipelineSummaryResponse(BaseModel):
    total_opportunities: int
    total_unweighted: float
    total_weighted: float
    won_value: float
    stages: list[PipelineStageSummary]


class RevenueTimelinePoint(BaseModel):
    period: str
    weighted_value: float
    won_value: float
    opportunity_count: int


class RevenueTimelineResponse(BaseModel):
    granularity: str
    points: list[RevenueTimelinePoint]


class AgencyRevenueSummary(BaseModel):
    agency: str
    opportunity_count: int
    unweighted_value: float
    weighted_value: float
    won_value: float


class AgencyRevenueResponse(BaseModel):
    agencies: list[AgencyRevenueSummary]
    total_agencies: int
