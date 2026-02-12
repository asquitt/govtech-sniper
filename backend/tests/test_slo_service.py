"""Tests for SLO service."""

from app.services.slo_service import SLO_TARGETS, CriticalFlow, SLOMetricCollector


class TestSLOTargets:
    def test_all_flows_have_targets(self):
        for flow in CriticalFlow:
            assert flow in SLO_TARGETS

    def test_success_rate_targets_reasonable(self):
        for target in SLO_TARGETS.values():
            assert 0.9 <= target.success_rate_target <= 1.0

    def test_latency_targets_positive(self):
        for target in SLO_TARGETS.values():
            assert target.p95_latency_ms > 0


class TestSLOMetricCollector:
    def test_record_and_summarize(self):
        collector = SLOMetricCollector()
        collector.record(CriticalFlow.INGEST, 1500.0, True)
        collector.record(CriticalFlow.INGEST, 2000.0, True)
        collector.record(CriticalFlow.INGEST, 35000.0, False, error="timeout")
        summary = collector.get_summary(CriticalFlow.INGEST)
        assert summary["total"] == 3
        assert summary["successes"] == 2
        assert summary["success_rate"] == 0.6667

    def test_empty_summary(self):
        collector = SLOMetricCollector()
        summary = collector.get_summary(CriticalFlow.DRAFT)
        assert summary["total"] == 0
        assert summary["success_rate"] is None

    def test_get_all_summaries(self):
        collector = SLOMetricCollector()
        summaries = collector.get_all_summaries()
        assert len(summaries) == 4

    def test_metric_cap_at_1000(self):
        collector = SLOMetricCollector()
        for i in range(1100):
            collector.record(CriticalFlow.EXPORT, float(i), True)
        assert len(collector._metrics[CriticalFlow.EXPORT]) == 1000


class TestErrorBudget:
    def test_error_budget_healthy_when_all_succeed(self):
        collector = SLOMetricCollector()
        for _ in range(100):
            collector.record(CriticalFlow.INGEST, 500.0, True)
        budget = collector.get_error_budget(CriticalFlow.INGEST)
        assert budget["is_healthy"] is True
        assert budget["actual"] == 1.0
        assert budget["actual_failures"] == 0
        assert budget["total_requests"] == 100

    def test_error_budget_unhealthy_when_failures_exceed_budget(self):
        collector = SLOMetricCollector()
        # INGEST target is 0.995 — with 100 requests, allowed failures = 0
        # So even 1 failure should breach on a small sample,
        # but let's use 1000 requests for clearer math.
        for _ in range(990):
            collector.record(CriticalFlow.INGEST, 500.0, True)
        for _ in range(10):
            collector.record(CriticalFlow.INGEST, 500.0, False, error="timeout")
        budget = collector.get_error_budget(CriticalFlow.INGEST)
        # actual = 990/1000 = 0.99, target = 0.995 → unhealthy
        assert budget["is_healthy"] is False
        assert budget["actual_failures"] == 10
        assert budget["target"] == 0.995


class TestReleaseGate:
    def test_release_gate_passes_when_all_healthy(self):
        collector = SLOMetricCollector()
        for flow in CriticalFlow:
            for _ in range(100):
                collector.record(flow, 500.0, True)
        gate = collector.get_release_gate()
        assert gate["can_release"] is True
        assert gate["breaches"] == []
        assert len(gate["flows"]) == 4
        assert "evaluated_at" in gate

    def test_release_gate_fails_with_breaches(self):
        collector = SLOMetricCollector()
        # Make all flows healthy except DRAFT
        for flow in CriticalFlow:
            for _ in range(100):
                collector.record(flow, 500.0, True)
        # Breach DRAFT by adding many failures (target 0.99)
        for _ in range(200):
            collector.record(CriticalFlow.DRAFT, 500.0, False, error="fail")
        gate = collector.get_release_gate()
        assert gate["can_release"] is False
        assert len(gate["breaches"]) >= 1
        breach_flows = [b["flow"] for b in gate["breaches"]]
        assert "draft" in breach_flows
