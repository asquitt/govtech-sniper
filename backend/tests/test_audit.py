"""
RFP Sniper - Audit Tests
========================
Tests for audit log endpoints.
"""

import pytest
from httpx import AsyncClient


class TestAudit:
    @pytest.mark.asyncio
    async def test_audit_list_and_summary(self, client: AsyncClient, auth_headers: dict):
        # Generate an audit event
        response = await client.post(
            "/api/v1/integrations",
            headers=auth_headers,
            json={
                "provider": "okta",
                "name": "Okta SSO",
                "config": {"domain": "example.okta.com"},
            },
        )
        assert response.status_code == 200

        response = await client.get("/api/v1/audit", headers=auth_headers)
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert any(event["action"] == "integration.created" for event in events)

        response = await client.get("/api/v1/audit/summary", headers=auth_headers)
        assert response.status_code == 200
        summary = response.json()
        assert summary["total_events"] >= 1
        assert any(item["action"] == "integration.created" for item in summary["by_action"])

        response = await client.get(
            "/api/v1/audit/export",
            headers=auth_headers,
            params={"format": "json"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "signature" in payload
        assert "payload" in payload

        response = await client.get(
            "/api/v1/audit/export",
            headers=auth_headers,
            params={"format": "csv"},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Audit-Signature")
