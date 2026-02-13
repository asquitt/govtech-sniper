"""
DIBBS Provider
==============
Fetches Defense Logistics Agency procurement opportunities from the DIBBS portal.
Uses the DLA's public bid board search API.
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

DIBBS_BASE_URL = "https://www.dibbs.bsm.dla.mil"
DIBBS_SEARCH_URL = f"{DIBBS_BASE_URL}/api/search"


class DIBBSProvider(DataSourceProvider):
    """Provider for Defense Logistics Agency DIBBS opportunities."""

    provider_name = "dibbs"
    display_name = "DIBBS"
    description = "Defense Logistics Agency procurement opportunities"
    is_active = True
    maturity = ProviderMaturity.HYBRID

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        query_params: dict = {
            "rows": min(params.limit, 100),
            "start": 0,
            "type": "rfp,rfq",
        }
        if params.keywords:
            query_params["q"] = params.keywords
        if params.naics_codes:
            query_params["naics"] = ",".join(params.naics_codes)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(DIBBS_SEARCH_URL, params=query_params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("dibbs.search failed", error=str(exc))
            return []

        items = data.get("results", data.get("docs", []))
        return [_map_dibbs(item) for item in items]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        url = f"{DIBBS_BASE_URL}/api/solicitation/{opportunity_id}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("dibbs.get_details failed", error=str(exc))
            return None

        if not data:
            return None
        return _map_dibbs(data)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(DIBBS_SEARCH_URL, params={"rows": 1, "start": 0})
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _map_dibbs(item: dict) -> RawOpportunity:
    sol_num = item.get("solicitationNumber", item.get("rfqNumber", item.get("id", "")))
    return RawOpportunity(
        external_id=f"DIBBS-{sol_num}",
        title=item.get("title", item.get("description", "Untitled")),
        agency=item.get("agency", "Defense Logistics Agency"),
        description=item.get("description"),
        posted_date=item.get("postedDate", item.get("publishDate")),
        response_deadline=item.get("closingDate", item.get("responseDeadline")),
        estimated_value=item.get("estimatedValue"),
        naics_code=item.get("naicsCode"),
        source_url=item.get("url", f"{DIBBS_BASE_URL}/RFQ/{sol_num}"),
        source_type="dibbs",
        raw_data=item,
    )
