"""
Data Source Provider Registry
==============================
Central registry for all procurement data source providers.
"""

from app.services.data_providers.base import (
    DataSourceProvider,
    RawOpportunity,
    SearchParams,
)
from app.services.data_providers.fpds import FPDSProvider
from app.services.data_providers.gsa_ebuy import GSAEbuyProvider
from app.services.data_providers.usaspending import USAspendingProvider

_PROVIDERS: dict[str, DataSourceProvider] = {
    "gsa_ebuy": GSAEbuyProvider(),
    "fpds": FPDSProvider(),
    "usaspending": USAspendingProvider(),
}


def get_provider(name: str) -> DataSourceProvider | None:
    """Look up a provider by name. Returns None if not found."""
    return _PROVIDERS.get(name)


def list_providers() -> list[DataSourceProvider]:
    """Return all registered providers."""
    return list(_PROVIDERS.values())


__all__ = [
    "DataSourceProvider",
    "RawOpportunity",
    "SearchParams",
    "get_provider",
    "list_providers",
]
