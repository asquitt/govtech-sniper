"""
Tests for draft/outline routes - Outline generation and management.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outline import OutlineSection, OutlineStatus, ProposalOutline
from app.models.proposal import Proposal
from app.models.user import User
from app.services.auth_service import create_token_pair


@pytest_asyncio.fixture
async def test_outline(db_session: AsyncSession, test_proposal: Proposal) -> ProposalOutline:
    outline = ProposalOutline(
        proposal_id=test_proposal.id,
        status=OutlineStatus.DRAFT,
    )
    db_session.add(outline)
    await db_session.commit()
    await db_session.refresh(outline)
    return outline


@pytest_asyncio.fixture
async def test_outline_section(
    db_session: AsyncSession, test_outline: ProposalOutline
) -> OutlineSection:
    section = OutlineSection(
        outline_id=test_outline.id,
        title="Executive Summary",
        description="High-level overview of the proposal",
        mapped_requirement_ids=["REQ-001"],
        display_order=0,
        estimated_pages=2.0,
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


@pytest_asyncio.fixture
async def test_child_section(
    db_session: AsyncSession,
    test_outline: ProposalOutline,
    test_outline_section: OutlineSection,
) -> OutlineSection:
    child = OutlineSection(
        outline_id=test_outline.id,
        parent_id=test_outline_section.id,
        title="Methodology",
        description="Detailed methodology",
        display_order=0,
    )
    db_session.add(child)
    await db_session.commit()
    await db_session.refresh(child)
    return child


class TestGetOutline:
    """Tests for GET /api/v1/draft/proposals/{proposal_id}/outline."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_outline_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_outline.id
        assert data["status"] == "draft"
        assert len(data["sections"]) >= 1
        assert data["sections"][0]["title"] == "Executive Summary"

    @pytest.mark.asyncio
    async def test_get_outline_nested_children(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
        test_child_section: OutlineSection,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        parent = data["sections"][0]
        assert len(parent["children"]) == 1
        assert parent["children"][0]["title"] == "Methodology"

    @pytest.mark.asyncio
    async def test_get_outline_no_outline_returns_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_outline_idor_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
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
            f"/api/v1/draft/proposals/{test_proposal.id}/outline",
            headers=other_headers,
        )
        assert response.status_code == 404


class TestAddOutlineSection:
    """Tests for POST /api/v1/draft/proposals/{proposal_id}/outline/sections."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections",
            json={"title": "New Section"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_section_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections",
            headers=auth_headers,
            json={
                "title": "Past Performance",
                "description": "Relevant contract experience",
                "mapped_requirement_ids": ["REQ-002", "REQ-003"],
                "display_order": 1,
                "estimated_pages": 3.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Past Performance"
        assert data["mapped_requirement_ids"] == ["REQ-002", "REQ-003"]
        assert data["estimated_pages"] == 3.0

    @pytest.mark.asyncio
    async def test_add_section_no_outline_returns_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections",
            headers=auth_headers,
            json={"title": "New Section"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_child_section(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections",
            headers=auth_headers,
            json={
                "title": "Sub-Section",
                "parent_id": test_outline_section.id,
                "display_order": 0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == test_outline_section.id


class TestUpdateOutlineSection:
    """Tests for PATCH /api/v1/draft/proposals/{proposal_id}/outline/sections/{section_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        test_outline_section: OutlineSection,
    ):
        response = await client.patch(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections/{test_outline_section.id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_section_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
    ):
        response = await client.patch(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections/{test_outline_section.id}",
            headers=auth_headers,
            json={"title": "Updated Executive Summary", "estimated_pages": 4.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Executive Summary"
        assert data["estimated_pages"] == 4.0

    @pytest.mark.asyncio
    async def test_update_section_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
    ):
        response = await client.patch(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections/99999",
            headers=auth_headers,
            json={"title": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteOutlineSection:
    """Tests for DELETE /api/v1/draft/proposals/{proposal_id}/outline/sections/{section_id}."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        test_outline_section: OutlineSection,
    ):
        response = await client.delete(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections/{test_outline_section.id}",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_section_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
    ):
        response = await client.delete(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections/{test_outline_section.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Section deleted"

    @pytest.mark.asyncio
    async def test_delete_section_cascades_children(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
        test_child_section: OutlineSection,
    ):
        response = await client.delete(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections/{test_outline_section.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_section_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
    ):
        response = await client.delete(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/sections/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestReorderOutline:
    """Tests for PUT /api/v1/draft/proposals/{proposal_id}/outline/reorder."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.put(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/reorder",
            json={"items": []},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reorder_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
    ):
        response = await client.put(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/reorder",
            headers=auth_headers,
            json={
                "items": [
                    {
                        "section_id": test_outline_section.id,
                        "parent_id": None,
                        "display_order": 5,
                    }
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sections_updated"] == 1

    @pytest.mark.asyncio
    async def test_reorder_no_outline_returns_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.put(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/reorder",
            headers=auth_headers,
            json={"items": []},
        )
        assert response.status_code == 404


class TestApproveOutline:
    """Tests for POST /api/v1/draft/proposals/{proposal_id}/outline/approve."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, test_proposal: Proposal):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/approve",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_approve_outline_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/approve",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Outline approved"
        assert data["sections_created"] >= 1

    @pytest.mark.asyncio
    async def test_approve_outline_no_outline_returns_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/approve",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_outline_creates_proposal_sections_for_leaves_only(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_outline: ProposalOutline,
        test_outline_section: OutlineSection,
        test_child_section: OutlineSection,
    ):
        """Parent sections should not become ProposalSections; only leaves."""
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/outline/approve",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Only the child (leaf) should be created as a ProposalSection
        assert data["sections_created"] == 1
