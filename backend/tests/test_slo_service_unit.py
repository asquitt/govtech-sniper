"""
SLO Service Unit Tests
========================
Tests for SLOMetricCollector — in-memory, no I/O.
"""

from app.services.slo_service import SLO_TARGETS, CriticalFlow, SLOMetricCollector, SLOTarget

# =============================================================================
# SLO Targets
# =============================================================================


class TestSLOTargets:
    def test_all_flows_have_targets(self):
        for flow in CriticalFlow:
            assert flow in SLO_TARGETS
            target = SLO_TARGETS[flow]
            assert isinstance(target, SLOTarget)

    def test_target_values_reasonable(self):
        for target in SLO_TARGETS.values():
            assert 0.9 <= target.success_rate_target <= 1.0
            assert target.p95_latency_ms > 0
            assert len(target.description) > 0


# =============================================================================
# SLOMetricCollector
# =============================================================================


class TestSLOMetricCollectorRecord:
    def test_record_success(self):
        collector = SLOMetricCollector()
        collector.record(CriticalFlow.INGEST, 500.0, True)
        summary = collector.get_summary(CriticalFlow.INGEST)
        assert summary["total"] == 1
        assert summary["successes"] == 1

    def test_record_failure(self):
        collector = SLOMetricCollector()
        collector.record(CriticalFlow.DRAFT, 120000.0, False, error="Timeout")
        summary = collector.get_summary(CriticalFlow.DRAFT)
        assert summary["total"] == 1
        assert summary["successes"] == 0

    def test_cap_at_1000(self):
        collector = SLOMetricCollector()
        for i in range(1050):
            collector.record(CriticalFlow.EXPORT, float(i), True)
        summary = collector.get_summary(CriticalFlow.EXPORT)
        assert summary["total"] == 1000


class TestSLOMetricCollectorSummary:
    def test_empty_summary(self):
        collector = SLOMetricCollector()
        summary = collector.get_summary(CriticalFlow.ANALYZE)
        assert summary["total"] == 0
        assert summary["success_rate"] is None
        assert summary["p95_ms"] is None

    def test_full_summary(self):
        collector = SLOMetricCollector()
        for i in range(100):
            collector.record(CriticalFlow.INGEST, float(i * 100), i < 99)
        summary = collector.get_summary(CriticalFlow.INGEST)
        assert summary["total"] == 100
        assert summary["success_rate"] == 0.99
        assert summary["p95_ms"] is not None

    def test_get_all_summaries(self):
        collector = SLOMetricCollector()
        collector.record(CriticalFlow.INGEST, 100.0, True)
        summaries = collector.get_all_summaries()
        assert len(summaries) == len(CriticalFlow)
        ingest = next(s for s in summaries if s["flow"] == "ingest")
        assert ingest["total"] == 1


class TestSLOErrorBudget:
    def test_healthy_budget(self):
        collector = SLOMetricCollector()
        for _ in range(100):
            collector.record(CriticalFlow.INGEST, 100.0, True)
        budget = collector.get_error_budget(CriticalFlow.INGEST)
        assert budget["is_healthy"] is True
        assert budget["actual"] == 1.0

    def test_unhealthy_budget(self):
        collector = SLOMetricCollector()
        for i in range(100):
            collector.record(CriticalFlow.INGEST, 100.0, i < 90)
        budget = collector.get_error_budget(CriticalFlow.INGEST)
        # Target is 0.995, actual is 0.9 — unhealthy
        assert budget["is_healthy"] is False

    def test_empty_is_healthy(self):
        collector = SLOMetricCollector()
        budget = collector.get_error_budget(CriticalFlow.DRAFT)
        assert budget["is_healthy"] is True
        assert budget["total_requests"] == 0


class TestSLOReleaseGate:
    def test_can_release_when_healthy(self):
        collector = SLOMetricCollector()
        for flow in CriticalFlow:
            for _ in range(50):
                collector.record(flow, 100.0, True)
        gate = collector.get_release_gate()
        assert gate["can_release"] is True
        assert gate["breaches"] == []

    def test_blocked_when_unhealthy(self):
        collector = SLOMetricCollector()
        for _ in range(50):
            collector.record(CriticalFlow.INGEST, 100.0, True)
        # Make one flow fail heavily
        for i in range(100):
            collector.record(CriticalFlow.DRAFT, 100.0, i < 50)
        gate = collector.get_release_gate()
        assert gate["can_release"] is False
        assert len(gate["breaches"]) >= 1

    def test_empty_collector_can_release(self):
        collector = SLOMetricCollector()
        gate = collector.get_release_gate()
        assert gate["can_release"] is True
