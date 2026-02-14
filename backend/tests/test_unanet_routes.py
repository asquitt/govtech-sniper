"""
RFP Sniper - Unanet route integration tests
===========================================
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.integration import IntegrationConfig, IntegrationProvider
from app.models.user import User
from app.services.unanet_service import UnanetServiceError


async def _create_unanet_integration(
    db_session: AsyncSession,
    user_id: int,
    *,
    include_resource_financial_endpoints: bool = False,
) -> IntegrationConfig:
    config_payload = {
        "base_url": "https://unanet.example.com",
        "api_key": "test-key",
        "projects_endpoint": "/api/projects",
        "sync_endpoint": "/api/sync",
    }
    if include_resource_financial_endpoints:
        config_payload["resources_endpoint"] = "/api/resources"
        config_payload["financials_endpoint"] = "/api/financials"

    integration = IntegrationConfig(
        user_id=user_id,
        provider=IntegrationProvider.UNANET,
        is_enabled=True,
        config=config_payload,
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


class TestUnanetRoutes:
    @pytest.mark.asyncio
    async def test_unanet_status_not_configured(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/unanet/status", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"configured": False, "enabled": False}

    @pytest.mark.asyncio
    async def test_unanet_status_and_projects(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        monkeypatch,
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _create_unanet_integration(db_session, user.id)

        async def fake_health(self):
            return True

        async def fake_projects(self):
            return [
                {
                    "id": "P-100",
                    "name": "Mission Support",
                    "status": "active",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "budget": 1500000.0,
                    "percent_complete": 42,
                }
            ]

        monkeypatch.setattr("app.services.unanet_service.UnanetService.health_check", fake_health)
        monkeypatch.setattr(
            "app.services.unanet_service.UnanetService.list_projects", fake_projects
        )

        status_response = await client.get("/api/v1/unanet/status", headers=auth_headers)
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["configured"] is True
        assert status_payload["enabled"] is True
        assert status_payload["healthy"] is True
        assert status_payload["resources_supported"] is False
        assert status_payload["financials_supported"] is False

        projects_response = await client.get("/api/v1/unanet/projects", headers=auth_headers)
        assert projects_response.status_code == 200
        projects_payload = projects_response.json()
        assert len(projects_payload) == 1
        assert projects_payload[0]["id"] == "P-100"
        assert projects_payload[0]["percent_complete"] == 42

    @pytest.mark.asyncio
    async def test_unanet_resources_and_financials(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        monkeypatch,
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _create_unanet_integration(db_session, user.id)

        async def fake_resources(self):
            return [
                {
                    "id": "LAB-1",
                    "labor_category": "Engineer III",
                    "role": "engineering",
                    "hourly_rate": 185.0,
                    "cost_rate": 132.0,
                    "currency": "USD",
                    "availability_hours": 140.0,
                    "source_project_id": "P-100",
                    "effective_date": "2026-02-01",
                    "is_active": True,
                }
            ]

        async def fake_financials(self):
            return [
                {
                    "id": "FIN-1",
                    "project_id": "P-100",
                    "project_name": "Mission Support",
                    "fiscal_year": 2026,
                    "booked_revenue": 1200000.0,
                    "funded_value": 1500000.0,
                    "invoiced_to_date": 600000.0,
                    "remaining_value": 900000.0,
                    "burn_rate_percent": 40.0,
                    "currency": "USD",
                    "status": "active",
                    "as_of_date": "2026-02-28",
                }
            ]

        monkeypatch.setattr(
            "app.services.unanet_service.UnanetService.list_resources", fake_resources
        )
        monkeypatch.setattr(
            "app.services.unanet_service.UnanetService.list_financials", fake_financials
        )

        resources_response = await client.get("/api/v1/unanet/resources", headers=auth_headers)
        assert resources_response.status_code == 200
        resources_payload = resources_response.json()
        assert len(resources_payload) == 1
        assert resources_payload[0]["labor_category"] == "Engineer III"

        financials_response = await client.get("/api/v1/unanet/financials", headers=auth_headers)
        assert financials_response.status_code == 200
        financials_payload = financials_response.json()
        assert len(financials_payload) == 1
        assert financials_payload[0]["funded_value"] == 1500000.0

    @pytest.mark.asyncio
    async def test_unanet_sync_handles_upstream_errors(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        monkeypatch,
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _create_unanet_integration(db_session, user.id)

        async def fake_sync_error(self):
            raise UnanetServiceError("Upstream Unanet outage")

        monkeypatch.setattr(
            "app.services.unanet_service.UnanetService.sync_projects", fake_sync_error
        )

        response = await client.post("/api/v1/unanet/sync", headers=auth_headers)
        assert response.status_code == 502
        assert "Upstream Unanet outage" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_unanet_resource_and_financial_sync_endpoints(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        monkeypatch,
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _create_unanet_integration(db_session, user.id)

        async def fake_sync_resources(self):
            return {
                "status": "success",
                "resources_synced": 5,
                "errors": [],
                "synced_at": "2026-02-14T10:00:00Z",
            }

        async def fake_sync_financials(self):
            return {
                "status": "success",
                "records_synced": 3,
                "total_funded_value": 4400000.0,
                "errors": [],
                "synced_at": "2026-02-14T10:00:00Z",
            }

        monkeypatch.setattr(
            "app.services.unanet_service.UnanetService.sync_resources",
            fake_sync_resources,
        )
        monkeypatch.setattr(
            "app.services.unanet_service.UnanetService.sync_financials",
            fake_sync_financials,
        )

        resource_sync_response = await client.post(
            "/api/v1/unanet/sync/resources",
            headers=auth_headers,
        )
        assert resource_sync_response.status_code == 200
        assert resource_sync_response.json()["resources_synced"] == 5

        financial_sync_response = await client.post(
            "/api/v1/unanet/sync/financials",
            headers=auth_headers,
        )
        assert financial_sync_response.status_code == 200
        assert financial_sync_response.json()["records_synced"] == 3

    @pytest.mark.asyncio
    async def test_unanet_status_reports_supported_resource_and_financial_endpoints(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        monkeypatch,
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _create_unanet_integration(
            db_session,
            user.id,
            include_resource_financial_endpoints=True,
        )

        async def fake_health(self):
            return True

        monkeypatch.setattr("app.services.unanet_service.UnanetService.health_check", fake_health)

        status_response = await client.get("/api/v1/unanet/status", headers=auth_headers)
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["resources_supported"] is True
        assert status_payload["financials_supported"] is True
