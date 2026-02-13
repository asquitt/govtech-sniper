"""
Admin routes - Provider maturity + release gate.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import UserAuth, get_current_user
from app.database import get_session
from app.services.slo_service import slo_collector

from .helpers import _require_org_admin

router = APIRouter()


@router.get("/provider-maturity")
async def get_provider_maturity(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the maturity matrix for all registered data providers."""
    from app.services.data_providers import list_providers

    await _require_org_admin(current_user, session)

    providers = list_providers()
    return {
        "providers": [
            {
                "provider_name": p.provider_name,
                "display_name": p.display_name,
                "maturity": p.maturity.value,
                "last_live_sync": p.last_live_sync,
                "record_count_estimate": p.record_count_estimate,
                "is_active": p.is_active,
            }
            for p in providers
        ],
        "total": len(providers),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/release-gate")
async def get_release_gate(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Release gate based on SLO error budgets across all critical flows."""
    await _require_org_admin(current_user, session)
    return slo_collector.get_release_gate()
