"""
SLO definitions and metric tracking for critical platform flows.

Tracks latency and success rates for: ingest, analyze, draft, export.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class CriticalFlow(str, Enum):
    INGEST = "ingest"
    ANALYZE = "analyze"
    DRAFT = "draft"
    EXPORT = "export"


@dataclass
class SLOTarget:
    flow: CriticalFlow
    success_rate_target: float  # e.g. 0.99
    p95_latency_ms: int  # max acceptable p95 latency in ms
    description: str


# SLO definitions for the 4 critical flows
SLO_TARGETS: dict[CriticalFlow, SLOTarget] = {
    CriticalFlow.INGEST: SLOTarget(
        flow=CriticalFlow.INGEST,
        success_rate_target=0.995,
        p95_latency_ms=30000,
        description="Document upload + text extraction + initial parse",
    ),
    CriticalFlow.ANALYZE: SLOTarget(
        flow=CriticalFlow.ANALYZE,
        success_rate_target=0.99,
        p95_latency_ms=60000,
        description="Compliance matrix extraction + requirement parsing",
    ),
    CriticalFlow.DRAFT: SLOTarget(
        flow=CriticalFlow.DRAFT,
        success_rate_target=0.99,
        p95_latency_ms=120000,
        description="AI section generation with citations",
    ),
    CriticalFlow.EXPORT: SLOTarget(
        flow=CriticalFlow.EXPORT,
        success_rate_target=0.995,
        p95_latency_ms=15000,
        description="DOCX/PDF export with formatting",
    ),
}


class SLOMetricCollector:
    """Collects latency and success/failure counts for SLO tracking."""

    def __init__(self):
        self._metrics: dict[CriticalFlow, list[dict]] = {f: [] for f in CriticalFlow}

    def record(
        self,
        flow: CriticalFlow,
        duration_ms: float,
        success: bool,
        error: str | None = None,
    ):
        entry = {
            "timestamp": time.time(),
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
        }
        self._metrics[flow].append(entry)
        # Keep last 1000 entries per flow
        if len(self._metrics[flow]) > 1000:
            self._metrics[flow] = self._metrics[flow][-1000:]
        logger.info(
            "slo_metric_recorded",
            flow=flow.value,
            duration_ms=round(duration_ms, 1),
            success=success,
        )

    def get_summary(self, flow: CriticalFlow) -> dict:
        entries = self._metrics[flow]
        if not entries:
            return {
                "flow": flow.value,
                "total": 0,
                "success_rate": None,
                "p95_ms": None,
            }
        total = len(entries)
        successes = sum(1 for e in entries if e["success"])
        durations = sorted(e["duration_ms"] for e in entries)
        p95_idx = int(total * 0.95)
        return {
            "flow": flow.value,
            "total": total,
            "successes": successes,
            "success_rate": round(successes / total, 4) if total else None,
            "p95_ms": round(durations[min(p95_idx, total - 1)], 1),
            "target_success_rate": SLO_TARGETS[flow].success_rate_target,
            "target_p95_ms": SLO_TARGETS[flow].p95_latency_ms,
        }

    def get_all_summaries(self) -> list[dict]:
        return [self.get_summary(f) for f in CriticalFlow]

    def get_error_budget(self, flow: CriticalFlow) -> dict:
        target = SLO_TARGETS[flow]
        entries = self._metrics[flow]
        total = len(entries)
        successes = sum(1 for e in entries if e["success"])
        actual = successes / total if total else 1.0
        budget = target.success_rate_target - actual
        error_allowance = 1 - target.success_rate_target
        budget_remaining_pct = (budget / error_allowance) * 100 if error_allowance > 0 else 100.0
        return {
            "flow": flow.value,
            "target": target.success_rate_target,
            "actual": round(actual, 4),
            "budget": round(budget, 4),
            "budget_remaining_pct": round(budget_remaining_pct, 2),
            "is_healthy": actual >= target.success_rate_target,
            "total_requests": total,
            "allowed_failures": int(error_allowance * total),
            "actual_failures": total - successes,
        }

    def get_release_gate(self) -> dict:
        budgets = [self.get_error_budget(f) for f in CriticalFlow]
        breaches = [b for b in budgets if not b["is_healthy"]]
        return {
            "can_release": all(b["is_healthy"] for b in budgets),
            "evaluated_at": datetime.utcnow().isoformat(),
            "flows": budgets,
            "breaches": breaches,
        }


# Global singleton
slo_collector = SLOMetricCollector()
