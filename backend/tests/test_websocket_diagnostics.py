"""
RFP Sniper - WebSocket diagnostics tests
========================================
Validates telemetry payload shape for websocket diagnostics runtime endpoint.
"""

import pytest
from httpx import AsyncClient


class TestWebsocketDiagnostics:
    @pytest.mark.asyncio
    async def test_websocket_diagnostics_requires_authentication(
        self,
        client: AsyncClient,
    ):
        response = await client.get("/api/v1/ws/diagnostics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_websocket_diagnostics_alerts_requires_authentication(
        self,
        client: AsyncClient,
    ):
        response = await client.get("/api/v1/ws/diagnostics/alerts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_websocket_diagnostics_export_requires_authentication(
        self,
        client: AsyncClient,
    ):
        response = await client.get("/api/v1/ws/diagnostics/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_websocket_diagnostics_snapshot_shape(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get("/api/v1/ws/diagnostics", headers=auth_headers)
        assert response.status_code == 200

        payload = response.json()
        assert "timestamp" in payload
        assert "connections" in payload
        assert "task_watch" in payload
        assert "event_throughput" in payload

        assert "reconnect_count" in payload["connections"]
        assert "avg_status_latency_ms" in payload["task_watch"]
        assert "inbound_events_per_minute" in payload["event_throughput"]
        assert "outbound_events_per_minute" in payload["event_throughput"]

    @pytest.mark.asyncio
    async def test_websocket_diagnostics_alerts_snapshot_shape(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get(
            "/api/v1/ws/diagnostics/alerts",
            headers=auth_headers,
            params={"include_all": True, "min_active_connection_count": 1},
        )
        assert response.status_code == 200

        payload = response.json()
        assert "timestamp" in payload
        assert "thresholds" in payload
        assert "alerts" in payload
        assert "telemetry" in payload
        assert "breached_count" in payload
        assert isinstance(payload["alerts"], list)
        if payload["alerts"]:
            first = payload["alerts"][0]
            assert "code" in first
            assert "metric" in first
            assert "breached" in first

    @pytest.mark.asyncio
    async def test_websocket_diagnostics_csv_export_contract(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.get(
            "/api/v1/ws/diagnostics/export",
            headers=auth_headers,
            params={"format": "csv", "include_alerts": True},
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert response.headers.get("content-disposition")
        assert "row_type,metric,value,alert_code,severity" in response.text
        assert "connections.active_connection_count" in response.text
