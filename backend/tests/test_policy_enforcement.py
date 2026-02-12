"""Tests for policy engine enforcement on export routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.proposal import Proposal
from app.models.rfp import RFP
from app.models.user import User


async def _setup_proposal(db_session: AsyncSession, user_id: int, classification: str) -> int:
    """Create an RFP + proposal with the given classification for testing."""
    rfp = RFP(
        title="Test RFP",
        solicitation_number=f"TEST-POL-{classification}",
        user_id=user_id,
        status="analyzed",
    )
    db_session.add(rfp)
    await db_session.flush()

    proposal = Proposal(
        title="Test Proposal",
        rfp_id=rfp.id,
        user_id=user_id,
        classification=classification,
    )
    db_session.add(proposal)
    await db_session.flush()
    await db_session.commit()
    return proposal.id


async def _set_org_role(db_session: AsyncSession, user_id: int, role: OrgRole):
    """Assign user to an org with the given role."""
    result = await db_session.execute(select(Organization).limit(1))
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(name="Test Org", slug="test-org", owner_id=user_id)
        db_session.add(org)
        await db_session.flush()

    existing = await db_session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    for m in existing.scalars().all():
        await db_session.delete(m)

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user_id,
        role=role,
    )
    db_session.add(member)
    await db_session.commit()


class TestPolicyEnforcement:
    """Integration tests for policy engine on export endpoints."""

    @pytest.mark.asyncio
    async def test_export_public_allowed_for_viewer(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.VIEWER)
        proposal_id = await _setup_proposal(db_session, user.id, "public")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_internal_allowed_for_viewer(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.VIEWER)
        proposal_id = await _setup_proposal(db_session, user.id, "internal")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_fci_denied_for_viewer(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.VIEWER)
        proposal_id = await _setup_proposal(db_session, user.id, "fci")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_fci_allowed_for_member(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.MEMBER)
        proposal_id = await _setup_proposal(db_session, user.id, "fci")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_cui_step_up_for_admin(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.ADMIN)
        proposal_id = await _setup_proposal(db_session, user.id, "cui")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "step-up" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_export_cui_denied_for_viewer(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.VIEWER)
        proposal_id = await _setup_proposal(db_session, user.id, "cui")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_creates_audit_event(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.MEMBER)
        proposal_id = await _setup_proposal(db_session, user.id, "internal")

        await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )

        events = (
            (
                await db_session.execute(
                    select(AuditEvent).where(
                        AuditEvent.entity_type == "proposal",
                        AuditEvent.entity_id == proposal_id,
                        AuditEvent.action == "export_docx",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(events) >= 1
        assert events[0].event_metadata["decision"] == "allow"

    @pytest.mark.asyncio
    async def test_pdf_export_policy_enforced(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.VIEWER)
        proposal_id = await _setup_proposal(db_session, user.id, "fci")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/pdf",
            headers=auth_headers,
        )
        assert response.status_code == 403
