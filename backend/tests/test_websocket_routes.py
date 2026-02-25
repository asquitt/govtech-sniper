"""
Integration tests for websocket.py — /api/v1/ws/ HTTP endpoints
(WebSocket connections are tested via the HTTP fallback endpoints.)
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


class TestWebSocketDiagnostics:
    """Tests for GET /api/v1/ws/diagnostics."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/ws/diagnostics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_diagnostics(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/ws/diagnostics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        assert "task_watch" in data
        assert "event_throughput" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_diagnostics_structure(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/ws/diagnostics", headers=auth_headers)
        data = response.json()
        conn = data["connections"]
        assert "active_user_channels" in conn
        assert "active_connection_count" in conn
        assert "total_connections" in conn
        assert "total_disconnects" in conn
        assert "reconnect_count" in conn


class TestWebSocketDiagnosticsAlerts:
    """Tests for GET /api/v1/ws/diagnostics/alerts."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/ws/diagnostics/alerts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_alerts_default(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/ws/diagnostics/alerts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data
        assert "alerts" in data
        assert "breached_count" in data
        assert "telemetry" in data

    @pytest.mark.asyncio
    async def test_alerts_include_all(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/ws/diagnostics/alerts?include_all=true", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # With include_all, should have all 6 alerts
        assert len(data["alerts"]) == 6

    @pytest.mark.asyncio
    async def test_alerts_custom_thresholds(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/ws/diagnostics/alerts?max_reconnect_count=0&include_all=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["thresholds"]["max_reconnect_count"] == 0


class TestWebSocketDiagnosticsExport:
    """Tests for GET /api/v1/ws/diagnostics/export."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/ws/diagnostics/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_json(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/ws/diagnostics/export?format=json", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "telemetry" in data
        assert "thresholds" in data

    @pytest.mark.asyncio
    async def test_export_csv(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/ws/diagnostics/export?format=csv", headers=auth_headers
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        # Should have CSV content with headers
        text = response.text
        assert "row_type" in text
        assert "metric" in text

    @pytest.mark.asyncio
    async def test_export_csv_with_alerts(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/ws/diagnostics/export?format=csv&include_alerts=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        text = response.text
        assert "alert" in text


class TestTaskStatusHTTP:
    """Tests for GET /api/v1/ws/task/{task_id}/status."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/ws/task/fake-task-id/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.endpoints.AsyncResult")
    async def test_task_status_pending(
        self, mock_result_cls: MagicMock, client: AsyncClient, auth_headers: dict
    ):
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        mock_result.state = "PENDING"
        mock_result_cls.return_value = mock_result

        response = await client.get("/api/v1/ws/task/test-task-123/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.endpoints.AsyncResult")
    async def test_task_status_completed(
        self, mock_result_cls: MagicMock, client: AsyncClient, auth_headers: dict
    ):
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.get.return_value = {"result": "done"}
        mock_result_cls.return_value = mock_result

        response = await client.get("/api/v1/ws/task/completed-task/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] == {"result": "done"}

    @pytest.mark.asyncio
    @patch("app.api.routes.websocket.endpoints.AsyncResult")
    async def test_task_status_failed(
        self, mock_result_cls: MagicMock, client: AsyncClient, auth_headers: dict
    ):
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.result = Exception("Task failed")
        mock_result_cls.return_value = mock_result

        response = await client.get("/api/v1/ws/task/failed-task/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "error" in data
