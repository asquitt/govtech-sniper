"""
Integration tests for versions.py — /versions/ proposal and section version history
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import (
    Proposal,
    ProposalSection,
    ProposalVersion,
    ProposalVersionType,
    SectionVersion,
)
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    user2 = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    tokens = create_token_pair(user2.id, user2.email, user2.tier)
    return user2, {"Authorization": f"Bearer {tokens.access_token}"}


async def _create_section(db_session: AsyncSession, proposal: Proposal) -> ProposalSection:
    section = ProposalSection(
        proposal_id=proposal.id,
        title="Technical Approach",
        section_type="technical",
        section_number="1.0",
        order_index=0,
        final_content="Initial content here.",
        word_count=3,
    )
    db_session.add(section)
    await db_session.commit()
    await db_session.refresh(section)
    return section


class TestListProposalVersions:
    """GET /api/v1/versions/proposals/{proposal_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/versions/proposals/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_versions(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        response = await client.get(
            f"/api/v1/versions/proposals/{test_proposal.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        version = ProposalVersion(
            proposal_id=test_proposal.id,
            user_id=test_user.id,
            version_number=1,
            version_type=ProposalVersionType.CREATED,
            description="Manual save",
            snapshot={"title": test_proposal.title},
        )
        db_session.add(version)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/versions/proposals/{test_proposal.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["version_number"] == 1
        assert data[0]["description"] == "Manual save"

    @pytest.mark.asyncio
    async def test_proposal_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/versions/proposals/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_proposal_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        user2, _ = await _create_second_user(db_session)
        other_rfp = RFP(
            user_id=user2.id,
            title="Other RFP",
            solicitation_number="OTHER-001",
            notice_id="other-notice",
            agency="Other Agency",
            rfp_type="solicitation",
            status="new",
        )
        db_session.add(other_rfp)
        await db_session.flush()
        other_proposal = Proposal(
            user_id=user2.id,
            rfp_id=other_rfp.id,
            title="Other's Proposal",
            status="draft",
        )
        db_session.add(other_proposal)
        await db_session.commit()
        await db_session.refresh(other_proposal)

        response = await client.get(
            f"/api/v1/versions/proposals/{other_proposal.id}", headers=auth_headers
        )
        assert response.status_code == 404


class TestGetProposalVersion:
    """GET /api/v1/versions/proposals/{proposal_id}/version/{version_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/versions/proposals/1/version/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_version_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        version = ProposalVersion(
            proposal_id=test_proposal.id,
            user_id=test_user.id,
            version_number=1,
            version_type=ProposalVersionType.CREATED,
            description="Detail test",
            snapshot={"title": "Snap"},
        )
        db_session.add(version)
        await db_session.commit()
        await db_session.refresh(version)

        response = await client.get(
            f"/api/v1/versions/proposals/{test_proposal.id}/version/{version.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["snapshot"]["title"] == "Snap"

    @pytest.mark.asyncio
    async def test_version_not_found(
        self, client: AsyncClient, auth_headers: dict, test_proposal: Proposal
    ):
        response = await client.get(
            f"/api/v1/versions/proposals/{test_proposal.id}/version/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListSectionVersions:
    """GET /api/v1/versions/sections/{section_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/versions/sections/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_section_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        section = await _create_section(db_session, test_proposal)
        sv = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=1,
            content="Version 1 content",
            word_count=3,
            change_type="manual_edit",
        )
        db_session.add(sv)
        await db_session.commit()

        response = await client.get(f"/api/v1/versions/sections/{section.id}", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_section_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get("/api/v1/versions/sections/99999", headers=auth_headers)
        assert response.status_code == 404


class TestGetSectionVersion:
    """GET /api/v1/versions/sections/{section_id}/version/{version_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/versions/sections/1/version/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_section_version_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        section = await _create_section(db_session, test_proposal)
        sv = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=1,
            content="Detailed content",
            word_count=2,
            change_type="manual_edit",
        )
        db_session.add(sv)
        await db_session.commit()
        await db_session.refresh(sv)

        response = await client.get(
            f"/api/v1/versions/sections/{section.id}/version/{sv.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Detailed content"


class TestRestoreSectionVersion:
    """POST /api/v1/versions/sections/{section_id}/restore"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/versions/sections/1/restore", json={"version_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_restore_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        section = await _create_section(db_session, test_proposal)
        sv = SectionVersion(
            section_id=section.id,
            user_id=test_user.id,
            version_number=1,
            content="Old content to restore",
            word_count=4,
            change_type="manual_edit",
        )
        db_session.add(sv)
        await db_session.commit()
        await db_session.refresh(sv)

        response = await client.post(
            f"/api/v1/versions/sections/{section.id}/restore",
            headers=auth_headers,
            json={"version_id": sv.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["restored_version"] == 1

    @pytest.mark.asyncio
    async def test_restore_section_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/versions/sections/99999/restore",
            headers=auth_headers,
            json={"version_id": 1},
        )
        assert response.status_code == 404


class TestCompareSectionVersions:
    """GET /api/v1/versions/sections/{section_id}/compare"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/versions/sections/1/compare",
            params={"version_a": 1, "version_b": 2},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_compare_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        section = await _create_section(db_session, test_proposal)
        for i in [1, 2]:
            db_session.add(
                SectionVersion(
                    section_id=section.id,
                    user_id=test_user.id,
                    version_number=i,
                    content=f"Content v{i}",
                    word_count=2,
                    change_type="manual_edit",
                )
            )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/versions/sections/{section.id}/compare",
            headers=auth_headers,
            params={"version_a": 1, "version_b": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version_a"]["content"] == "Content v1"
        assert data["version_b"]["content"] == "Content v2"

    @pytest.mark.asyncio
    async def test_compare_missing_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_proposal: Proposal,
    ):
        section = await _create_section(db_session, test_proposal)
        db_session.add(
            SectionVersion(
                section_id=section.id,
                user_id=test_user.id,
                version_number=1,
                content="Only v1",
                word_count=2,
                change_type="manual_edit",
            )
        )
        await db_session.commit()

        response = await client.get(
            f"/api/v1/versions/sections/{section.id}/compare",
            headers=auth_headers,
            params={"version_a": 1, "version_b": 99},
        )
        assert response.status_code == 404
