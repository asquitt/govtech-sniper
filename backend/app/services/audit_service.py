"""
RFP Sniper - Audit Service
==========================
Helpers for writing audit events.
"""

from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.models.audit import AuditEvent


async def log_audit_event(
    session: AsyncSession,
    *,
    user_id: Optional[int],
    entity_type: str,
    entity_id: Optional[int],
    action: str,
    metadata: Optional[dict] = None,
) -> AuditEvent:
    """
    Record an audit event.
    """
    event = AuditEvent(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        event_metadata=metadata or {},
    )
    session.add(event)
    return event


async def purge_audit_events(session: AsyncSession, retention_days: int) -> int:
    """
    Purge audit events older than retention_days.

    Returns number of rows deleted.
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    result = await session.execute(
        delete(AuditEvent).where(AuditEvent.created_at < cutoff)
    )
    return result.rowcount or 0
