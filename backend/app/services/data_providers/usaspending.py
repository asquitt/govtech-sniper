"""
USAspending Data Provider
==========================
Fetches federal spending / award data from the USAspending.gov REST API.
"""


import httpx
import structlog

from app.services.data_providers.base import (
    DataSourceProvider,
    RawOpportunity,
    SearchParams,
)

logger = structlog.get_logger(__name__)

USASPENDING_BASE_URL = "https://api.usaspending.gov/api/v2"


class USAspendingProvider(DataSourceProvider):
    """Provider for USAspending.gov federal award data."""

    provider_name = "usaspending"
    display_name = "USAspending"
    description = "Federal award spending data from USAspending.gov"
    is_active = True

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        from datetime import datetime, timedelta

        start_date = (datetime.utcnow() - timedelta(days=params.days_back)).strftime("%Y-%m-%d")
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

        filters: dict = {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["A", "B", "C", "D"],  # Contracts only
        }
        if params.keywords:
            filters["keywords"] = [params.keywords]
        if params.naics_codes:
            filters["naics_codes"] = [{"code": c} for c in params.naics_codes]
        if params.agency:
            filters["agencies"] = [{"type": "funding", "tier": "toptier", "name": params.agency}]

        payload = {
            "filters": filters,
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Awarding Agency",
                "Start Date",
                "Description",
                "NAICS Code",
                "generated_internal_id",
            ],
            "limit": min(params.limit, 100),
            "page": 1,
            "sort": "Award Amount",
            "order": "desc",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{USASPENDING_BASE_URL}/search/spending_by_award/",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("usaspending.search failed", error=str(exc))
            return []

        results = data.get("results", [])
        return [_map_award(r) for r in results]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{USASPENDING_BASE_URL}/awards/{opportunity_id}/",
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("usaspending.get_details failed", error=str(exc))
            return None

        if not data:
            return None

        return RawOpportunity(
            external_id=data.get("generated_unique_award_id", opportunity_id),
            title=data.get("description", "Untitled"),
            agency=data.get("awarding_agency", {}).get("toptier_agency", {}).get("name"),
            description=data.get("description"),
            posted_date=data.get("period_of_performance_start_date"),
            response_deadline=None,
            estimated_value=_parse_float(data.get("total_obligation")),
            naics_code=data.get("naics", {}).get("code")
            if isinstance(data.get("naics"), dict)
            else None,
            source_url=f"https://www.usaspending.gov/award/{opportunity_id}",
            source_type="usaspending",
            raw_data=data,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{USASPENDING_BASE_URL}/references/filter_tree/psc/")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _map_award(record: dict) -> RawOpportunity:
    return RawOpportunity(
        external_id=record.get("generated_internal_id", record.get("Award ID", "")),
        title=record.get("Description") or record.get("Recipient Name") or "Untitled",
        agency=record.get("Awarding Agency"),
        description=record.get("Description"),
        posted_date=record.get("Start Date"),
        response_deadline=None,
        estimated_value=_parse_float(record.get("Award Amount")),
        naics_code=record.get("NAICS Code"),
        source_url=None,
        source_type="usaspending",
        raw_data=record,
    )


def _parse_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        return float(val)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None
