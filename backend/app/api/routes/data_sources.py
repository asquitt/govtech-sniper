"""
Data Sources Routes
====================
Endpoints to list, search, ingest, and health-check data source providers.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.rfp import RFP, RFPStatus
from app.services.auth_service import UserAuth
from app.services.data_providers import (
    RawOpportunity,
    SearchParams,
    get_provider,
    list_providers,
)

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])


# ── Response schemas ────────────────────────────────────────────────────────


class ProviderInfo(BaseModel):
    provider_name: str
    display_name: str
    description: str
    is_active: bool
    healthy: bool | None = None


class SearchResponse(BaseModel):
    provider: str
    count: int
    results: list[RawOpportunity]


class IngestResponse(BaseModel):
    provider: str
    searched: int
    created: int
    skipped: int


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("", response_model=list[ProviderInfo])
async def list_data_sources(
    current_user: UserAuth = Depends(get_current_user),
) -> list[ProviderInfo]:
    """List all registered data source providers."""
    providers = list_providers()
    return [
        ProviderInfo(
            provider_name=p.provider_name,
            display_name=p.display_name,
            description=p.description,
            is_active=p.is_active,
        )
        for p in providers
    ]


@router.post("/{provider_name}/search", response_model=SearchResponse)
async def search_provider(
    provider_name: str,
    params: SearchParams,
    current_user: UserAuth = Depends(get_current_user),
) -> SearchResponse:
    """Search opportunities via a specific provider."""
    provider = get_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")
    if not provider.is_active:
        raise HTTPException(status_code=400, detail=f"Provider '{provider_name}' is not active")

    results = await provider.search(params)
    return SearchResponse(provider=provider_name, count=len(results), results=results)


@router.post("/{provider_name}/ingest", response_model=IngestResponse)
async def ingest_from_provider(
    provider_name: str,
    params: SearchParams,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    """Search a provider and create RFP records for new results."""
    provider = get_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")
    if not provider.is_active:
        raise HTTPException(status_code=400, detail=f"Provider '{provider_name}' is not active")

    results = await provider.search(params)

    created = 0
    skipped = 0

    for opp in results:
        # Skip duplicates by external_id used as solicitation_number
        existing = await session.execute(
            select(RFP).where(RFP.solicitation_number == opp.external_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        rfp = RFP(
            title=opp.title[:500],
            solicitation_number=opp.external_id,
            agency=opp.agency or "Unknown",
            naics_code=opp.naics_code,
            description=opp.description,
            source_url=opp.source_url,
            source_type=opp.source_type,
            estimated_value=int(opp.estimated_value) if opp.estimated_value else None,
            posted_date=_parse_date(opp.posted_date),
            response_deadline=_parse_date(opp.response_deadline),
            status=RFPStatus.NEW,
            user_id=current_user.id,
        )
        session.add(rfp)
        created += 1

    if created:
        await session.commit()

    return IngestResponse(
        provider=provider_name,
        searched=len(results),
        created=created,
        skipped=skipped,
    )


@router.get("/{provider_name}/health")
async def check_provider_health(
    provider_name: str,
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Health check a single provider."""
    provider = get_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    healthy = await provider.health_check()
    return {"provider": provider_name, "healthy": healthy}


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None
