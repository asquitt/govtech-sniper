"""
RFP Sniper - Analytics Tests
============================
Tests for observability analytics endpoints.
"""

import pytest
from httpx import AsyncClient


class TestAnalytics:
    @pytest.mark.asyncio
    async def test_observability_metrics(self, client: AsyncClient, auth_headers: dict):
        # Create SharePoint integration
        response = await client.post(
            "/api/v1/integrations",
            headers=auth_headers,
            json={
                "provider": "sharepoint",
                "name": "SharePoint",
                "config": {
                    "site_url": "https://example.sharepoint.com/sites/demo",
                    "tenant_id": "tenant",
                    "client_id": "client",
                    "client_secret": "secret",
                },
            },
        )
        assert response.status_code == 200
        integration_id = response.json()["id"]

        # Trigger a sync
        response = await client.post(
            f"/api/v1/integrations/{integration_id}/sync",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200

        # Send webhook event
        response = await client.post(
            f"/api/v1/integrations/{integration_id}/webhook",
            headers=auth_headers,
            json={"event_type": "file.created", "document_id": "doc-99"},
        )
        assert response.status_code == 200

        # Fetch observability metrics
        response = await client.get("/api/v1/analytics/observability", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["integration_syncs"]["total"] >= 1
        assert data["webhook_events"]["total"] >= 1
