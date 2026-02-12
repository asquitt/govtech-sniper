"""AI draft quality benchmarking routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_optional
from app.services.auth_service import UserAuth
from app.services.draft_benchmark import (
    BENCHMARK_SCENARIOS,
    generate_recommendations,
    score_section_text,
)

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ScoreRequest(BaseModel):
    section_name: str = Field(..., description="Name of the proposal section")
    section_text: str = Field(..., min_length=1, description="Text content to score")
    requirements: list[str] = Field(
        ..., min_length=1, description="RFP requirements to check against"
    )


class ScoreResponse(BaseModel):
    section_name: str
    compliance_coverage: float
    specificity: float
    citation_density: float
    readability: float
    structure_score: float
    overall: float
    is_pink_team_ready: bool


class BenchmarkResultResponse(BaseModel):
    rfp_type: str
    sections: list[ScoreResponse]
    overall_score: float
    pink_team_ready: bool
    recommendations: list[str]


class ScenarioResponse(BaseModel):
    rfp_type: str
    title: str
    sections: list[str]
    key_requirements: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/scenarios", response_model=list[ScenarioResponse])
async def list_scenarios(
    current_user: UserAuth | None = Depends(get_current_user_optional),
) -> list[ScenarioResponse]:
    """Return all built-in benchmark RFP scenarios."""
    return [ScenarioResponse(**s) for s in BENCHMARK_SCENARIOS]


@router.post("/score", response_model=ScoreResponse)
async def score_section(
    request: ScoreRequest,
    current_user: UserAuth | None = Depends(get_current_user_optional),
) -> ScoreResponse:
    """Score a single proposal section against pink-team readiness criteria."""
    result = score_section_text(
        section_name=request.section_name,
        text=request.section_text,
        requirements=request.requirements,
    )
    return ScoreResponse(
        section_name=result.section_name,
        compliance_coverage=result.compliance_coverage,
        specificity=result.specificity,
        citation_density=result.citation_density,
        readability=result.readability,
        structure_score=result.structure_score,
        overall=result.overall,
        is_pink_team_ready=result.is_pink_team_ready,
    )


@router.post("/score-batch", response_model=BenchmarkResultResponse)
async def score_batch(
    rfp_type: str,
    sections: list[ScoreRequest],
    current_user: UserAuth | None = Depends(get_current_user_optional),
) -> BenchmarkResultResponse:
    """Score multiple sections and return an aggregate benchmark result."""
    scores = [
        score_section_text(
            section_name=s.section_name,
            text=s.section_text,
            requirements=s.requirements,
        )
        for s in sections
    ]

    overall = sum(s.overall for s in scores) / max(len(scores), 1)
    pink_ready = all(s.is_pink_team_ready for s in scores)
    recs = generate_recommendations(scores)

    section_responses = [
        ScoreResponse(
            section_name=s.section_name,
            compliance_coverage=s.compliance_coverage,
            specificity=s.specificity,
            citation_density=s.citation_density,
            readability=s.readability,
            structure_score=s.structure_score,
            overall=s.overall,
            is_pink_team_ready=s.is_pink_team_ready,
        )
        for s in scores
    ]

    return BenchmarkResultResponse(
        rfp_type=rfp_type,
        sections=section_responses,
        overall_score=round(overall, 1),
        pink_team_ready=pink_ready,
        recommendations=recs,
    )
