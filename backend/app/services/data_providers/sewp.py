"""
NASA SEWP V Data Provider
==========================
Fetches IT procurement opportunities from NASA SEWP V catalog.
SEWP (Solutions for Enterprise-Wide Procurement) is a multi-award GWAC
for IT products and services.
"""

import httpx
import structlog

from app.services.data_providers.base import (
    DataSourceProvider,
    ProviderMaturity,
    RawOpportunity,
    SearchParams,
)

logger = structlog.get_logger(__name__)

SEWP_BASE_URL = "https://www.sewp.nasa.gov/sewpapi"
SEWP_SEARCH_URL = f"{SEWP_BASE_URL}/search/rfq"


class SEWPProvider(DataSourceProvider):
    """Provider for NASA SEWP V IT procurement opportunities."""

    provider_name = "sewp"
    display_name = "NASA SEWP V"
    description = "NASA SEWP V IT hardware, software, and services procurements"
    is_active = True
    maturity = ProviderMaturity.HYBRID

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        query_params: dict = {
            "limit": min(params.limit, 100),
            "offset": 0,
        }
        if params.keywords:
            query_params["keyword"] = params.keywords
        if params.naics_codes:
            query_params["naics"] = ",".join(params.naics_codes)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(SEWP_SEARCH_URL, params=query_params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("sewp.search failed", error=str(exc))
            return []

        items = data.get("results", data.get("rfqs", []))
        return [_map_sewp_to_raw(item) for item in items]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        url = f"{SEWP_BASE_URL}/rfq/{opportunity_id}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("sewp.get_details failed", error=str(exc))
            return None

        if not data:
            return None
        return _map_sewp_to_raw(data)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(SEWP_SEARCH_URL, params={"limit": 1, "offset": 0})
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _map_sewp_to_raw(item: dict) -> RawOpportunity:
    return RawOpportunity(
        external_id=item.get("rfqNumber", item.get("id", "")),
        title=item.get("title", item.get("description", "Untitled")),
        agency=item.get("agency", "NASA"),
        description=item.get("description"),
        posted_date=item.get("postedDate", item.get("publishDate")),
        response_deadline=item.get("closeDate", item.get("responseDeadline")),
        estimated_value=item.get("estimatedValue"),
        naics_code=item.get("naicsCode"),
        source_url=item.get("url"),
        source_type="sewp",
        raw_data=item,
    )
