"""
Contract Vehicle Feed Providers
===============================
GWAC/IDIQ vehicle providers that fetch real opportunities via SAM.gov API
filtered by managing organization and contract vehicle metadata.
"""

from datetime import datetime, timedelta

import httpx
import structlog

from app.config import settings
from app.services.data_providers.base import (
    DataSourceProvider,
    ProviderMaturity,
    RawOpportunity,
    SearchParams,
)

logger = structlog.get_logger(__name__)

SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"


def _days_back_date(days: int) -> str:
    return (datetime.utcnow() - timedelta(days=days)).strftime("%m/%d/%Y")


def _today() -> str:
    return datetime.utcnow().strftime("%m/%d/%Y")


def _map_sam_to_raw(opp: dict, source_type: str) -> RawOpportunity:
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
        source_type=source_type,
        raw_data=opp,
    )


class _SAMVehicleProvider(DataSourceProvider):
    """Base class for contract vehicle providers that query SAM.gov with org filters."""

    organization_id: str = ""
    vehicle_keyword: str = ""
    maturity = ProviderMaturity.HYBRID

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        api_key = getattr(settings, "sam_gov_api_key", None)
        if not api_key:
            logger.warning(f"{self.provider_name}.search: SAM_GOV_API_KEY not configured")
            return []

        query_params: dict = {
            "api_key": api_key,
            "postedFrom": _days_back_date(params.days_back),
            "postedTo": _today(),
            "limit": min(params.limit, 100),
            "offset": 0,
        }
        if self.organization_id:
            query_params["organizationId"] = self.organization_id
        if params.keywords:
            query_params["keyword"] = params.keywords
        elif self.vehicle_keyword:
            query_params["keyword"] = self.vehicle_keyword
        if params.naics_codes:
            query_params["naicsCode"] = ",".join(params.naics_codes)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(SAM_SEARCH_URL, params=query_params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"{self.provider_name}.search failed", error=str(exc))
            return []

        opportunities = data.get("opportunitiesData", [])
        return [_map_sam_to_raw(opp, self.provider_name) for opp in opportunities]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        api_key = getattr(settings, "sam_gov_api_key", None)
        if not api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    SAM_SEARCH_URL,
                    params={"api_key": api_key, "noticeId": opportunity_id, "limit": 1},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error(f"{self.provider_name}.get_details failed", error=str(exc))
            return None

        items = data.get("opportunitiesData", [])
        if not items:
            return None
        return _map_sam_to_raw(items[0], self.provider_name)

    async def health_check(self) -> bool:
        api_key = getattr(settings, "sam_gov_api_key", None)
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    SAM_SEARCH_URL, params={"api_key": api_key, "limit": 1, "offset": 0}
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


class GsaMasProvider(_SAMVehicleProvider):
    """GSA Multiple Award Schedule opportunities via SAM.gov."""

    provider_name = "gsa_mas"
    display_name = "GSA MAS"
    description = "GSA Multiple Award Schedule opportunities"
    organization_id = "100006688"  # GSA org ID
    vehicle_keyword = "GSA Schedule"


class CioSpProvider(_SAMVehicleProvider):
    """NIH CIO-SP3/CIO-SP4 contract vehicle opportunities via SAM.gov."""

    provider_name = "cio_sp3"
    display_name = "CIO-SP3"
    description = "NIH CIO-SP3 contract vehicle opportunities"
    organization_id = "100000116"  # HHS/NIH org ID
    vehicle_keyword = "CIO-SP"


class ITESProvider(_SAMVehicleProvider):
    """Army ITES contract vehicle opportunities via SAM.gov."""

    provider_name = "ites"
    display_name = "ITES"
    description = "Army ITES contract vehicle opportunities"
    organization_id = "100000180"  # Army org ID
    vehicle_keyword = "ITES"


class OasisProvider(_SAMVehicleProvider):
    """OASIS+ professional services opportunities via SAM.gov."""

    provider_name = "oasis"
    display_name = "OASIS+"
    description = "OASIS+ professional services opportunities"
    organization_id = "100006688"  # GSA org ID
    vehicle_keyword = "OASIS"
