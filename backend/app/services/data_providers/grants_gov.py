"""
Grants.gov Data Provider
=========================
Fetches federal grant opportunities from the Grants.gov REST API.
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

GRANTS_GOV_BASE_URL = "https://www.grants.gov/grantsws/rest/opportunities/search"
GRANTS_GOV_DETAIL_URL = "https://www.grants.gov/grantsws/rest/opportunity/details"


class GrantsGovProvider(DataSourceProvider):
    """Provider for federal grant opportunities from Grants.gov."""

    provider_name = "grants_gov"
    display_name = "Grants.gov"
    description = "Federal grants and cooperative agreements"
    is_active = True
    maturity = ProviderMaturity.HYBRID

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        payload: dict = {
            "startRecordNum": 0,
            "rows": min(params.limit, 100),
            "sortBy": "openDate|desc",
            "oppStatuses": "posted",
        }
        if params.keywords:
            payload["keyword"] = params.keywords
        if params.naics_codes:
            # Grants.gov uses CFDA, but we pass naics as a keyword filter
            payload["keyword"] = (
                f"{payload.get('keyword', '')} {' '.join(params.naics_codes)}".strip()
            )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(GRANTS_GOV_BASE_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("grants_gov.search failed", error=str(exc))
            return []

        hits = data.get("oppHits", [])
        return [_map_grant_to_raw(hit) for hit in hits]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(GRANTS_GOV_DETAIL_URL, params={"oppId": opportunity_id})
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("grants_gov.get_details failed", error=str(exc))
            return None

        if not data:
            return None
        return _map_grant_to_raw(data)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    GRANTS_GOV_BASE_URL,
                    json={"startRecordNum": 0, "rows": 1, "oppStatuses": "posted"},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _map_grant_to_raw(item: dict) -> RawOpportunity:
    opp_id = str(item.get("id", item.get("oppId", item.get("number", ""))))
    title = item.get("title", item.get("oppTitle", "Untitled"))
    agency = item.get("agency", item.get("agencyName"))
    description = item.get("description", item.get("synopsis"))
    posted = item.get("openDate", item.get("postedDate"))
    deadline = item.get("closeDate", item.get("closeDateExplanation"))
    award_ceiling = item.get("awardCeiling")
    estimated = float(award_ceiling) if award_ceiling else None
    cfda = item.get("cfdaNumber", item.get("cfda"))
    url = f"https://www.grants.gov/search-results-detail/{opp_id}" if opp_id else None

    return RawOpportunity(
        external_id=opp_id,
        title=title,
        agency=agency,
        description=description,
        posted_date=posted,
        response_deadline=deadline,
        estimated_value=estimated,
        naics_code=cfda,  # CFDA number (not NAICS) — grants use Assistance Listings
        source_url=url,
        source_type="grants_gov",
        raw_data=item,
    )
