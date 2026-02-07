"""
Data Source Provider - Base Classes
====================================
Abstract base class and shared data models for all procurement data providers.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class SearchParams(BaseModel):
    """Parameters for searching opportunities across any provider."""

    keywords: str | None = None
    naics_codes: list[str] | None = None
    agency: str | None = None
    days_back: int = 90
    limit: int = 25


class RawOpportunity(BaseModel):
    """Normalized opportunity record from any data source."""

    external_id: str
    title: str
    agency: str | None = None
    description: str | None = None
    posted_date: str | None = None
    response_deadline: str | None = None
    estimated_value: float | None = None
    naics_code: str | None = None
    source_url: str | None = None
    source_type: str
    raw_data: dict | None = None


class DataSourceProvider(ABC):
    """Abstract base class for all procurement data source providers."""

    provider_name: str
    display_name: str
    description: str
    is_active: bool = True

    @abstractmethod
    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        """Search for opportunities matching the given parameters."""
        ...

    @abstractmethod
    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        """Fetch detailed information for a single opportunity."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider API is reachable and functional."""
        ...
