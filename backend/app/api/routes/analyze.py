"""
RFP Sniper - Analysis Routes
=============================
Endpoints for RFP analysis using Gemini AI.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user_optional, resolve_user_id
from app.services.auth_service import UserAuth
from app.models.rfp import RFP, RFPStatus, ComplianceMatrix
from app.schemas.rfp import AnalyzeResponse, ComplianceMatrixRead, ComplianceRequirementRead
from app.tasks.analysis_tasks import analyze_rfp, run_killer_filter
from app.config import settings

router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post("/{rfp_id}", response_model=AnalyzeResponse)
async def trigger_rfp_analysis(
    rfp_id: int = Path(..., description="RFP ID to analyze"),
    force_reanalyze: bool = Query(False, description="Re-analyze even if already done"),
    session: AsyncSession = Depends(get_session),
) -> AnalyzeResponse:
    """
    Trigger Deep Read analysis on an RFP.
    
    This uses Gemini 1.5 Pro to:
    1. Extract all compliance requirements
    2. Categorize by importance (Mandatory, Evaluated, etc.)
    3. Generate a summary
    
    The analysis runs as a background task. Poll the status endpoint
    or check the RFP's status field for completion.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured. Set GEMINI_API_KEY environment variable.",
        )
    
    # Verify RFP exists
    result = await session.execute(
        select(RFP).where(RFP.id == rfp_id)
    )
    rfp = result.scalar_one_or_none()
    
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")
    
    # Check if already analyzed
    if rfp.status == RFPStatus.ANALYZED and not force_reanalyze:
        return AnalyzeResponse(
            task_id="none",
            rfp_id=rfp_id,
            message="RFP already analyzed. Set force_reanalyze=true to re-analyze.",
            status="already_completed",
        )
    
    # Check if has content to analyze
    if not rfp.full_text and not rfp.description:
        raise HTTPException(
            status_code=400,
            detail="RFP has no text content to analyze. Upload a PDF first.",
        )
    
    # Queue the analysis task
    task = analyze_rfp.delay(rfp_id=rfp_id, force_reanalyze=force_reanalyze)
    
    return AnalyzeResponse(
        task_id=task.id,
        rfp_id=rfp_id,
        message="Deep Read analysis started",
        status="analyzing",
    )


@router.get("/{rfp_id}/status/{task_id}")
async def get_analysis_status(
    rfp_id: int = Path(..., description="RFP ID"),
    task_id: str = Path(..., description="Task ID from analyze endpoint"),
) -> dict:
    """
    Get the status of an analysis task.
    """
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app
    
    def normalize_status(result: AsyncResult) -> str:
        if result.ready():
            return "completed" if result.successful() else "failed"
        state = (result.state or "").lower()
        if state in {"pending", "received"}:
            return "pending"
        return "processing"
    
    result = AsyncResult(task_id, app=celery_app)
    
    if result.ready():
        if result.successful():
            return {
                "task_id": task_id,
                "rfp_id": rfp_id,
                "status": "completed",
                "result": result.get(),
            }
        else:
            return {
                "task_id": task_id,
                "rfp_id": rfp_id,
                "status": "failed",
                "error": str(result.result),
            }
    else:
        return {
            "task_id": task_id,
            "rfp_id": rfp_id,
            "status": normalize_status(result),
        }


@router.get("/{rfp_id}/matrix", response_model=ComplianceMatrixRead)
async def get_compliance_matrix(
    rfp_id: int = Path(..., description="RFP ID"),
    session: AsyncSession = Depends(get_session),
) -> ComplianceMatrixRead:
    """
    Get the extracted compliance matrix for an RFP.
    
    Returns all requirements with their importance levels,
    categories, and addressed status.
    """
    # Get the compliance matrix
    result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = result.scalar_one_or_none()
    
    if not matrix:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance matrix not found for RFP {rfp_id}. Run analysis first.",
        )
    
    # Parse requirements
    requirements = [
        ComplianceRequirementRead(**req) for req in matrix.requirements
    ]
    
    return ComplianceMatrixRead(
        id=matrix.id,
        rfp_id=matrix.rfp_id,
        requirements=requirements,
        total_requirements=matrix.total_requirements,
        mandatory_count=matrix.mandatory_count,
        addressed_count=matrix.addressed_count,
        extraction_confidence=matrix.extraction_confidence,
        created_at=matrix.created_at,
        updated_at=matrix.updated_at,
    )


@router.post("/{rfp_id}/filter")
async def trigger_killer_filter(
    rfp_id: int = Path(..., description="RFP ID to filter"),
    user_id: Optional[int] = Query(None, description="User ID for profile lookup (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Run the Killer Filter on an RFP.
    
    Uses Gemini 1.5 Flash to quickly determine if the user
    should pursue this opportunity based on their profile.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured",
        )
    
    # Verify RFP exists
    result = await session.execute(
        select(RFP).where(RFP.id == rfp_id)
    )
    rfp = result.scalar_one_or_none()
    
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Queue the filter task
    task = run_killer_filter.delay(rfp_id=rfp_id, user_id=resolved_user_id)
    
    return {
        "task_id": task.id,
        "rfp_id": rfp_id,
        "message": "Killer Filter analysis started",
        "status": "processing",
    }
