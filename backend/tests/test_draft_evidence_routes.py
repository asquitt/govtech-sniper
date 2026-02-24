"""
Tests for draft/evidence routes - Section Evidence CRUD.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.proposal import Proposal, ProposalSection, SectionEvidence, SectionStatus
from app.models.user import User
from app.services.auth_service import create_token_pair


@pytest_asyncio.fixture
async def test_section(db_session: AsyncSession, test_proposal: Proposal) -> ProposalSection:
    section = ProposalSection(
        proposal_id=test_proposal.id,
        title="Evidence Test Section",
        section_number="E.1",
        requirement_id="REQ-E1",
        requirement_text="Evidence requirement",
        status=SectionStatus.PENDING,
        display_order=0,
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


@pytest_asyncio.fixture
async def test_evidence(
    db_session: AsyncSession,
    test_section: ProposalSection,
    test_document: KnowledgeBaseDocument,
) -> SectionEvidence:
    evidence = SectionEvidence(
        section_id=test_section.id,
        document_id=test_document.id,
        citation="Page 5, Section 2.1",
        notes="Key capability statement",
    )
    db_session.add(evidence)
    await db_session.commit()
    await db_session.refresh(evidence)
    return evidence


class TestListSectionEvidence:
    """Tests for GET /api/v1/draft/sections/{section_id}/evidence."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_section: ProposalSection
    ):
        response = await client.get(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_evidence_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
        test_evidence: SectionEvidence,
    ):
        response = await client.get(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["citation"] == "Page 5, Section 2.1"
        assert data[0]["document_title"] is not None

    @pytest.mark.asyncio
    async def test_list_evidence_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.get(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_list_evidence_idor_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_section: ProposalSection,
    ):
        other = User(
            email="other@example.com",
            hashed_password="hashed",
            full_name="Other User",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            headers=other_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_evidence_section_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/draft/sections/99999/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestAddSectionEvidence:
    """Tests for POST /api/v1/draft/sections/{section_id}/evidence."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_section: ProposalSection,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.post(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            json={"document_id": test_document.id, "citation": "Page 1"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_evidence_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.post(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            headers=auth_headers,
            json={
                "document_id": test_document.id,
                "citation": "Page 3, Table 1",
                "notes": "Past performance data",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_document.id
        assert data["citation"] == "Page 3, Table 1"
        assert data["notes"] == "Past performance data"
        assert data["document_title"] is not None

    @pytest.mark.asyncio
    async def test_add_evidence_document_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.post(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            headers=auth_headers,
            json={"document_id": 99999, "citation": "Page 1"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_evidence_other_user_document_returns_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_section: ProposalSection,
    ):
        other = User(
            email="other@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)

        other_doc = KnowledgeBaseDocument(
            user_id=other.id,
            title="Other Doc",
            document_type="past_performance",
            original_filename="other.pdf",
            file_path="/uploads/other.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status="ready",
            is_ready=True,
        )
        db_session.add(other_doc)
        await db_session.commit()
        await db_session.refresh(other_doc)

        response = await client.post(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            headers=auth_headers,
            json={"document_id": other_doc.id, "citation": "Page 1"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_evidence_section_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.post(
            "/api/v1/draft/sections/99999/evidence",
            headers=auth_headers,
            json={"document_id": test_document.id, "citation": "Page 1"},
        )
        assert response.status_code == 404


class TestDeleteSectionEvidence:
    """Tests for DELETE /api/v1/draft/sections/{section_id}/evidence/{evidence_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_section: ProposalSection,
        test_evidence: SectionEvidence,
    ):
        response = await client.delete(
            f"/api/v1/draft/sections/{test_section.id}/evidence/{test_evidence.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_evidence_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
        test_evidence: SectionEvidence,
    ):
        response = await client.delete(
            f"/api/v1/draft/sections/{test_section.id}/evidence/{test_evidence.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Evidence deleted"

        # Verify it's gone
        response2 = await client.get(
            f"/api/v1/draft/sections/{test_section.id}/evidence",
            headers=auth_headers,
        )
        assert response2.status_code == 200
        assert len(response2.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_evidence_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.delete(
            f"/api/v1/draft/sections/{test_section.id}/evidence/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_evidence_idor_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_section: ProposalSection,
        test_evidence: SectionEvidence,
    ):
        other = User(
            email="other@example.com",
            hashed_password="hashed",
            full_name="Other User",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.delete(
            f"/api/v1/draft/sections/{test_section.id}/evidence/{test_evidence.id}",
            headers=other_headers,
        )
        assert response.status_code == 404
