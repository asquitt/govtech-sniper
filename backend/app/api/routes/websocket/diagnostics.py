"""
WebSocket Routes - Diagnostics
===============================
Runtime telemetry, alerting, and export for WebSocket health monitoring.
"""

import csv
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.services.auth_service import UserAuth

from .manager import manager

router = APIRouter()


def _compute_disconnect_ratio(snapshot: dict) -> float:
    total_connections = snapshot["connections"]["total_connections"]
    total_disconnects = snapshot["connections"]["total_disconnects"]
    if total_connections <= 0:
        return 0.0
    return round(total_disconnects / total_connections, 4)


def _build_alert(
    *,
    code: str,
    severity: str,
    message: str,
    metric: str,
    actual: float,
    threshold: float,
    breached: bool,
) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "metric": metric,
        "actual": round(actual, 4),
        "threshold": round(threshold, 4),
        "breached": breached,
    }


def _build_diagnostics_alerts(
    snapshot: dict,
    *,
    max_avg_status_latency_ms: float,
    max_p95_status_latency_ms: float,
    max_reconnect_count: int,
    max_disconnect_ratio: float,
    min_outbound_events_per_minute: int,
    min_active_connection_count: int,
    include_all: bool,
) -> list[dict]:
    alerts: list[dict] = []

    avg_latency = float(snapshot["task_watch"]["avg_status_latency_ms"] or 0.0)
    p95_latency = float(snapshot["task_watch"]["p95_status_latency_ms"] or 0.0)
    reconnect_count = int(snapshot["connections"]["reconnect_count"])
    disconnect_ratio = _compute_disconnect_ratio(snapshot)
    outbound_per_minute = int(snapshot["event_throughput"]["outbound_events_per_minute"])
    active_connections = int(snapshot["connections"]["active_connection_count"])

    candidates = [
        _build_alert(
            code="task_watch_latency_high",
            severity="warning",
            message="Average task-watch status latency exceeded threshold.",
            metric="task_watch.avg_status_latency_ms",
            actual=avg_latency,
            threshold=max_avg_status_latency_ms,
            breached=avg_latency > max_avg_status_latency_ms,
        ),
        _build_alert(
            code="task_watch_p95_latency_high",
            severity="critical",
            message="P95 task-watch status latency exceeded threshold.",
            metric="task_watch.p95_status_latency_ms",
            actual=p95_latency,
            threshold=max_p95_status_latency_ms,
            breached=p95_latency > max_p95_status_latency_ms,
        ),
        _build_alert(
            code="reconnect_count_high",
            severity="warning",
            message="WebSocket reconnect count exceeded threshold.",
            metric="connections.reconnect_count",
            actual=float(reconnect_count),
            threshold=float(max_reconnect_count),
            breached=reconnect_count > max_reconnect_count,
        ),
        _build_alert(
            code="disconnect_ratio_high",
            severity="warning",
            message="Disconnect ratio exceeded threshold.",
            metric="connections.disconnect_ratio",
            actual=disconnect_ratio,
            threshold=max_disconnect_ratio,
            breached=disconnect_ratio > max_disconnect_ratio,
        ),
        _build_alert(
            code="outbound_throughput_low",
            severity="warning",
            message="Outbound event throughput dropped below threshold.",
            metric="event_throughput.outbound_events_per_minute",
            actual=float(outbound_per_minute),
            threshold=float(min_outbound_events_per_minute),
            breached=active_connections > 0
            and outbound_per_minute < min_outbound_events_per_minute,
        ),
        _build_alert(
            code="active_connections_low",
            severity="critical",
            message="Active WebSocket connection count dropped below threshold.",
            metric="connections.active_connection_count",
            actual=float(active_connections),
            threshold=float(min_active_connection_count),
            breached=active_connections < min_active_connection_count,
        ),
    ]

    for candidate in candidates:
        if include_all or candidate["breached"]:
            alerts.append(candidate)
    return alerts


