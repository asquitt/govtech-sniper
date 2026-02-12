"""
SLED BidNet Provider
====================
Fetches state/local/education opportunities from BidNet Direct's public search.
"""

import httpx
import structlog

from app.services.data_providers.base import DataSourceProvider, RawOpportunity, SearchParams

logger = structlog.get_logger(__name__)

BIDNET_SEARCH_URL = "https://www.bidnetdirect.com/api/search/solicitations"


class SLEDBidNetProvider(DataSourceProvider):
    """Provider for SLED opportunities sourced from BidNet Direct."""

    provider_name = "sled_bidnet"
    display_name = "SLED (BidNet)"
    description = "State, local, and education solicitations from BidNet Direct"
    is_active = True

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        query_params: dict = {
            "pageSize": min(params.limit, 50),
            "page": 1,
            "status": "open",
        }
        if params.keywords:
            query_params["searchText"] = params.keywords
        if params.agency:
            query_params["buyerName"] = params.agency

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(BIDNET_SEARCH_URL, params=query_params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("sled_bidnet.search failed", error=str(exc))
            return []

        items = data.get("results", data.get("solicitations", []))
        return [_map_bidnet(item) for item in items]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        url = f"https://www.bidnetdirect.com/api/solicitations/{opportunity_id}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("sled_bidnet.get_details failed", error=str(exc))
            return None

        if not data:
            return None
        return _map_bidnet(data)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    BIDNET_SEARCH_URL, params={"pageSize": 1, "page": 1, "status": "open"}
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _map_bidnet(item: dict) -> RawOpportunity:
    sol_id = str(item.get("solicitationId", item.get("id", "")))
    return RawOpportunity(
        external_id=f"SLED-{sol_id}",
        title=item.get("title", item.get("solicitationTitle", "Untitled")),
        agency=item.get("buyerName", item.get("agency")),
        description=item.get("description", item.get("summary")),
        posted_date=item.get("publishedDate", item.get("postedDate")),
        response_deadline=item.get("closingDate", item.get("responseDeadline")),
        estimated_value=item.get("estimatedValue"),
        naics_code=item.get("naicsCode"),
        source_url=f"https://www.bidnetdirect.com/solicitations/{sol_id}",
        source_type="sled",
        raw_data=item,
    )
