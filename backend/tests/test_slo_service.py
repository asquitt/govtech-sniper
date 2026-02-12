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
