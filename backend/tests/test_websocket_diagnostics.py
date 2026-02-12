"""
RFP Sniper - WebSocket diagnostics tests
========================================
Validates telemetry payload shape for websocket diagnostics runtime endpoint.
"""

import pytest
from httpx import AsyncClient


class TestWebsocketDiagnostics:
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
