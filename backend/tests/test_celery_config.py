"""
Celery Configuration Tests
===========================
Verify task registration, queue config, and beat schedule.
"""

from app.tasks.celery_app import celery_app


class TestCeleryAppConfig:
    def test_broker_and_backend_configured(self):
        assert celery_app.conf.broker_url is not None
        assert celery_app.conf.result_backend is not None

    def test_json_serialization(self):
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_utc_timezone(self):
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_reliability_settings(self):
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_time_limits(self):
        assert celery_app.conf.task_soft_time_limit == 300
        assert celery_app.conf.task_time_limit == 600

    def test_result_expiry(self):
        assert celery_app.conf.result_expires == 86400


class TestQueueConfiguration:
    def test_required_queues_exist(self):
        queue_names = {q.name for q in celery_app.conf.task_queues}
        expected = {
            "celery",
            "ingest",
            "analysis",
            "generation",
            "documents",
            "periodic",
            "maintenance",
        }
        assert expected.issubset(queue_names)

    def test_task_routing(self):
        routes = celery_app.conf.task_routes
        assert routes["app.tasks.ingest_tasks.*"]["queue"] == "ingest"
        assert routes["app.tasks.analysis_tasks.*"]["queue"] == "analysis"
        assert routes["app.tasks.generation_tasks.*"]["queue"] == "generation"
        assert routes["app.tasks.document_tasks.*"]["queue"] == "documents"


class TestBeatSchedule:
    def test_periodic_sam_scan_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "scan-sam-gov-periodic" in schedule
        entry = schedule["scan-sam-gov-periodic"]
        assert entry["task"] == "app.tasks.ingest_tasks.periodic_sam_scan"
        assert entry["options"]["queue"] == "periodic"

    def test_cache_cleanup_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-caches" in schedule
        entry = schedule["cleanup-caches"]
        assert entry["task"] == "app.tasks.analysis_tasks.cleanup_expired_caches"
        assert entry["options"]["queue"] == "maintenance"

    def test_audit_purge_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "purge-audit-events" in schedule
        entry = schedule["purge-audit-events"]
        assert entry["options"]["queue"] == "maintenance"

    def test_deadline_reminders_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "send-deadline-reminders" in schedule

    def test_signal_feeds_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "poll-signal-feeds" in schedule
        assert "send-signal-digest" in schedule

    def test_email_ingest_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "poll-email-inboxes" in schedule
        assert "process-ingested-emails" in schedule

    def test_sharepoint_watch_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "watch-sharepoint-folders" in schedule

    def test_all_beat_entries_have_task_and_schedule(self):
        for name, entry in celery_app.conf.beat_schedule.items():
            assert "task" in entry, f"{name} missing 'task'"
            assert "schedule" in entry, f"{name} missing 'schedule'"


class TestTaskRegistration:
    def test_core_tasks_included(self):
        """All task modules should be in the include list."""
        includes = celery_app.conf.include
        assert "app.tasks.ingest_tasks" in includes
        assert "app.tasks.analysis_tasks" in includes
        assert "app.tasks.generation_tasks" in includes
        assert "app.tasks.document_tasks" in includes
        assert "app.tasks.maintenance_tasks" in includes
        assert "app.tasks.sharepoint_sync_tasks" in includes
        assert "app.tasks.email_ingest_tasks" in includes
        assert "app.tasks.signal_tasks" in includes
