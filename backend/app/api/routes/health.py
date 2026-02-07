"""
RFP Sniper - Health Check Routes
=================================
System health and status endpoints.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import text

from app.config import settings
from app.database import get_session
from app.services.gemini_service import GeminiService
from app.services.ingest_service import SAMGovService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint.
    Returns application status without checking dependencies.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Readiness check - verifies all dependencies are available.
    Use this for Kubernetes readiness probes.
    """
    checks = {
        "database": False,
        "redis": False,
        "sam_gov_api": False,
        "gemini_api": False,
    }

    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)

    # Check Redis
    try:
        import redis.asyncio as redis

        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        checks["redis"] = True
    except Exception as e:
        checks["redis_error"] = str(e)

    # Check SAM.gov API (if key configured)
    if settings.mock_sam_gov:
        checks["sam_gov_api"] = "mocked"
    elif settings.sam_gov_api_key:
        try:
            sam_service = SAMGovService()
            checks["sam_gov_api"] = await sam_service.health_check()
        except Exception as e:
            checks["sam_gov_error"] = str(e)
    else:
        checks["sam_gov_api"] = "not_configured"

    # Check Gemini API (if key configured)
    if settings.gemini_api_key:
        try:
            gemini_service = GeminiService()
            checks["gemini_api"] = await gemini_service.health_check()
        except Exception as e:
            checks["gemini_error"] = str(e)
    else:
        checks["gemini_api"] = "not_configured"

    # Determine overall status
    critical_checks = ["database", "redis"]
    all_critical_healthy = all(checks.get(c) is True for c in critical_checks)

    return {
        "status": "ready" if all_critical_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """
    Liveness check - just confirms the process is running.
    Use this for Kubernetes liveness probes.
    """
    return {"status": "alive"}
