"""
RFP Sniper - Audit Service
==========================
Helpers for writing audit events.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

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
