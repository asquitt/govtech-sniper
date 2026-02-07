"""
Canada Buy and Sell Provider
==============================
Stub provider for Canadian procurement via buyandsell.gc.ca.
"""

from typing import Optional

from app.services.data_providers.base import (
    DataSourceProvider,
    RawOpportunity,
    SearchParams,
)


class CanadaProvider(DataSourceProvider):
    """Canadian Government procurement (buyandsell.gc.ca) -- coming soon."""

    provider_name = "buyandsell_gc"
    display_name = "Canada Buy & Sell"
    description = "Canadian federal procurement opportunities via buyandsell.gc.ca"
    is_active = False

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        raise NotImplementedError(
            "Canada Buy & Sell provider coming soon. "
            "This provider will support searching Canadian federal procurement."
        )

    async def get_details(self, opportunity_id: str) -> Optional[RawOpportunity]:
        raise NotImplementedError(
            "Canada Buy & Sell provider coming soon. "
            "Detail retrieval is not yet implemented."
        )

    async def health_check(self) -> bool:
        raise NotImplementedError(
            "Canada Buy & Sell provider coming soon. "
            "Health check is not yet available."
        )
