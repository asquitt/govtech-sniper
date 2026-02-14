"""
Canada Buy and Sell Provider
=============================
Fetches procurement opportunities from the official CanadaBuys open-data feed.
"""

import httpx
import structlog

from app.services.data_providers.base import (
    DataSourceProvider,
    ProviderMaturity,
    RawOpportunity,
    SearchParams,
)
from app.services.data_providers.canada_open_data import (
    OPEN_TENDERS_CSV_URL,
    fetch_canadabuys_rows,
    row_to_opportunity,
)

logger = structlog.get_logger(__name__)


class CanadaBuyAndSellProvider(DataSourceProvider):
    """Provider for Canadian federal procurement opportunities."""

    provider_name = "canada_buyandsell"
    display_name = "Canada Buy & Sell"
    description = "Canadian federal procurement opportunities from CanadaBuys open data"
    is_active = True
    maturity = ProviderMaturity.LIVE
    record_count_estimate = 75_000

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        try:
            rows = await fetch_canadabuys_rows(params=params, provincial_only=False)
        except httpx.HTTPError as exc:
            logger.error("canada_buyandsell.search failed", error=str(exc))
            return []
        return [
            row_to_opportunity(
                row,
                source_type=self.provider_name,
                include_portal_metadata=False,
            )
            for row in rows
        ]

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        search_params = SearchParams(limit=250, keywords=None, agency=None, days_back=3650)
        try:
            rows = await fetch_canadabuys_rows(params=search_params, provincial_only=False)
        except httpx.HTTPError as exc:
            logger.error("canada_buyandsell.get_details failed", error=str(exc))
            return None

        target_id = opportunity_id.removeprefix("CA-")
        for row in rows:
            opportunity = row_to_opportunity(
                row,
                source_type=self.provider_name,
                include_portal_metadata=False,
            )
            if (
                opportunity.external_id == opportunity_id
                or opportunity.external_id == f"CA-{target_id}"
            ):
                return opportunity
        return None

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(OPEN_TENDERS_CSV_URL)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
