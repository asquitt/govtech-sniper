"""
Audit Service Unit Tests
=========================
Tests for audit event logging and purging.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit import AuditEvent
from app.services.audit_service import log_audit_event, purge_audit_events


class TestLogAuditEvent:
    @pytest.mark.asyncio
    async def test_creates_event(self, db_session: AsyncSession):
        event = await log_audit_event(
            db_session,
            user_id=1,
            entity_type="rfp",
            entity_id=42,
            action="created",
            metadata={"title": "Test RFP"},
        )
        await db_session.commit()
        assert event.user_id == 1
        assert event.entity_type == "rfp"
        assert event.entity_id == 42
        assert event.action == "created"
        assert event.event_metadata["title"] == "Test RFP"

    @pytest.mark.asyncio
    async def test_none_metadata_becomes_empty_dict(self, db_session: AsyncSession):
        event = await log_audit_event(
            db_session,
            user_id=1,
            entity_type="proposal",
            entity_id=1,
            action="exported",
        )
        assert event.event_metadata == {}

    @pytest.mark.asyncio
    async def test_event_persists(self, db_session: AsyncSession):
        await log_audit_event(
            db_session,
            user_id=5,
            entity_type="rfp",
            entity_id=10,
            action="deleted",
        )
        await db_session.commit()

        result = await db_session.execute(select(AuditEvent).where(AuditEvent.user_id == 5))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].action == "deleted"


class TestPurgeAuditEvents:
    @pytest.mark.asyncio
    async def test_purges_old_events(self, db_session: AsyncSession):
        # Create an old event
        old_event = AuditEvent(
            user_id=1,
            entity_type="rfp",
            entity_id=1,
            action="created",
            event_metadata={},
            created_at=datetime.utcnow() - timedelta(days=100),
        )
        db_session.add(old_event)

        # Create a recent event
        recent_event = AuditEvent(
            user_id=1,
            entity_type="rfp",
            entity_id=2,
            action="updated",
            event_metadata={},
            created_at=datetime.utcnow(),
        )
        db_session.add(recent_event)
        await db_session.commit()

        purged = await purge_audit_events(db_session, retention_days=90)
        await db_session.commit()

        assert purged >= 1

        # Recent event should remain
        result = await db_session.execute(select(AuditEvent).where(AuditEvent.entity_id == 2))
        remaining = result.scalars().all()
        assert len(remaining) == 1

    @pytest.mark.asyncio
    async def test_purge_with_no_old_events(self, db_session: AsyncSession):
        purged = await purge_audit_events(db_session, retention_days=90)
        assert purged == 0
