"""
Unit tests for maintenance_tasks Celery tasks.
Tests purge_audit_events_task, send_deadline_reminders_task, check_operational_alerts.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch


def _mock_session_ctx(mock_session):
    @asynccontextmanager
    async def _ctx():
        yield mock_session

    return _ctx


class TestPurgeAuditEventsTask:
    def test_purge_returns_count(self):
        mock_session = AsyncMock()

        with (
            patch(
                "app.tasks.maintenance_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch(
                "app.tasks.maintenance_tasks.purge_audit_events",
                new_callable=AsyncMock,
                return_value=15,
            ),
            patch("app.tasks.maintenance_tasks.settings") as mock_settings,
        ):
            mock_settings.audit_retention_days = 90

            from app.tasks.maintenance_tasks import purge_audit_events_task

            result = purge_audit_events_task()
            assert result["status"] == "ok"
            assert result["purged"] == 15

    def test_purge_zero_events(self):
        mock_session = AsyncMock()

        with (
            patch(
                "app.tasks.maintenance_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch(
                "app.tasks.maintenance_tasks.purge_audit_events",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch("app.tasks.maintenance_tasks.settings") as mock_settings,
        ):
            mock_settings.audit_retention_days = 30

            from app.tasks.maintenance_tasks import purge_audit_events_task

            result = purge_audit_events_task()
            assert result["purged"] == 0


class TestCheckOperationalAlerts:
    def test_returns_alert_counts(self):
        mock_session = AsyncMock()

        with (
            patch(
                "app.tasks.maintenance_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch(
                "app.tasks.maintenance_tasks.get_alert_counts",
                new_callable=AsyncMock,
                return_value={"critical": 2, "warning": 5, "info": 10},
            ),
        ):
            from app.tasks.maintenance_tasks import check_operational_alerts

            result = check_operational_alerts()
            assert result["status"] == "ok"
            assert result["critical"] == 2
            assert result["warning"] == 5


class TestSendDeadlineReminders:
    def test_sends_reminders(self):
        mock_session = AsyncMock()
        mock_send = AsyncMock()

        with (
            patch(
                "app.tasks.maintenance_tasks.get_celery_session_context",
                _mock_session_ctx(mock_session),
            ),
            patch("app.api.routes.notifications.send_deadline_reminders", mock_send),
        ):
            from app.tasks.maintenance_tasks import send_deadline_reminders_task

            result = send_deadline_reminders_task()
            assert result["status"] == "ok"
            assert result["sent"] is True
