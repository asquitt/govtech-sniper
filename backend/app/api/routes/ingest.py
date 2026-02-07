"""
RFP Sniper - Ingest Routes
===========================
Endpoints for SAM.gov data ingestion.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.deps import get_current_user_optional, resolve_user_id, check_rate_limit
from app.services.auth_service import UserAuth
from app.schemas.rfp import SAMSearchParams, SAMIngestResponse
from app.tasks.ingest_tasks import ingest_sam_opportunities
from app.config import settings

router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.post("/sam", response_model=SAMIngestResponse, dependencies=[Depends(check_rate_limit)])
async def trigger_sam_ingest(
    params: SAMSearchParams,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    apply_filter: bool = Query(True, description="Apply Killer Filter to results"),
    mock_variant: Optional[str] = Query(
        None,
        description="Mock variant override (only applies when MOCK_SAM_GOV=true)",
    ),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SAMIngestResponse:
    """
    Trigger a SAM.gov opportunity ingestion task.
    
    This endpoint queues a Celery task to:
    1. Search SAM.gov API for matching opportunities
    2. Store new opportunities in the database
    3. Optionally run the Killer Filter to qualify/disqualify
    
    **Note:** In production, user_id will come from JWT auth.
    **Note:** If MOCK_SAM_GOV=true, the task returns deterministic mock opportunities.
    """
    if not settings.sam_gov_api_key and not settings.mock_sam_gov:
        raise HTTPException(
            status_code=503,
            detail="SAM.gov API key not configured. Set SAM_GOV_API_KEY environment variable.",
        )
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Queue the Celery task
    task = ingest_sam_opportunities.delay(
        user_id=resolved_user_id,
        keywords=params.keywords,
        days_back=params.days_back,
        limit=params.limit,
        naics_codes=params.naics_codes,
        apply_filter=apply_filter,
        mock_variant=mock_variant,
    )
    
    return SAMIngestResponse(
        task_id=task.id,
        message=f"Ingest task queued. Searching for '{params.keywords}' opportunities.",
        status="processing",
    )


@router.get("/sam/status/{task_id}")
async def get_ingest_status(task_id: str) -> dict:
    """
    Get the status of an ingest task.
    
    Poll this endpoint to check if the ingest is complete.
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
                "status": "completed",
                "result": result.get(),
            }
        else:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(result.result),
            }
    else:
        return {
            "task_id": task_id,
            "status": normalize_status(result),
        }


@router.post("/sam/quick-search")
async def quick_search_sam(
    keywords: str = Query(..., min_length=1, description="Search keywords"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    days_back: int = Query(30, ge=1, le=365, description="Days to look back"),
) -> dict:
    """
    Quick synchronous search of SAM.gov (for preview/testing).
    
    Unlike the async ingest endpoint, this returns results immediately
    but doesn't store them in the database.
    
    **Note:** Use sparingly - the async ingest is preferred for production.
    **Note:** If MOCK_SAM_GOV=true, this returns deterministic mock opportunities.
    """
    if not settings.sam_gov_api_key and not settings.mock_sam_gov:
        raise HTTPException(
            status_code=503,
            detail="SAM.gov API key not configured",
        )
    
    from app.services.ingest_service import SAMGovService
    from app.schemas.rfp import SAMSearchParams
    
    service = SAMGovService()
    params = SAMSearchParams(
        keywords=keywords,
        days_back=days_back,
        limit=limit,
    )
    
    try:
        opportunities = await service.search_opportunities(params)
        return {
            "count": len(opportunities),
            "opportunities": [opp.model_dump() for opp in opportunities],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
