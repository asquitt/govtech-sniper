"""
Tests for draft/sections routes - Section CRUD operations.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal, ProposalSection, SectionStatus
from app.models.user import User
from app.services.auth_service import create_token_pair

VALID_SECTION_PAYLOAD = {
    "title": "Technical Approach",
    "section_number": "L.1",
    "requirement_id": "REQ-001",
    "requirement_text": "Describe your technical approach",
    "display_order": 0,
}


@pytest_asyncio.fixture
async def test_section(db_session: AsyncSession, test_proposal: Proposal) -> ProposalSection:
    """Create a test proposal section."""
    section = ProposalSection(
        proposal_id=test_proposal.id,
        title="Existing Section",
        section_number="L.0",
        requirement_id="REQ-000",
        requirement_text="Existing requirement",
        status=SectionStatus.PENDING,
        display_order=0,
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


class TestCreateSection:
    """Tests for POST /api/v1/draft/proposals/{proposal_id}/sections."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/sections",
            json=VALID_SECTION_PAYLOAD,
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_section_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/sections",
            headers=auth_headers,
            json=VALID_SECTION_PAYLOAD,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Technical Approach"
        assert data["section_number"] == "L.1"
        assert data["requirement_id"] == "REQ-001"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_section_other_user_proposal_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
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

        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/sections",
            headers=other_headers,
            json=VALID_SECTION_PAYLOAD,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_section_nonexistent_proposal_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/v1/draft/proposals/99999/sections",
            headers=auth_headers,
            json=VALID_SECTION_PAYLOAD,
        )
        assert response.status_code == 404


class TestListSections:
    """Tests for GET /api/v1/draft/proposals/{proposal_id}/sections."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/sections",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_sections_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_section: ProposalSection,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/sections",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["title"] == "Existing Section"

    @pytest.mark.asyncio
    async def test_list_sections_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_section: ProposalSection,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/sections?status=pending",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "pending" for s in data)

    @pytest.mark.asyncio
    async def test_list_sections_other_user_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
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
            f"/api/v1/draft/proposals/{test_proposal.id}/sections",
            headers=other_headers,
        )
        assert response.status_code == 404


class TestGetSection:
    """Tests for GET /api/v1/draft/sections/{section_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_section: ProposalSection
    ):
        response = await client.get(
            f"/api/v1/draft/sections/{test_section.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_section_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.get(
            f"/api/v1/draft/sections/{test_section.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_section.id
        assert data["title"] == "Existing Section"

    @pytest.mark.asyncio
    async def test_get_section_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/draft/sections/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_section_idor_returns_404(
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
            f"/api/v1/draft/sections/{test_section.id}",
            headers=other_headers,
        )
        assert response.status_code == 404


class TestUpdateSection:
    """Tests for PATCH /api/v1/draft/sections/{section_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, test_section: ProposalSection
    ):
        response = await client.patch(
            f"/api/v1/draft/sections/{test_section.id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_section_title(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.patch(
            f"/api/v1/draft/sections/{test_section.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_section_final_content_sets_word_count(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        content = "This is the final content for the section with multiple words"
        response = await client.patch(
            f"/api/v1/draft/sections/{test_section.id}",
            headers=auth_headers,
            json={"final_content": content},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["word_count"] == len(content.split())
        assert data["status"] == "editing"

    @pytest.mark.asyncio
    async def test_update_section_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.patch(
            f"/api/v1/draft/sections/{test_section.id}",
            headers=auth_headers,
            json={"status": "approved"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    @pytest.mark.asyncio
    async def test_update_section_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/draft/sections/99999",
            headers=auth_headers,
            json={"title": "Updated"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_section_idor_returns_404(
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

        response = await client.patch(
            f"/api/v1/draft/sections/{test_section.id}",
            headers=other_headers,
            json={"title": "Hacked"},
        )
        assert response.status_code == 404


class TestAssignSection:
    """Tests for PATCH /api/v1/draft/sections/{section_id}/assign."""

    @pytest.mark.asyncio
    async def test_assign_section_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_section: ProposalSection,
    ):
        response = await client.patch(
            f"/api/v1/draft/sections/{test_section.id}/assign",
            headers=auth_headers,
            json={"assigned_to_user_id": test_user.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to_user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_unassign_section(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_section: ProposalSection,
    ):
        response = await client.patch(
            f"/api/v1/draft/sections/{test_section.id}/assign",
            headers=auth_headers,
            json={"assigned_to_user_id": None},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to_user_id"] is None

    @pytest.mark.asyncio
    async def test_assign_section_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/draft/sections/99999/assign",
            headers=auth_headers,
            json={"assigned_to_user_id": 1},
        )
        assert response.status_code == 404
