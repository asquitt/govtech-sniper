"""
RFP Sniper - Audit Tests
========================
Tests for audit log generation.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.user import User
from app.models.rfp import RFP


class TestAuditEvents:
    @pytest.mark.asyncio
    async def test_audit_events_for_rfp_lifecycle(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        # Create RFP
        response = await client.post(
            "/api/v1/rfps",
            params={"user_id": test_user.id},
            json={
                "title": "Audit RFP",
                "solicitation_number": "AUD-001",
                "notice_id": "audit-notice-001",
                "agency": "Audit Agency",
                "rfp_type": "solicitation",
            },
        )
        assert response.status_code == 200
        rfp_id = response.json()["id"]

        result = await db_session.execute(
            select(AuditEvent).where(AuditEvent.action == "rfp.created")
        )
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].entity_id == rfp_id

        # Update RFP
        response = await client.patch(
            f"/api/v1/rfps/{rfp_id}",
            json={"status": "analyzing"},
        )
        assert response.status_code == 200

        result = await db_session.execute(
            select(AuditEvent).where(AuditEvent.action == "rfp.updated")
        )
        events = result.scalars().all()
        assert len(events) == 1

        # Delete RFP
        response = await client.delete(f"/api/v1/rfps/{rfp_id}")
        assert response.status_code == 200

        result = await db_session.execute(
            select(AuditEvent).where(AuditEvent.action == "rfp.deleted")
        )
        events = result.scalars().all()
        assert len(events) == 1
