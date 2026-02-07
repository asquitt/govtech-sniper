"""
RFP Sniper - Version History Tests
==================================
Tests for proposal and section version history.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal, ProposalSection, SectionVersion
from app.models.user import User


class TestProposalVersions:
    """Tests for proposal version history."""

    @pytest.mark.asyncio
    async def test_list_proposal_versions_empty(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        """Test listing versions when none exist."""
        response = await client.get(
            f"/api/v1/versions/proposals/{test_proposal.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_proposal_versions_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test listing versions for non-existent proposal."""
        response = await client.get(
            "/api/v1/versions/proposals/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestSectionVersions:
    """Tests for section version history."""

    @pytest.mark.asyncio
    async def test_create_and_list_section_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
        test_user: User,
    ):
        """Test creating and listing section versions."""
        # Create a section
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Technical Approach",
            section_number="3.1",
            final_content="Initial content for the technical approach section.",
            word_count=7,
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        # Create a version manually
        version = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=1,
            content="Initial content for the technical approach section.",
            word_count=7,
            change_type="generated",
            change_summary="Initial generation",
        )
        db_session.add(version)
        await db_session.commit()

        # List versions
        response = await client.get(
            f"/api/v1/versions/sections/{section.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["version_number"] == 1
        assert data[0]["change_type"] == "generated"

    @pytest.mark.asyncio
    async def test_get_section_version_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
        test_user: User,
    ):
        """Test getting detailed section version."""
        # Create section and version
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Management Approach",
            section_number="4.0",
            final_content="Management approach content.",
            word_count=3,
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        version = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=1,
            content="Management approach content.",
            word_count=3,
            change_type="generated",
        )
        db_session.add(version)
        await db_session.commit()
        await db_session.refresh(version)

        # Get version detail
        response = await client.get(
            f"/api/v1/versions/sections/{section.id}/version/{version.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_number"] == 1
        assert data["content"] == "Management approach content."

    @pytest.mark.asyncio
    async def test_restore_section_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
        test_user: User,
    ):
        """Test restoring a section to a previous version."""
        # Create section
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Executive Summary",
            section_number="1.0",
            final_content="Current content that will be replaced.",
            word_count=6,
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        # Create original version
        original_version = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=1,
            content="Original content to restore to.",
            word_count=5,
            change_type="generated",
        )
        db_session.add(original_version)
        await db_session.commit()
        await db_session.refresh(original_version)

        # Restore to original version
        response = await client.post(
            f"/api/v1/versions/sections/{section.id}/restore",
            headers=auth_headers,
            json={"version_id": original_version.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["restored_version"] == 1

        # Verify content was restored
        await db_session.refresh(section)
        assert section.final_content == "Original content to restore to."

    @pytest.mark.asyncio
    async def test_compare_section_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
        test_user: User,
    ):
        """Test comparing two section versions."""
        # Create section
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Staffing Plan",
            section_number="5.0",
            final_content="Version 2 content.",
            word_count=3,
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        # Create two versions
        v1 = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=1,
            content="Version 1 content.",
            word_count=3,
            change_type="generated",
        )
        v2 = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=2,
            content="Version 2 content with updates.",
            word_count=5,
            change_type="edited",
        )
        db_session.add_all([v1, v2])
        await db_session.commit()

        # Compare versions
        response = await client.get(
            f"/api/v1/versions/sections/{section.id}/compare",
            headers=auth_headers,
            params={"version_a": 1, "version_b": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_a"]["version_number"] == 1
        assert data["version_b"]["version_number"] == 2
        assert data["version_a"]["content"] == "Version 1 content."
        assert data["version_b"]["content"] == "Version 2 content with updates."

    @pytest.mark.asyncio
    async def test_compare_nonexistent_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """Test comparing with non-existent versions."""
        section = ProposalSection(
            proposal_id=test_proposal.id,
            title="Test Section",
            section_number="9.0",
        )
        db_session.add(section)
        await db_session.commit()
        await db_session.refresh(section)

        response = await client.get(
            f"/api/v1/versions/sections/{section.id}/compare",
            headers=auth_headers,
            params={"version_a": 1, "version_b": 2},
        )
        assert response.status_code == 404


class TestVersionAccessControl:
    """Tests for version access control."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_user_versions(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_proposal: Proposal,
    ):
        """Test that users cannot access other users' proposal versions."""
        # Create another user and get their auth headers
        from app.models.user import User
        from app.services.auth_service import create_token_pair, hash_password

        other_user = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
            tier="free",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        other_headers = {"Authorization": f"Bearer {tokens.access_token}"}

        # Try to access test_proposal versions with other user's token
        response = await client.get(
            f"/api/v1/versions/proposals/{test_proposal.id}",
            headers=other_headers,
        )
        assert response.status_code == 404  # Proposal not found for this user
