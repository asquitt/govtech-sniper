"""
RFP Sniper - Celery Application Configuration
==============================================
"""

import structlog
from celery import Celery
from celery.schedules import crontab
from celery.signals import before_task_publish, task_postrun, task_prerun
from kombu import Queue

from app.config import settings

# Create Celery app
celery_app = Celery(
    "rfp_sniper",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.ingest_tasks",
        "app.tasks.analysis_tasks",
        "app.tasks.generation_tasks",
        "app.tasks.document_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.sharepoint_sync_tasks",
        "app.tasks.email_ingest_tasks",
        "app.tasks.signal_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Result expiration (24 hours)
    result_expires=86400,
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    # Queues
    task_queues=(
        Queue("celery"),
        Queue("ingest"),
        Queue("analysis"),
        Queue("generation"),
        Queue("documents"),
        Queue("periodic"),
        Queue("maintenance"),
    ),
    # Beat schedule for periodic tasks
    beat_schedule={
        # Scan SAM.gov every 6 hours for new opportunities
        "scan-sam-gov-periodic": {
            "task": "app.tasks.ingest_tasks.periodic_sam_scan",
            "schedule": crontab(minute=0, hour="*/6"),
            "options": {"queue": "periodic"},
        },
        # Clean up expired context caches daily
        "cleanup-caches": {
            "task": "app.tasks.analysis_tasks.cleanup_expired_caches",
            "schedule": crontab(minute=0, hour=2),  # 2 AM UTC
            "options": {"queue": "maintenance"},
        },
        # Purge audit logs based on retention policy
        "purge-audit-events": {
            "task": "app.tasks.maintenance_tasks.purge_audit_events",
            "schedule": crontab(minute=0, hour=1),  # 1 AM UTC
            "options": {"queue": "maintenance"},
        },
        # Check operational alerts hourly
        "check-operational-alerts": {
            "task": "app.tasks.maintenance_tasks.check_operational_alerts",
            "schedule": crontab(minute=0, hour="*/1"),
            "options": {"queue": "maintenance"},
        },
        # Scan all non-SAM data sources every 6 hours (offset by 30 min from SAM)
        "scan-all-sources-periodic": {
            "task": "app.tasks.ingest_tasks.periodic_multi_source_scan",
            "schedule": crontab(minute=30, hour="*/6"),
            "options": {"queue": "periodic"},
        },
        # Daily opportunity digest at 7 AM UTC
        "daily-opportunity-digest": {
            "task": "app.tasks.ingest_tasks.send_daily_digest",
            "schedule": crontab(minute=0, hour=7),
            "options": {"queue": "periodic"},
        },
        # Poll RSS feeds for market signals every 4 hours
        "poll-signal-feeds": {
            "task": "app.tasks.signal_tasks.poll_signal_feeds",
            "schedule": crontab(minute=0, hour="*/4"),
            "options": {"queue": "periodic"},
        },
        # Send signal digest at 7:30 AM UTC daily
        "send-signal-digest": {
            "task": "app.tasks.signal_tasks.send_signal_digest",
            "schedule": crontab(minute=30, hour=7),
            "options": {"queue": "periodic"},
        },
        # Poll IMAP inboxes every 15 minutes for forwarded RFPs
        "poll-email-inboxes": {
            "task": "app.tasks.email_ingest_tasks.poll_email_inboxes",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "ingest"},
        },
        # Process pending ingested emails every 15 minutes (offset by 5 min)
        "process-ingested-emails": {
            "task": "app.tasks.email_ingest_tasks.process_ingested_emails",
            "schedule": crontab(minute="5,20,35,50"),
            "options": {"queue": "ingest"},
        },
        # Send deadline reminders at 8 AM UTC daily
        "send-deadline-reminders": {
            "task": "app.tasks.maintenance_tasks.send_deadline_reminders",
            "schedule": crontab(minute=0, hour=8),
            "options": {"queue": "periodic"},
        },
        # Watch SharePoint folders for new RFP documents every 15 minutes
        "watch-sharepoint-folders": {
            "task": "app.tasks.sharepoint_sync_tasks.watch_sharepoint_folders",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "periodic"},
        },
    },
    # Task routing
    task_routes={
        "app.tasks.ingest_tasks.*": {"queue": "ingest"},
        "app.tasks.analysis_tasks.*": {"queue": "analysis"},
        "app.tasks.generation_tasks.*": {"queue": "generation"},
        "app.tasks.document_tasks.*": {"queue": "documents"},
    },
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Correlation ID propagation into Celery tasks
# ---------------------------------------------------------------------------
# The HTTP middleware (CorrelationIDMiddleware) binds `correlation_id` to
# structlog contextvars. When a task is dispatched with `.delay()`, Celery
# automatically copies the current headers dict. We hook into the before_publish
# signal to inject the correlation_id, then bind it on the worker side via
# task_prerun.
# ---------------------------------------------------------------------------


@before_task_publish.connect
def inject_correlation_id(headers=None, **kwargs):
    """Inject correlation_id into task message headers at publish time."""
    if headers is not None:
        ctx = structlog.contextvars.get_contextvars()
        cid = ctx.get("correlation_id")
        if cid:
            headers["correlation_id"] = cid


@task_prerun.connect
def bind_correlation_id(task_id, task, args, kwargs, **kw):
    """Bind correlation_id from task headers into structlog context on the worker."""
    request = task.request
    cid = getattr(request, "correlation_id", None)
    if not cid and hasattr(request, "headers") and request.headers:
        cid = request.headers.get("correlation_id")
    if cid:
        structlog.contextvars.bind_contextvars(correlation_id=cid, task_id=task_id)
    else:
        structlog.contextvars.bind_contextvars(task_id=task_id)


@task_postrun.connect
def unbind_correlation_id(task_id, task, **kw):
    """Clean up structlog context after task completes."""
    structlog.contextvars.unbind_contextvars("correlation_id", "task_id")
