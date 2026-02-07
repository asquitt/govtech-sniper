"""Past performance schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class PastPerformanceMetadata(BaseModel):
    """Metadata to add to a knowledge base document."""

    contract_number: str | None = Field(None, max_length=50)
    performing_agency: str | None = Field(None, max_length=255)
    contract_value: float | None = None
    period_of_performance_start: datetime | None = None
    period_of_performance_end: datetime | None = None
    naics_code: str | None = Field(None, max_length=10)
    relevance_tags: list[str] | None = None


class PastPerformanceRead(BaseModel):
    """Past performance document with metadata."""

    id: int
    title: str
    document_type: str
    contract_number: str | None = None
    performing_agency: str | None = None
    contract_value: float | None = None
    period_of_performance_start: datetime | None = None
    period_of_performance_end: datetime | None = None
    naics_code: str | None = None
    relevance_tags: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PastPerformanceListResponse(BaseModel):
    """List of past performance documents."""

    documents: list[PastPerformanceRead]
    total: int


class MatchResult(BaseModel):
    """Single match result."""

    document_id: int
    title: str
    score: float
    matching_criteria: list[str]


class MatchResponse(BaseModel):
    """Response for relevance matching."""

    rfp_id: int
    matches: list[MatchResult]
    total: int


class NarrativeResponse(BaseModel):
    """Generated narrative response."""

    document_id: int
    rfp_id: int
    narrative: str
