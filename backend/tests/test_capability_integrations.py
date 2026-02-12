"""
Regression coverage for capability integration endpoints used in live UI pages.
"""

import pytest
from httpx import AsyncClient


class TestCapabilityIntegrations:
    @pytest.mark.asyncio
    async def test_reports_list_returns_empty_array_for_new_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/reports", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_admin_endpoints_fail_with_403_not_500_without_org_membership(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        for path in (
            "/api/v1/admin/organization",
            "/api/v1/admin/members",
            "/api/v1/admin/usage",
            "/api/v1/admin/audit",
            "/api/v1/admin/capability-health",
        ):
            response = await client.get(path, headers=auth_headers)
            assert response.status_code == 403
            assert (
                "organization" in response.json()["detail"].lower()
                or "admin" in response.json()["detail"].lower()
            )

    @pytest.mark.asyncio
    async def test_admin_capability_health_returns_runtime_and_discoverability(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        create_org = await client.post(
            "/api/v1/admin/organizations",
            headers=auth_headers,
            json={
                "name": "Capability Org",
                "slug": "capability-org",
                "domain": "capability.example.com",
            },
        )
        assert create_org.status_code == 200

        response = await client.get("/api/v1/admin/capability-health", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()

        assert "runtime" in payload
        assert "workers" in payload
        assert "enterprise" in payload
        assert "discoverability" in payload
        assert isinstance(payload["discoverability"], list)
        assert "websocket" in payload["runtime"]
        assert payload["runtime"]["websocket"]["endpoint"] == "/api/v1/ws?token=<jwt>"
        assert "active_documents" in payload["runtime"]["websocket"]
        assert "presence_users" in payload["runtime"]["websocket"]
        assert "active_section_locks" in payload["runtime"]["websocket"]
        assert "active_cursors" in payload["runtime"]["websocket"]
        assert any(
            item["capability"] == "Template Marketplace" and item["frontend_path"] == "/templates"
            for item in payload["discoverability"]
        )
        assert any(
            item["capability"] == "Word Add-in" and item["frontend_path"] == "/word-addin"
            for item in payload["discoverability"]
        )
        assert any(
            item["capability"] == "WebSocket Task Feed"
            and item["frontend_path"] == "/diagnostics"
            and item["status"] == "integrated"
            for item in payload["discoverability"]
        )

    @pytest.mark.asyncio
    async def test_analytics_reporting_sqlite_compatibility(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        win_rate = await client.get("/api/v1/analytics/win-rate", headers=auth_headers)
        assert win_rate.status_code == 200
        assert "win_rate" in win_rate.json()
        assert "trend" in win_rate.json()

        turnaround = await client.get(
            "/api/v1/analytics/proposal-turnaround",
            headers=auth_headers,
        )
        assert turnaround.status_code == 200
        assert "overall_avg_days" in turnaround.json()
        assert "trend" in turnaround.json()

    @pytest.mark.asyncio
    async def test_intelligence_budget_sqlite_compatibility(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/intelligence/budget", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert "top_agencies" in payload
        assert "top_naics" in payload
        assert "budget_season" in payload
        assert "top_competitors" in payload
