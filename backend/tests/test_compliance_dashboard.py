"""Integration tests for compliance dashboard endpoints."""

import pytest
from httpx import AsyncClient


class TestComplianceDashboard:
    @pytest.mark.asyncio
    async def test_readiness_endpoint_returns_programs(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/compliance/readiness", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["programs"]
        ids = {item["id"] for item in payload["programs"]}
        assert {
            "fedramp_moderate",
            "cmmc_level_2",
            "govcloud_deployment",
            "salesforce_appexchange",
            "microsoft_appsource",
        }.issubset(ids)
