"""
RFP Sniper - Maintenance Tasks
==============================
Scheduled maintenance for audit retention and operational alerts.
"""

import asyncio
from datetime import datetime
import structlog

from app.tasks.celery_app import celery_app
from app.database import get_celery_session_context
from app.config import settings
from app.services.audit_service import purge_audit_events
from app.services.alert_service import get_alert_counts

logger = structlog.get_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.maintenance_tasks.purge_audit_events")
def purge_audit_events_task() -> dict:
    async def _purge() -> dict:
        async with get_celery_session_context() as session:
            purged = await purge_audit_events(session, settings.audit_retention_days)
            return {"purged": purged}

    result = run_async(_purge())
    logger.info("Audit retention purge complete", **result)
    return {"status": "ok", **result}


@celery_app.task(name="app.tasks.maintenance_tasks.check_operational_alerts")
def check_operational_alerts() -> dict:
    async def _check() -> dict:
        async with get_celery_session_context() as session:
            counts = await get_alert_counts(session, user_id=None, days=7)
            return counts

    counts = run_async(_check())
    logger.info("Operational alert check", timestamp=datetime.utcnow().isoformat(), **counts)
    return {"status": "ok", **counts}
