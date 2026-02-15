"""Integration tests for compliance registry control/evidence endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.compliance_registry import (
    ComplianceControl,
    ComplianceEvidence,
    ControlFramework,
    ControlStatus,
    EvidenceType,
)
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User
from app.services.auth_service import hash_password


async def _set_org_membership(
    db_session: AsyncSession,
    *,
    user_id: int,
    role: OrgRole,
    slug_suffix: str,
) -> Organization:
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()

    org = Organization(name=f"Registry Org {slug_suffix}", slug=f"registry-org-{slug_suffix}")
    db_session.add(org)
    await db_session.flush()

    db_session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            role=role,
            is_active=True,
        )
    )
    user.organization_id = org.id
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(org)
    return org


class TestComplianceRegistry:
    @pytest.mark.asyncio
    async def test_control_evidence_link_crud_for_current_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        control_response = await client.post(
            "/api/v1/compliance-registry/controls",
            headers=auth_headers,
            json={
                "framework": "fedramp",
                "control_id": "AC-2",
                "title": "Account management",
                "description": "Account provisioning and de-provisioning",
                "status": "in_progress",
            },
        )
        assert control_response.status_code == 201
        control = control_response.json()
        assert control["control_id"] == "AC-2"

        evidence_response = await client.post(
            "/api/v1/compliance-registry/evidence",
            headers=auth_headers,
            json={
                "title": "IAM workflow screenshot",
                "evidence_type": "screenshot",
                "description": "Workflow screen for account provisioning approvals",
            },
        )
        assert evidence_response.status_code == 201
        evidence = evidence_response.json()
        assert evidence["title"] == "IAM workflow screenshot"

        controls_list_response = await client.get(
            "/api/v1/compliance-registry/controls",
            headers=auth_headers,
        )
        assert controls_list_response.status_code == 200
        assert any(item["id"] == control["id"] for item in controls_list_response.json())

        evidence_list_response = await client.get(
            "/api/v1/compliance-registry/evidence",
            headers=auth_headers,
        )
        assert evidence_list_response.status_code == 200
        assert any(item["id"] == evidence["id"] for item in evidence_list_response.json())

        link_response = await client.post(
            "/api/v1/compliance-registry/links",
            headers=auth_headers,
            json={
                "control_id": control["id"],
                "evidence_id": evidence["id"],
                "notes": "Mapped during readiness review",
            },
        )
        assert link_response.status_code == 201
        link_payload = link_response.json()
        assert link_payload["status"] == "linked"
        assert link_payload["id"] is not None

        control_evidence_response = await client.get(
            f"/api/v1/compliance-registry/controls/{control['id']}/evidence",
            headers=auth_headers,
        )
        assert control_evidence_response.status_code == 200
        control_evidence_items = control_evidence_response.json()
        assert len(control_evidence_items) == 1
        assert control_evidence_items[0]["id"] == evidence["id"]

        update_control_response = await client.patch(
            f"/api/v1/compliance-registry/controls/{control['id']}",
            headers=auth_headers,
            json={"status": "assessed", "assessor_notes": "Accepted by reviewer"},
        )
        assert update_control_response.status_code == 200
        updated_control = update_control_response.json()
        assert updated_control["status"] == "assessed"
        assert updated_control["assessor_notes"] == "Accepted by reviewer"

    @pytest.mark.asyncio
    async def test_organization_scope_filters_records_by_org(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        own_org = await _set_org_membership(
            db_session,
            user_id=test_user.id,
            role=OrgRole.OWNER,
            slug_suffix=f"owner-{test_user.id}",
        )

        own_control_response = await client.post(
            "/api/v1/compliance-registry/controls",
            headers=auth_headers,
            json={
                "framework": "soc2",
                "control_id": "CC1.1",
                "title": "Integrity oversight",
                "status": "implemented",
            },
        )
        assert own_control_response.status_code == 201

        own_evidence_response = await client.post(
            "/api/v1/compliance-registry/evidence",
            headers=auth_headers,
            json={
                "title": "SOC2 evidence package",
                "evidence_type": "policy",
            },
        )
        assert own_evidence_response.status_code == 201

        other_user = User(
            email=f"other-org-{test_user.id}@example.com",
            hashed_password=hash_password("TestPassword123!"),
            full_name="Other Org User",
            company_name="Other Org Inc",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        other_org = await _set_org_membership(
            db_session,
            user_id=other_user.id,
            role=OrgRole.OWNER,
            slug_suffix=f"other-{other_user.id}",
        )

        db_session.add(
            ComplianceControl(
                user_id=other_user.id,
                organization_id=other_org.id,
                framework=ControlFramework.FEDRAMP,
                control_id="OTHER-CTRL-1",
                title="Other org control",
                status=ControlStatus.IN_PROGRESS,
            )
        )
        db_session.add(
            ComplianceEvidence(
                user_id=other_user.id,
                organization_id=other_org.id,
                title="Other org evidence",
                evidence_type=EvidenceType.LOG,
            )
        )
        await db_session.commit()

        own_controls_scope_response = await client.get(
            "/api/v1/compliance-registry/controls?scope=organization",
            headers=auth_headers,
        )
        assert own_controls_scope_response.status_code == 200
        scoped_control_ids = {item["control_id"] for item in own_controls_scope_response.json()}
        assert "CC1.1" in scoped_control_ids
        assert "OTHER-CTRL-1" not in scoped_control_ids

        own_evidence_scope_response = await client.get(
            "/api/v1/compliance-registry/evidence?scope=organization",
            headers=auth_headers,
        )
        assert own_evidence_scope_response.status_code == 200
        scoped_evidence_titles = {item["title"] for item in own_evidence_scope_response.json()}
        assert "SOC2 evidence package" in scoped_evidence_titles
        assert "Other org evidence" not in scoped_evidence_titles

        own_mine_controls_response = await client.get(
            "/api/v1/compliance-registry/controls?scope=mine",
            headers=auth_headers,
        )
        assert own_mine_controls_response.status_code == 200
        mine_control_ids = {item["control_id"] for item in own_mine_controls_response.json()}
        assert "CC1.1" in mine_control_ids
        assert "OTHER-CTRL-1" not in mine_control_ids

        assert own_org.id != other_org.id

    @pytest.mark.asyncio
    async def test_organization_scope_requires_org_membership(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        controls_response = await client.get(
            "/api/v1/compliance-registry/controls?scope=organization",
            headers=auth_headers,
        )
        assert controls_response.status_code == 403

        evidence_response = await client.get(
            "/api/v1/compliance-registry/evidence?scope=organization",
            headers=auth_headers,
        )
        assert evidence_response.status_code == 403

    @pytest.mark.asyncio
    async def test_org_member_can_link_org_scoped_records_created_by_another_member(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        org = await _set_org_membership(
            db_session,
            user_id=test_user.id,
            role=OrgRole.ADMIN,
            slug_suffix=f"shared-{test_user.id}",
        )

        other_user = User(
            email=f"org-peer-{test_user.id}@example.com",
            hashed_password=hash_password("TestPassword123!"),
            full_name="Org Peer",
            company_name="Peer Org Inc",
            tier="professional",
            is_active=True,
            is_verified=True,
            organization_id=org.id,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        db_session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=other_user.id,
                role=OrgRole.MEMBER,
                is_active=True,
            )
        )
        await db_session.flush()

        shared_control = ComplianceControl(
            user_id=other_user.id,
            organization_id=org.id,
            framework=ControlFramework.FEDRAMP,
            control_id="AC-ORG-1",
            title="Org shared control",
            status=ControlStatus.IN_PROGRESS,
        )
        shared_evidence = ComplianceEvidence(
            user_id=other_user.id,
            organization_id=org.id,
            title="Org shared evidence",
            evidence_type=EvidenceType.POLICY,
        )
        db_session.add(shared_control)
        db_session.add(shared_evidence)
        await db_session.commit()
        await db_session.refresh(shared_control)
        await db_session.refresh(shared_evidence)

        link_response = await client.post(
            "/api/v1/compliance-registry/links",
            headers=auth_headers,
            json={
                "control_id": shared_control.id,
                "evidence_id": shared_evidence.id,
            },
        )
        assert link_response.status_code == 201

        control_evidence_response = await client.get(
            f"/api/v1/compliance-registry/controls/{shared_control.id}/evidence",
            headers=auth_headers,
        )
        assert control_evidence_response.status_code == 200
        evidence_ids = {item["id"] for item in control_evidence_response.json()}
        assert shared_evidence.id in evidence_ids
