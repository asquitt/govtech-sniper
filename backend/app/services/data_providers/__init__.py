"""
Data Source Provider Registry
==============================
Central registry for all procurement data source providers.
"""

from app.services.data_providers.base import (
    DataSourceProvider,
    ProviderMaturity,
    RawOpportunity,
    SearchParams,
)
from app.services.data_providers.canada_buyandsell import CanadaBuyAndSellProvider
from app.services.data_providers.canada_provincial import CanadaProvincialPortalsProvider
from app.services.data_providers.contract_vehicle_feeds import (
    CioSpProvider,
    GsaMasProvider,
    ITESProvider,
    OasisProvider,
)
from app.services.data_providers.dibbs import DIBBSProvider
from app.services.data_providers.fpds import FPDSProvider
from app.services.data_providers.grants_gov import GrantsGovProvider
from app.services.data_providers.gsa_ebuy import GSAEbuyProvider
from app.services.data_providers.sewp import SEWPProvider
from app.services.data_providers.sled_bidnet import SLEDBidNetProvider
from app.services.data_providers.usaspending import USAspendingProvider

_PROVIDERS: dict[str, DataSourceProvider] = {
    "gsa_ebuy": GSAEbuyProvider(),
    "fpds": FPDSProvider(),
    "usaspending": USAspendingProvider(),
    "sewp": SEWPProvider(),
    "gsa_mas": GsaMasProvider(),
    "cio_sp3": CioSpProvider(),
    "ites": ITESProvider(),
    "oasis": OasisProvider(),
    "sled_bidnet": SLEDBidNetProvider(),
    "dibbs": DIBBSProvider(),
    "grants_gov": GrantsGovProvider(),
    "canada_buyandsell": CanadaBuyAndSellProvider(),
    "canada_provincial": CanadaProvincialPortalsProvider(),
}


def get_provider(name: str) -> DataSourceProvider | None:
    """Look up a provider by name. Returns None if not found."""
    return _PROVIDERS.get(name)


def list_providers() -> list[DataSourceProvider]:
    """Return all registered providers."""
    return list(_PROVIDERS.values())


__all__ = [
    "DataSourceProvider",
    "ProviderMaturity",
    "RawOpportunity",
    "SearchParams",
    "get_provider",
    "list_providers",
]
