"""
Data Source Provider - Base Classes
====================================
Abstract base class and shared data models for all procurement data providers.
"""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class SearchParams(BaseModel):
    """Parameters for searching opportunities across any provider."""
    keywords: Optional[str] = None
    naics_codes: Optional[list[str]] = None
    agency: Optional[str] = None
    days_back: int = 90
    limit: int = 25


class RawOpportunity(BaseModel):
    """Normalized opportunity record from any data source."""
    external_id: str
    title: str
    agency: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    response_deadline: Optional[str] = None
    estimated_value: Optional[float] = None
    naics_code: Optional[str] = None
    source_url: Optional[str] = None
    source_type: str
    raw_data: Optional[dict] = None


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
    async def get_details(self, opportunity_id: str) -> Optional[RawOpportunity]:
        """Fetch detailed information for a single opportunity."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider API is reachable and functional."""
        ...
