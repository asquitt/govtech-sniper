"""
GSA eBuy Data Provider
=======================
Fetches opportunities from the GSA eBuy system via the SAM.gov API.
GSA eBuy opportunities are published through SAM.gov with specific filters.
"""

from typing import Optional

import httpx
import structlog

from app.config import settings
from app.services.data_providers.base import (
    DataSourceProvider,
    RawOpportunity,
    SearchParams,
)

logger = structlog.get_logger(__name__)

GSA_EBUY_BASE_URL = "https://api.sam.gov/opportunities/v2/search"


class GSAEbuyProvider(DataSourceProvider):
    """Provider for GSA eBuy opportunities via SAM.gov API."""

    provider_name = "gsa_ebuy"
    display_name = "GSA eBuy"
    description = "GSA eBuy quotes and RFQs for Schedule holders"
    is_active = True

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        api_key = getattr(settings, "sam_gov_api_key", None)
        if not api_key:
            logger.warning("gsa_ebuy.search: SAM_GOV_API_KEY not configured")
            return []

        query_params: dict = {
            "api_key": api_key,
            "postedFrom": _days_back_date(params.days_back),
            "postedTo": _today(),
            "limit": min(params.limit, 100),
            "offset": 0,
            "organizationId": "100006688",  # GSA org ID in SAM
        }
        if params.keywords:
            query_params["keyword"] = params.keywords
        if params.naics_codes:
            query_params["naicsCode"] = ",".join(params.naics_codes)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(GSA_EBUY_BASE_URL, params=query_params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("gsa_ebuy.search failed", error=str(exc))
            return []

        opportunities = data.get("opportunitiesData", [])
        return [_map_sam_to_raw(opp) for opp in opportunities]

    async def get_details(self, opportunity_id: str) -> Optional[RawOpportunity]:
        api_key = getattr(settings, "sam_gov_api_key", None)
        if not api_key:
            return None

        url = f"https://api.sam.gov/opportunities/v2/search"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    url,
                    params={
                        "api_key": api_key,
                        "noticeId": opportunity_id,
                        "limit": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("gsa_ebuy.get_details failed", error=str(exc))
            return None

        items = data.get("opportunitiesData", [])
        if not items:
            return None
        return _map_sam_to_raw(items[0])

    async def health_check(self) -> bool:
        api_key = getattr(settings, "sam_gov_api_key", None)
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    GSA_EBUY_BASE_URL,
                    params={"api_key": api_key, "limit": 1, "offset": 0},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _map_sam_to_raw(opp: dict) -> RawOpportunity:
    return RawOpportunity(
        external_id=opp.get("noticeId", ""),
        title=opp.get("title", "Untitled"),
        agency=opp.get("fullParentPathName", opp.get("departmentName")),
        description=opp.get("description"),
        posted_date=opp.get("postedDate"),
        response_deadline=opp.get("responseDeadLine"),
        estimated_value=None,
        naics_code=opp.get("naicsCode"),
        source_url=opp.get("uiLink"),
        source_type="gsa_ebuy",
        raw_data=opp,
    )


def _days_back_date(days: int) -> str:
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(days=days)).strftime("%m/%d/%Y")


def _today() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%m/%d/%Y")