@router.get("/ws/diagnostics")
async def get_websocket_diagnostics(
    _current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """
    Runtime diagnostics telemetry for websocket task feed health.
    """
    snapshot = manager.telemetry_snapshot()
    snapshot["timestamp"] = datetime.utcnow().isoformat()
    return snapshot


@router.get("/ws/diagnostics/alerts")
async def get_websocket_diagnostics_alerts(
    max_avg_status_latency_ms: float = Query(2000.0, ge=0.0),
    max_p95_status_latency_ms: float = Query(5000.0, ge=0.0),
    max_reconnect_count: int = Query(25, ge=0),
    max_disconnect_ratio: float = Query(0.4, ge=0.0, le=1.0),
    min_outbound_events_per_minute: int = Query(1, ge=0),
    min_active_connection_count: int = Query(0, ge=0),
    include_all: bool = Query(False),
    _current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """
    Evaluate websocket runtime telemetry against configurable alert thresholds.
    """
    snapshot = manager.telemetry_snapshot()
    alerts = _build_diagnostics_alerts(
        snapshot,
        max_avg_status_latency_ms=max_avg_status_latency_ms,
        max_p95_status_latency_ms=max_p95_status_latency_ms,
        max_reconnect_count=max_reconnect_count,
        max_disconnect_ratio=max_disconnect_ratio,
        min_outbound_events_per_minute=min_outbound_events_per_minute,
        min_active_connection_count=min_active_connection_count,
        include_all=include_all,
    )
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "thresholds": {
            "max_avg_status_latency_ms": max_avg_status_latency_ms,
            "max_p95_status_latency_ms": max_p95_status_latency_ms,
            "max_reconnect_count": max_reconnect_count,
            "max_disconnect_ratio": max_disconnect_ratio,
            "min_outbound_events_per_minute": min_outbound_events_per_minute,
            "min_active_connection_count": min_active_connection_count,
        },
        "alerts": alerts,
        "breached_count": sum(1 for item in alerts if item["breached"]),
        "telemetry": {
            **snapshot,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


@router.get("/ws/diagnostics/export", response_model=None)
async def export_websocket_diagnostics(
    format: str = Query("csv", pattern="^(csv|json)$"),
    include_alerts: bool = Query(True),
    max_avg_status_latency_ms: float = Query(2000.0, ge=0.0),
    max_p95_status_latency_ms: float = Query(5000.0, ge=0.0),
    max_reconnect_count: int = Query(25, ge=0),
    max_disconnect_ratio: float = Query(0.4, ge=0.0, le=1.0),
    min_outbound_events_per_minute: int = Query(1, ge=0),
    min_active_connection_count: int = Query(0, ge=0),
    _current_user: UserAuth = Depends(get_current_user),
) -> dict | StreamingResponse:
    """
    Export websocket telemetry snapshot with optional threshold-alert evaluation.
    """
    snapshot = manager.telemetry_snapshot()
    alerts = _build_diagnostics_alerts(
        snapshot,
        max_avg_status_latency_ms=max_avg_status_latency_ms,
        max_p95_status_latency_ms=max_p95_status_latency_ms,
        max_reconnect_count=max_reconnect_count,
        max_disconnect_ratio=max_disconnect_ratio,
        min_outbound_events_per_minute=min_outbound_events_per_minute,
        min_active_connection_count=min_active_connection_count,
        include_all=True,
    )
    timestamp = datetime.utcnow().isoformat()
    threshold_payload = {
        "max_avg_status_latency_ms": max_avg_status_latency_ms,
        "max_p95_status_latency_ms": max_p95_status_latency_ms,
        "max_reconnect_count": max_reconnect_count,
        "max_disconnect_ratio": max_disconnect_ratio,
        "min_outbound_events_per_minute": min_outbound_events_per_minute,
        "min_active_connection_count": min_active_connection_count,
    }

    if format == "json":
        return {
            "timestamp": timestamp,
            "thresholds": threshold_payload,
            "telemetry": snapshot,
            "alerts": alerts if include_alerts else [],
        }

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "row_type",
            "metric",
            "value",
            "alert_code",
            "severity",
            "actual",
            "threshold",
            "message",
            "breached",
        ],
    )
    writer.writeheader()

    metric_rows = {
        "connections.active_user_channels": snapshot["connections"]["active_user_channels"],
        "connections.active_connection_count": snapshot["connections"]["active_connection_count"],
        "connections.total_connections": snapshot["connections"]["total_connections"],
        "connections.total_disconnects": snapshot["connections"]["total_disconnects"],
        "connections.reconnect_count": snapshot["connections"]["reconnect_count"],
        "connections.disconnect_ratio": _compute_disconnect_ratio(snapshot),
        "task_watch.watched_tasks": snapshot["task_watch"]["watched_tasks"],
        "task_watch.avg_status_latency_ms": snapshot["task_watch"]["avg_status_latency_ms"],
        "task_watch.p95_status_latency_ms": snapshot["task_watch"]["p95_status_latency_ms"],
        "event_throughput.inbound_events_total": snapshot["event_throughput"][
            "inbound_events_total"
        ],
        "event_throughput.outbound_events_total": snapshot["event_throughput"][
            "outbound_events_total"
        ],
        "event_throughput.inbound_events_per_minute": snapshot["event_throughput"][
            "inbound_events_per_minute"
        ],
        "event_throughput.outbound_events_per_minute": snapshot["event_throughput"][
            "outbound_events_per_minute"
        ],
    }
    for key, value in metric_rows.items():
        writer.writerow(
            {
                "row_type": "metric",
                "metric": key,
                "value": value,
                "alert_code": "",
                "severity": "",
                "actual": "",
                "threshold": "",
                "message": "",
                "breached": "",
            }
        )

    if include_alerts:
        for alert in alerts:
            writer.writerow(
                {
                    "row_type": "alert",
                    "metric": alert["metric"],
                    "value": "",
                    "alert_code": alert["code"],
                    "severity": alert["severity"],
                    "actual": alert["actual"],
                    "threshold": alert["threshold"],
                    "message": alert["message"],
                    "breached": alert["breached"],
                }
            )

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="websocket_diagnostics_{datetime.utcnow().strftime("%Y%m%d")}.csv"'
    )
    return response
