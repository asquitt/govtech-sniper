"""
Stub Data Providers
====================
Placeholder providers for future data sources (SLED, DIBBS, GWAC).
Return empty results with is_active=False.
"""

from typing import Optional

from app.services.data_providers.base import (
    DataSourceProvider,
    RawOpportunity,
    SearchParams,
)


class SLEDProvider(DataSourceProvider):
    """State/Local/Education procurement — coming soon."""

    provider_name = "sled"
    display_name = "SLED (State & Local)"
    description = "State, local, and education procurement opportunities — coming soon"
    is_active = False

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        return []

    async def get_details(self, opportunity_id: str) -> Optional[RawOpportunity]:
        return None

    async def health_check(self) -> bool:
        return False


class DIBBSProvider(DataSourceProvider):
    """DLA Internet Bid Board System — coming soon."""

    provider_name = "dibbs"
    display_name = "DIBBS"
    description = "DLA Internet Bid Board System for defense logistics — coming soon"
    is_active = False

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        return []

    async def get_details(self, opportunity_id: str) -> Optional[RawOpportunity]:
        return None

    async def health_check(self) -> bool:
        return False


class GWACProvider(DataSourceProvider):
    """Government-Wide Acquisition Contracts — coming soon."""

    provider_name = "gwac"
    display_name = "GWAC"
    description = "Government-Wide Acquisition Contract vehicles — coming soon"
    is_active = False

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        return []

    async def get_details(self, opportunity_id: str) -> Optional[RawOpportunity]:
        return None

    async def health_check(self) -> bool:
        return False
