"""
RFP Sniper - Ingest Routes
===========================
Endpoints for SAM.gov data ingestion.
"""

import socket
from datetime import datetime
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from kombu.exceptions import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import check_rate_limit, get_current_user_optional, resolve_user_id
from app.config import settings
from app.database import get_session
from app.models.rfp import RFP, RFPStatus
from app.schemas.rfp import SAMIngestResponse, SAMSearchParams
from app.services.auth_service import UserAuth
from app.services.cache_service import cache_clear_prefix
from app.services.ingest_service import SAMGovService
from app.tasks.ingest_tasks import ingest_sam_opportunities

router = APIRouter(prefix="/ingest", tags=["Ingest"])
logger = structlog.get_logger(__name__)


def _celery_broker_available() -> bool:
    """
    Best-effort broker probe so local/dev environments can gracefully
    fall back to synchronous ingest when Redis/Celery is unavailable.
    """
    broker_url = settings.celery_broker_url
    parsed = urlparse(broker_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return True

    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def _celery_worker_available() -> bool:
    """
    Best-effort worker probe so local/dev environments don't enqueue work
    that can never be processed when no Celery worker is connected.
    """
    try:
        from app.tasks.celery_app import celery_app

        replies = celery_app.control.inspect(timeout=0.5).ping() or {}
        return len(replies) > 0
    except Exception:
        return False


async def _run_synchronous_ingest(
    *,
    user_id: int,
    session: AsyncSession,
    params: SAMSearchParams,
    apply_filter: bool,  # kept for API parity; not used in inline fallback
    mock_variant: str | None,
) -> SAMIngestResponse:
    service = SAMGovService(mock_variant=mock_variant)
    opportunities = await service.search_opportunities(params)

    saved_count = 0
    seen_solicitations = set()
    for opp in opportunities:
        if opp.solicitation_number in seen_solicitations:
            continue
        seen_solicitations.add(opp.solicitation_number)

        existing_for_user = await session.execute(
            select(RFP).where(
                RFP.user_id == user_id,
                RFP.solicitation_number == opp.solicitation_number,
            )
        )
        if existing_for_user.scalar_one_or_none():
            continue

        solicitation_number = opp.solicitation_number
        existing_global = await session.execute(
            select(RFP).where(RFP.solicitation_number == solicitation_number)
        )
        global_rfp = existing_global.scalar_one_or_none()
        if global_rfp and global_rfp.user_id != user_id:
            # SQLite test/dev schema currently enforces globally unique solicitation
            # numbers, so namespaced mock IDs keep local ingest deterministic per user.
            if settings.mock_sam_gov:
                base = f"{opp.solicitation_number}-U{user_id}"
                solicitation_number = base[:100]
                suffix = 1
                while True:
                    candidate_check = await session.execute(
                        select(RFP).where(RFP.solicitation_number == solicitation_number)
                    )
                    if candidate_check.scalar_one_or_none() is None:
                        break
                    suffix_str = f"-{suffix}"
                    solicitation_number = f"{base[: 100 - len(suffix_str)]}{suffix_str}"
                    suffix += 1
            else:
                logger.debug(
                    "Skipping globally duplicate solicitation",
                    solicitation_number=solicitation_number,
                    user_id=user_id,
                )
                continue

        session.add(
            RFP(
                user_id=user_id,
                title=opp.title,
                solicitation_number=solicitation_number,
                agency=opp.agency,
                sub_agency=opp.sub_agency,
                naics_code=opp.naics_code,
                set_aside=opp.set_aside,
                rfp_type=opp.rfp_type,
                posted_date=opp.posted_date,
                response_deadline=opp.response_deadline,
                sam_gov_link=opp.ui_link,
                description=opp.description,
                status=RFPStatus.NEW,
            )
        )
        saved_count += 1

    await session.commit()
    await cache_clear_prefix(f"rfps:list:{user_id}:")

    task_id = f"sync-{int(datetime.utcnow().timestamp())}"

    return SAMIngestResponse(
        task_id=task_id,
        message=f"Ingest completed synchronously (saved {saved_count}).",
        status="completed",
        opportunities_found=len(opportunities),
    )


@router.post("/sam", response_model=SAMIngestResponse, dependencies=[Depends(check_rate_limit)])
async def trigger_sam_ingest(
    params: SAMSearchParams,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    apply_filter: bool = Query(True, description="Apply Killer Filter to results"),
    mock_variant: str | None = Query(
        None,
        description="Mock variant override (only applies when MOCK_SAM_GOV=true)",
    ),
    current_user: UserAuth | None = Depends(get_current_user_optional),
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

    # Prefer background task, but fall back to sync mode for local/dev when
    # broker/worker infrastructure is unavailable.
    should_fallback_sync = (settings.debug or settings.mock_sam_gov) and (
        not _celery_broker_available() or not _celery_worker_available()
    )
    if should_fallback_sync:
        logger.warning("Celery broker/worker unavailable; running ingest synchronously")
        return await _run_synchronous_ingest(
            user_id=resolved_user_id,
            session=session,
            params=params,
            apply_filter=apply_filter,
            mock_variant=mock_variant,
        )

    try:
        task = ingest_sam_opportunities.delay(
            user_id=resolved_user_id,
            keywords=params.keywords,
            days_back=params.days_back,
            limit=params.limit,
            naics_codes=params.naics_codes,
            apply_filter=apply_filter,
            mock_variant=mock_variant,
        )
    except OperationalError as exc:
        if settings.debug or settings.mock_sam_gov:
            logger.warning(
                "Celery dispatch failed; running ingest synchronously",
                error=str(exc),
            )
            return await _run_synchronous_ingest(
                user_id=resolved_user_id,
                session=session,
                params=params,
                apply_filter=apply_filter,
                mock_variant=mock_variant,
            )
        raise HTTPException(
            status_code=503,
            detail="Ingest worker unavailable. Please try again shortly.",
        ) from exc

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

    from app.schemas.rfp import SAMSearchParams
    from app.services.ingest_service import SAMGovService

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
