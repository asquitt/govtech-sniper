"""Teaming Board - Capability Gap Analysis."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.schemas.teaming import CapabilityGapResult
from app.services.auth_service import UserAuth
from app.services.capability_gap_service import analyze_capability_gaps

router = APIRouter()


@router.get("/gap-analysis/{rfp_id}", response_model=CapabilityGapResult)
async def get_gap_analysis(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CapabilityGapResult:
    """AI-powered capability gap analysis for an RFP."""
    result = await analyze_capability_gaps(rfp_id, current_user.id, session)
    return CapabilityGapResult(
        rfp_id=result.rfp_id,
        gaps=result.gaps,
        recommended_partners=result.recommended_partners,
        analysis_summary=result.analysis_summary,
    )
