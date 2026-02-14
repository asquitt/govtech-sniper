"""
RFP Sniper - Unanet service unit tests
======================================
"""

import pytest

from app.models.integration import IntegrationConfig, IntegrationProvider
from app.services.unanet_service import (
    UnanetService,
    _extract_synced_count,
    _normalize_financial_record,
    _normalize_project,
    _normalize_resource,
)


def _integration_config(sync_endpoint: str | None = "/api/sync") -> IntegrationConfig:
    return IntegrationConfig(
        user_id=1,
        provider=IntegrationProvider.UNANET,
        is_enabled=True,
        config={
            "base_url": "https://unanet.example.com",
            "api_key": "test-key",
            "projects_endpoint": "/api/projects",
            "sync_endpoint": sync_endpoint,
        },
    )


class TestUnanetService:
    def test_normalize_project_supports_alternate_field_names(self):
        normalized = _normalize_project(
            {
                "projectNumber": "PRJ-77",
                "project_name": "Acquisition Support",
                "state": "in_progress",
                "startDate": "2026-01-10T00:00:00Z",
                "endDate": "2026-06-30T00:00:00Z",
                "totalBudget": "2500000",
                "completion": 61,
            }
        )
        assert normalized["id"] == "PRJ-77"
        assert normalized["name"] == "Acquisition Support"
        assert normalized["status"] == "in_progress"
        assert normalized["start_date"] == "2026-01-10"
        assert normalized["end_date"] == "2026-06-30"
        assert normalized["budget"] == 2500000.0
        assert normalized["percent_complete"] == 61

    @pytest.mark.asyncio
    async def test_sync_projects_uses_sync_endpoint_count(self, monkeypatch):
        service = UnanetService(_integration_config(sync_endpoint="/api/sync"))

        async def fake_request(*_args, **_kwargs):
            return {"items_synced": 7}

        monkeypatch.setattr(service, "_request", fake_request)
        result = await service.sync_projects()
        assert result["status"] == "success"
        assert result["projects_synced"] == 7
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_sync_projects_falls_back_to_project_count(self, monkeypatch):
        service = UnanetService(_integration_config(sync_endpoint=None))

        async def fake_list_projects():
            return [{"id": "A"}, {"id": "B"}, {"id": "C"}]

        monkeypatch.setattr(service, "list_projects", fake_list_projects)
        result = await service.sync_projects()
        assert result["status"] == "success"
        assert result["projects_synced"] == 3

    def test_extract_synced_count_from_record_list(self):
        count = _extract_synced_count({"projects": [{"id": 1}, {"id": 2}]})
        assert count == 2

    def test_normalize_resource_supports_alternate_fields(self):
        normalized = _normalize_resource(
            {
                "resource_id": "LAB-55",
                "laborCategory": "Senior Engineer",
                "labor_role": "engineering",
                "bill_rate": "195.5",
                "costRate": "133.2",
                "available_hours": 160,
                "projectNumber": "P-22",
                "effectiveDate": "2026-03-01T00:00:00Z",
                "status": "active",
            }
        )
        assert normalized["id"] == "LAB-55"
        assert normalized["labor_category"] == "Senior Engineer"
        assert normalized["hourly_rate"] == 195.5
        assert normalized["cost_rate"] == 133.2
        assert normalized["availability_hours"] == 160.0
        assert normalized["source_project_id"] == "P-22"
        assert normalized["effective_date"] == "2026-03-01"
        assert normalized["is_active"] is True

    def test_normalize_financial_record_calculates_remaining_and_burn(self):
        normalized = _normalize_financial_record(
            {
                "transaction_id": "FIN-88",
                "contract_id": "P-88",
                "contract_name": "Ops Support",
                "fy": 2026,
                "revenue": "820000",
                "contract_value": "1200000",
                "actuals": "300000",
                "period_end": "2026-02-28T00:00:00Z",
            }
        )
        assert normalized["id"] == "FIN-88"
        assert normalized["project_id"] == "P-88"
        assert normalized["fiscal_year"] == 2026
        assert normalized["booked_revenue"] == 820000.0
        assert normalized["funded_value"] == 1200000.0
        assert normalized["invoiced_to_date"] == 300000.0
        assert normalized["remaining_value"] == 900000.0
        assert normalized["burn_rate_percent"] == 25.0
        assert normalized["as_of_date"] == "2026-02-28"

    @pytest.mark.asyncio
    async def test_sync_resources_uses_sync_endpoint_count(self, monkeypatch):
        config = _integration_config(sync_endpoint="/api/sync")
        config.config["resource_sync_endpoint"] = "/api/resources/sync"
        service = UnanetService(config)

        async def fake_request(*_args, **_kwargs):
            return {"synced": 4}

        monkeypatch.setattr(service, "_request", fake_request)
        result = await service.sync_resources()
        assert result["status"] == "success"
        assert result["resources_synced"] == 4
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_sync_financials_falls_back_to_records_and_sums_funded(self, monkeypatch):
        config = _integration_config(sync_endpoint=None)
        config.config["financial_sync_endpoint"] = None
        service = UnanetService(config)

        async def fake_list_financials():
            return [
                {"id": "A", "funded_value": 100000.0},
                {"id": "B", "funded_value": 250000.0},
            ]

        monkeypatch.setattr(service, "list_financials", fake_list_financials)
        result = await service.sync_financials()
        assert result["status"] == "success"
        assert result["records_synced"] == 2
        assert result["total_funded_value"] == 350000.0
