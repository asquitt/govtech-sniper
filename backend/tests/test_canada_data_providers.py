"""
Canada data provider tests
==========================
Regression coverage for CanadaBuys and provincial provider mapping.
"""

import pytest

from app.services.data_providers.base import SearchParams
from app.services.data_providers.canada_buyandsell import CanadaBuyAndSellProvider
from app.services.data_providers.canada_open_data import row_to_opportunity
from app.services.data_providers.canada_provincial import CanadaProvincialPortalsProvider


def _sample_row() -> dict[str, str]:
    return {
        "title-titre-eng": "Provincial Security Operations Centre",
        "title-titre-fra": "",
        "referenceNumber-numeroReference": "cb-01-123456",
        "solicitationNumber-numeroSollicitation": "ON-SEC-2026-001",
        "publicationDate-datePublication": "2026-02-10",
        "tenderClosingDate-appelOffresDateCloture": "2026-03-12T16:00:00",
        "tenderStatus-appelOffresStatut-eng": "Open",
        "gsin-nibs": "541512",
        "unspsc": "81161700",
        "contractingEntityName-nomEntitContractante-eng": "Ontario Shared Services",
        "contractingEntityAddressProvince-entiteContractanteAdresseProvince-eng": "Ontario",
        "noticeURL-URLavis-eng": "https://ontariotenders.bravosolution.com/opportunity/123",
        "tenderDescription-descriptionAppelOffres-eng": "Managed SOC and SIEM services.",
        "regionsOfOpportunity-regionAppelOffres-eng": "Ontario",
        "regionsOfDelivery-regionsLivraison-eng": "Ontario",
    }


def test_row_to_opportunity_includes_province_jurisdiction():
    opportunity = row_to_opportunity(
        _sample_row(),
        source_type="canada_buyandsell",
        include_portal_metadata=False,
    )
    assert opportunity.external_id == "CA-cb-01-123456"
    assert opportunity.jurisdiction == "CA-ON"
    assert opportunity.currency == "CAD"
    assert opportunity.source_type == "canada_buyandsell"


def test_row_to_opportunity_adds_portal_metadata_for_provincial_provider():
    opportunity = row_to_opportunity(
        _sample_row(),
        source_type="canada_provincial",
        include_portal_metadata=True,
    )
    assert opportunity.jurisdiction == "CA-ON"
    assert opportunity.source_type == "canada_provincial"
    assert opportunity.raw_data is not None
    urls = opportunity.raw_data.get("provincial_portal_urls")
    assert isinstance(urls, dict)
    assert urls.get("ON") == "https://ontariotenders.bravosolution.com/"


@pytest.mark.asyncio
async def test_canada_buyandsell_provider_maps_rows(monkeypatch):
    provider = CanadaBuyAndSellProvider()

    async def fake_fetch(*, params, provincial_only):  # noqa: ANN001
        assert isinstance(params, SearchParams)
        assert provincial_only is False
        return [_sample_row()]

    monkeypatch.setattr(
        "app.services.data_providers.canada_buyandsell.fetch_canadabuys_rows",
        fake_fetch,
    )

    results = await provider.search(SearchParams(limit=5))
    assert len(results) == 1
    assert results[0].source_type == "canada_buyandsell"
    assert results[0].jurisdiction == "CA-ON"


@pytest.mark.asyncio
async def test_canada_provincial_provider_maps_rows(monkeypatch):
    provider = CanadaProvincialPortalsProvider()

    async def fake_fetch(*, params, provincial_only):  # noqa: ANN001
        assert isinstance(params, SearchParams)
        assert provincial_only is True
        return [_sample_row()]

    monkeypatch.setattr(
        "app.services.data_providers.canada_provincial.fetch_canadabuys_rows",
        fake_fetch,
    )

    results = await provider.search(SearchParams(limit=5))
    assert len(results) == 1
    assert results[0].source_type == "canada_provincial"
    assert results[0].jurisdiction == "CA-ON"
    assert results[0].raw_data is not None
    assert "provincial_portal_urls" in results[0].raw_data
