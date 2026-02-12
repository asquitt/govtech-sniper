"""
Canada Buy and Sell Provider
=============================
Fetches procurement opportunities from Canada's buyandsell.gc.ca open data API.
"""

import httpx
import structlog

from app.services.data_providers.base import DataSourceProvider, RawOpportunity, SearchParams

logger = structlog.get_logger(__name__)

BUYANDSELL_API_URL = "https://buyandsell.gc.ca/procurement-data/api/search/tender"


class CanadaBuyAndSellProvider(DataSourceProvider):
    """Provider for Canadian federal procurement opportunities."""

    provider_name = "canada_buyandsell"
    display_name = "Canada Buy & Sell"
    description = "Canadian federal procurement opportunities from buyandsell.gc.ca"
    is_active = True

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        query_params: dict = {
            "limit": min(params.limit, 100),
            "offset": 0,
            "status": "open",
        }
        if params.keywords:
            query_params["search"] = params.keywords
        if params.agency:
            query_params["department"] = params.agency

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(BUYANDSELL_API_URL, params=query_params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("canada_buyandsell.search failed", error=str(exc))
            return []

        items = data.get("results", data.get("tenders", []))
        return [_map_tender(item) for item in items]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        url = f"{BUYANDSELL_API_URL}/{opportunity_id}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("canada_buyandsell.get_details failed", error=str(exc))
            return None

        if not data:
            return None
        return _map_tender(data)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    BUYANDSELL_API_URL, params={"limit": 1, "offset": 0, "status": "open"}
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _map_tender(item: dict) -> RawOpportunity:
    tender_id = str(item.get("referenceNumber", item.get("id", "")))
    return RawOpportunity(
        external_id=f"CA-{tender_id}",
        title=item.get("title", item.get("description", "Untitled")),
        agency=item.get("department", item.get("organizationName")),
        description=item.get("description"),
        posted_date=item.get("publishDate", item.get("publicationDate")),
        response_deadline=item.get("closingDate", item.get("deadlineDate")),
        estimated_value=item.get("estimatedValue"),
        naics_code=item.get("gsinCode"),  # Canada uses GSIN, map to NAICS if available
        source_url=item.get(
            "url", f"https://buyandsell.gc.ca/procurement-data/tender-notice/{tender_id}"
        ),
        source_type="canada_buyandsell",
        raw_data=item,
    )
