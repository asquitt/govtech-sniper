"""
RFP Sniper - Application Metrics
================================
Custom metrics and performance tracking.
"""

import time
from functools import wraps
from typing import Dict, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    Simple in-memory metrics collector.
    For production, replace with Prometheus, DataDog, or similar.
    """

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._start_time = datetime.utcnow()

    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        key = self._make_key(name, tags)
        self._counters[key] += value

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        key = self._make_key(name, tags)
        self._gauges[key] = value

    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram value."""
        key = self._make_key(name, tags)
        self._histograms[key].append(value)
        # Keep only last 1000 values to prevent memory issues
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Create a unique key for the metric."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"

    def get_all(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        result = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {},
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds(),
        }

        # Calculate histogram summaries
        for key, values in self._histograms.items():
            if values:
                sorted_vals = sorted(values)
                result["histograms"][key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": sorted_vals[len(sorted_vals) // 2],
                    "p95": sorted_vals[int(len(sorted_vals) * 0.95)],
                    "p99": sorted_vals[int(len(sorted_vals) * 0.99)],
                }

        return result

    def reset(self):
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


# Global metrics instance
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics


def increment_counter(name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
    """Increment a counter metric."""
    _metrics.increment(name, value, tags)


def set_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Set a gauge metric."""
    _metrics.gauge(name, value, tags)


def record_histogram(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Record a histogram value."""
    _metrics.histogram(name, value, tags)


def track_time(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to track function execution time.

    Usage:
        @track_time("api.analyze_rfp")
        async def analyze_rfp(rfp_id: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                increment_counter(f"{metric_name}.success", tags=tags)
                return result
            except Exception as e:
                increment_counter(f"{metric_name}.error", tags=tags)
                raise
            finally:
                duration = (time.perf_counter() - start) * 1000  # ms
                record_histogram(f"{metric_name}.duration_ms", duration, tags)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                increment_counter(f"{metric_name}.success", tags=tags)
                return result
            except Exception as e:
                increment_counter(f"{metric_name}.error", tags=tags)
                raise
            finally:
                duration = (time.perf_counter() - start) * 1000  # ms
                record_histogram(f"{metric_name}.duration_ms", duration, tags)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class MetricsMiddleware:
    """
    Middleware to collect HTTP request metrics.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start_time = time.perf_counter()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        # Normalize path for metrics (remove IDs)
        import re
        normalized_path = re.sub(r'/\d+', '/{id}', path)

        response_status = 500

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = (time.perf_counter() - start_time) * 1000  # ms

            tags = {
                "method": method,
                "path": normalized_path,
                "status": str(response_status),
            }

            increment_counter("http.requests", tags=tags)
            record_histogram("http.request_duration_ms", duration, tags=tags)

            # Track specific status code ranges
            if response_status >= 500:
                increment_counter("http.5xx_errors", tags={"path": normalized_path})
            elif response_status >= 400:
                increment_counter("http.4xx_errors", tags={"path": normalized_path})


# Application-specific metrics helpers
def track_rfp_ingested(source: str = "sam_gov"):
    """Track when an RFP is ingested."""
    increment_counter("rfp.ingested", tags={"source": source})


def track_rfp_analyzed(success: bool = True):
    """Track RFP analysis completion."""
    status = "success" if success else "failure"
    increment_counter("rfp.analyzed", tags={"status": status})


def track_proposal_generated(section_count: int):
    """Track proposal generation."""
    increment_counter("proposal.generated")
    record_histogram("proposal.section_count", section_count)


def track_ai_request(model: str, tokens: int, duration_ms: float):
    """Track AI API requests."""
    increment_counter("ai.requests", tags={"model": model})
    record_histogram("ai.tokens_used", tokens, tags={"model": model})
    record_histogram("ai.duration_ms", duration_ms, tags={"model": model})


def track_export(format: str):
    """Track document exports."""
    increment_counter("export.completed", tags={"format": format})


def track_user_action(action: str, user_tier: str):
    """Track user actions for analytics."""
    increment_counter("user.actions", tags={"action": action, "tier": user_tier})
