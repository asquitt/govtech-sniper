"""
Tests for draft/generation routes - Section generation, rewrite, expand, scorecard.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal, ProposalSection, SectionStatus
from app.models.rfp import RFP, ComplianceMatrix
from app.models.user import User
from app.services.auth_service import create_token_pair


@pytest_asyncio.fixture
async def test_section(db_session: AsyncSession, test_proposal: Proposal) -> ProposalSection:
    section = ProposalSection(
        proposal_id=test_proposal.id,
        title="Technical Approach",
        section_number="L.1",
        requirement_id="REQ-001",
        requirement_text="Describe your technical approach",
        status=SectionStatus.PENDING,
        display_order=0,
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


@pytest_asyncio.fixture
async def test_section_with_content(
    db_session: AsyncSession, test_proposal: Proposal
) -> ProposalSection:
    section = ProposalSection(
        proposal_id=test_proposal.id,
        title="Past Performance",
        section_number="L.2",
        requirement_id="REQ-002",
        requirement_text="Describe past performance",
        status=SectionStatus.GENERATED,
        display_order=1,
        final_content="We have extensive past performance in cybersecurity services.",
        word_count=9,
        quality_score=85.0,
        quality_breakdown={"overall_score": 85.0},
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


@pytest_asyncio.fixture
async def test_compliance_matrix(db_session: AsyncSession, test_rfp: RFP) -> ComplianceMatrix:
    matrix = ComplianceMatrix(
        rfp_id=test_rfp.id,
        requirements=[
            {
                "id": "REQ-001",
                "section": "L.1",
                "requirement_text": "Technical approach",
                "importance": "mandatory",
                "is_addressed": False,
            },
            {
                "id": "REQ-002",
                "section": "L.2",
                "requirement_text": "Past performance",
                "importance": "evaluated",
                "is_addressed": False,
            },
        ],
        total_requirements=2,
        mandatory_count=1,
        addressed_count=0,
    )
    db_session.add(matrix)
    await db_session.commit()
    await db_session.refresh(matrix)
    return matrix


class TestGenerateSectionsFromMatrix:
    """Tests for POST /api/v1/draft/proposals/{proposal_id}/generate-from-matrix."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/generate-from-matrix",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_from_matrix_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_compliance_matrix: ComplianceMatrix,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/generate-from-matrix",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sections_created"] == 2
        assert data["proposal_id"] == test_proposal.id

    @pytest.mark.asyncio
    async def test_generate_from_matrix_skips_existing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_compliance_matrix: ComplianceMatrix,
        test_section: ProposalSection,
    ):
        """Sections matching existing requirement_ids should be skipped."""
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/generate-from-matrix",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # REQ-001 exists via test_section, so only REQ-002 should be created
        assert data["sections_created"] == 1

    @pytest.mark.asyncio
    async def test_generate_from_matrix_no_matrix_returns_400(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/generate-from-matrix",
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_from_matrix_other_user_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
        test_compliance_matrix: ComplianceMatrix,
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
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/generate-from-matrix",
            headers=other_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_from_matrix_nonexistent_proposal(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/v1/draft/proposals/99999/generate-from-matrix",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestRewriteSection:
    """Tests for POST /api/v1/draft/sections/{section_id}/rewrite."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_section_with_content: ProposalSection
    ):
        response = await client.post(
            f"/api/v1/draft/sections/{test_section_with_content.id}/rewrite",
            json={"tone": "technical"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rewrite_section_no_content_returns_400(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.post(
            f"/api/v1/draft/sections/{test_section.id}/rewrite",
            headers=auth_headers,
            json={"tone": "professional"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rewrite_section_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/draft/sections/99999/rewrite",
            headers=auth_headers,
            json={"tone": "professional"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_rewrite_section_idor_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_section_with_content: ProposalSection,
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
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/draft/sections/{test_section_with_content.id}/rewrite",
            headers=other_headers,
            json={"tone": "professional"},
        )
        assert response.status_code == 404


class TestExpandSection:
    """Tests for POST /api/v1/draft/sections/{section_id}/expand."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_section_with_content: ProposalSection
    ):
        response = await client.post(
            f"/api/v1/draft/sections/{test_section_with_content.id}/expand",
            json={"target_words": 800},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expand_section_no_content_returns_400(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.post(
            f"/api/v1/draft/sections/{test_section.id}/expand",
            headers=auth_headers,
            json={"target_words": 800},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_expand_section_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/draft/sections/99999/expand",
            headers=auth_headers,
            json={"target_words": 800},
        )
        assert response.status_code == 404


class TestGetGenerationProgress:
    """Tests for GET /api/v1/draft/proposals/{proposal_id}/generation-progress."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/generation-progress",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generation_progress_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_section: ProposalSection,
        test_section_with_content: ProposalSection,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/generation-progress",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["proposal_id"] == test_proposal.id
        assert data["total"] == 2
        assert data["pending"] >= 1
        assert data["generated"] >= 1
        assert "completion_percentage" in data

    @pytest.mark.asyncio
    async def test_generation_progress_empty_proposal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/generation-progress",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["completion_percentage"] == 0

    @pytest.mark.asyncio
    async def test_generation_progress_nonexistent_proposal(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get(
            "/api/v1/draft/proposals/99999/generation-progress",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generation_progress_idor_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
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
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/generation-progress",
            headers=other_headers,
        )
        assert response.status_code == 404


class TestGetProposalScorecard:
    """Tests for GET /api/v1/draft/proposals/{proposal_id}/scorecard."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/scorecard",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_scorecard_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_section: ProposalSection,
        test_section_with_content: ProposalSection,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/scorecard",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["proposal_id"] == test_proposal.id
        assert data["sections_total"] == 2
        assert data["sections_scored"] >= 1
        assert "overall_score" in data
        assert "pink_team_ready" in data
        assert len(data["section_scores"]) == 2

    @pytest.mark.asyncio
    async def test_scorecard_empty_proposal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/scorecard",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sections_total"] == 0
        assert data["overall_score"] is None
        assert data["pink_team_ready"] is False

    @pytest.mark.asyncio
    async def test_scorecard_nonexistent_proposal(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/draft/proposals/99999/scorecard",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_scorecard_idor_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
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
        tokens = create_token_pair(other.id, other.email, other.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/scorecard",
            headers=other_headers,
        )
        assert response.status_code == 404
