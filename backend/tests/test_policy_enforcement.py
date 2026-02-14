"""Tests for policy engine enforcement on export routes."""

import io
import json
import zipfile

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.capture import BidScorecard, BidScorecardRecommendation, ScorerType
from app.models.knowledge_base import DocumentType, KnowledgeBaseDocument, ProcessingStatus
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.proposal import Proposal, ProposalSection, SectionEvidence
from app.models.review import (
    ChecklistItemStatus,
    CommentSeverity,
    CommentStatus,
    ProposalReview,
    ReviewChecklistItem,
    ReviewComment,
    ReviewStatus,
    ReviewType,
)
from app.models.rfp import RFP
from app.models.user import User


async def _setup_proposal(db_session: AsyncSession, user_id: int, classification: str) -> int:
    """Create an RFP + proposal with the given classification for testing."""
    rfp = RFP(
        title="Test RFP",
        solicitation_number=f"TEST-POL-{classification}",
        agency="Test Agency",
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


async def _set_org_role(
    db_session: AsyncSession,
    user_id: int,
    role: OrgRole,
    org_settings: dict | None = None,
):
    """Assign user to an org with the given role."""
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    result = await db_session.execute(select(Organization).limit(1))
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()
    if org_settings:
        settings = dict(org.settings) if isinstance(org.settings, dict) else {}
        settings.update(org_settings)
        org.settings = settings
        db_session.add(org)

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
    user.organization_id = org.id
    db_session.add(user)
    await db_session.commit()


async def _enable_mfa(db_session: AsyncSession, user: User) -> str:
    secret = pyotp.random_base32()
    user.mfa_enabled = True
    user.mfa_secret = secret
    db_session.add(user)
    await db_session.commit()
    return secret


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
    async def test_export_cui_step_up_succeeds_with_valid_mfa_code(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.ADMIN)
        secret = await _enable_mfa(db_session, user)
        proposal_id = await _setup_proposal(db_session, user.id, "cui")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers={**auth_headers, "X-Step-Up-Code": pyotp.TOTP(secret).now()},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_cui_step_up_rejects_invalid_code(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.ADMIN)
        await _enable_mfa(db_session, user)
        proposal_id = await _setup_proposal(db_session, user.id, "cui")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers={**auth_headers, "X-Step-Up-Code": "000000"},
        )
        assert response.status_code == 403
        assert response.headers.get("x-step-up-required") == "true"

    @pytest.mark.asyncio
    async def test_export_cui_step_up_can_be_disabled_by_org_policy(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(
            db_session,
            user.id,
            OrgRole.ADMIN,
            org_settings={"require_step_up_for_sensitive_exports": False},
        )
        proposal_id = await _setup_proposal(db_session, user.id, "cui")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/docx",
            headers=auth_headers,
        )
        assert response.status_code == 200

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

    @pytest.mark.asyncio
    async def test_compliance_package_export_policy_enforced(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.VIEWER)
        proposal_id = await _setup_proposal(db_session, user.id, "fci")

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/compliance-package/zip",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_compliance_package_export_contains_manifest_and_sections(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        user = (await db_session.execute(select(User).limit(1))).scalar_one()
        await _set_org_role(db_session, user.id, OrgRole.MEMBER)
        proposal_id = await _setup_proposal(db_session, user.id, "internal")
        proposal = (
            await db_session.execute(select(Proposal).where(Proposal.id == proposal_id))
        ).scalar_one()
        db_session.add(
            ProposalSection(
                proposal_id=proposal.id,
                title="Technical Approach",
                section_number="1.0",
                requirement_id="REQ-001",
                requirement_text="Contractor shall provide SOC operations support.",
                display_order=1,
                final_content=(
                    "Our SOC operations support model is based on ITIL-aligned playbooks."
                ),
            )
        )
        await db_session.flush()

        section = (
            await db_session.execute(
                select(ProposalSection).where(ProposalSection.proposal_id == proposal_id)
            )
        ).scalar_one()

        document = KnowledgeBaseDocument(
            user_id=user.id,
            title="SOC Support Playbook",
            document_type=DocumentType.TECHNICAL_SPEC,
            original_filename="soc-playbook.pdf",
            file_path="/tmp/soc-playbook.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=ProcessingStatus.READY,
            full_text="SOC operations playbook and staffing model.",
        )
        db_session.add(document)
        await db_session.flush()

        db_session.add(
            SectionEvidence(
                section_id=section.id,  # type: ignore[arg-type]
                document_id=document.id,  # type: ignore[arg-type]
                citation="SOC Playbook, Section 2.1",
                notes="Primary evidence for staffing model.",
            )
        )

        db_session.add(
            BidScorecard(
                rfp_id=proposal.rfp_id,
                user_id=user.id,
                criteria_scores=[
                    {"name": "technical_capability", "weight": 30, "score": 82},
                    {"name": "past_performance", "weight": 20, "score": 76},
                    {"name": "price_competitiveness", "weight": 20, "score": 72},
                    {"name": "teaming_strength", "weight": 15, "score": 70},
                    {"name": "proposal_timeline", "weight": 15, "score": 74},
                ],
                overall_score=76.4,
                recommendation=BidScorecardRecommendation.BID,
                confidence=0.81,
                reasoning="Strong technical and staffing posture.",
                scorer_type=ScorerType.HUMAN,
                scorer_id=user.id,
            )
        )

        review = ProposalReview(
            proposal_id=proposal.id,
            review_type=ReviewType.RED,
            status=ReviewStatus.IN_PROGRESS,
            summary="Red review in progress",
        )
        db_session.add(review)
        await db_session.flush()

        db_session.add(
            ReviewChecklistItem(
                review_id=review.id,  # type: ignore[arg-type]
                category="Compliance",
                item_text="All mandatory requirements mapped.",
                status=ChecklistItemStatus.PASS,
                display_order=1,
            )
        )
        db_session.add(
            ReviewComment(
                review_id=review.id,  # type: ignore[arg-type]
                section_id=section.id,  # type: ignore[arg-type]
                reviewer_user_id=user.id,
                comment_text="Clarify operational transition timeline details.",
                severity=CommentSeverity.MAJOR,
                status=CommentStatus.OPEN,
            )
        )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/export/proposals/{proposal_id}/compliance-package/zip",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/zip")

        archive = zipfile.ZipFile(io.BytesIO(response.content))
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "sections.json" in names
        assert "proposal.docx" in names
        assert "source-trace.json" in names
        assert "section-decisions.json" in names
        assert "reviews/review-packets.json" in names
        assert "reviews/review-outcomes.json" in names
        assert "capture/bid-stress-test.json" in names

        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["proposal"]["id"] == proposal_id
        assert manifest["summary"]["total_sections"] >= 1
        assert manifest["summary"]["source_trace_links"] >= 1
        assert manifest["summary"]["review_packets_included"] >= 1
        assert manifest["summary"]["bid_stress_test_included"] is True

        source_trace = json.loads(archive.read("source-trace.json").decode("utf-8"))
        assert len(source_trace) >= 1
        assert source_trace[0]["document_filename"] == "soc-playbook.pdf"

        section_decisions = json.loads(archive.read("section-decisions.json").decode("utf-8"))
        assert len(section_decisions) >= 1
        assert section_decisions[0]["linked_evidence_count"] >= 1

        review_packets = json.loads(archive.read("reviews/review-packets.json").decode("utf-8"))
        assert len(review_packets) >= 1
        assert review_packets[0]["review_type"] == "red"
        assert "action_queue" in review_packets[0]

        stress_test = json.loads(archive.read("capture/bid-stress-test.json").decode("utf-8"))
        assert stress_test["baseline"]["overall_score"] > 0
        assert len(stress_test["scenarios"]) >= 1
