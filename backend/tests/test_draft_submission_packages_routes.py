"""
Integration tests for draft/submission_packages.py:
  - GET   /draft/proposals/{id}/submission-packages
  - POST  /draft/proposals/{id}/submission-packages
  - PATCH /draft/submission-packages/{id}
  - POST  /draft/submission-packages/{id}/submit
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proposal import Proposal, SubmissionPackage
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestListSubmissionPackages:
    """Tests for GET /api/v1/draft/proposals/{id}/submission-packages."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/draft/proposals/1/submission-packages")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/submission-packages",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
        db_session: AsyncSession,
    ):
        pkg = SubmissionPackage(
            proposal_id=test_proposal.id,
            title="Volume I",
            checklist=[],
        )
        db_session.add(pkg)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/submission-packages",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Volume I"

    @pytest.mark.asyncio
    async def test_list_proposal_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.get(
            "/api/v1/draft/proposals/99999/submission-packages",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        db_session: AsyncSession,
    ):
        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/submission-packages",
            headers=headers,
        )
        assert response.status_code == 404


class TestCreateSubmissionPackage:
    """Tests for POST /api/v1/draft/proposals/{id}/submission-packages."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/draft/proposals/1/submission-packages",
            json={"title": "Volume I"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.post(
            f"/api/v1/draft/proposals/{test_proposal.id}/submission-packages",
            headers=auth_headers,
            json={"title": "Volume I", "notes": "Technical volume"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Volume I"
        assert data["notes"] == "Technical volume"
        assert data["proposal_id"] == test_proposal.id

    @pytest.mark.asyncio
    async def test_create_proposal_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/draft/proposals/99999/submission-packages",
            headers=auth_headers,
            json={"title": "Volume I"},
        )
        assert response.status_code == 404


class TestUpdateSubmissionPackage:
    """Tests for PATCH /api/v1/draft/submission-packages/{id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(
            "/api/v1/draft/submission-packages/1",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
        db_session: AsyncSession,
    ):
        pkg = SubmissionPackage(
            proposal_id=test_proposal.id,
            title="Volume I",
            checklist=[],
        )
        db_session.add(pkg)
        await db_session.commit()
        await db_session.refresh(pkg)

        response = await client.patch(
            f"/api/v1/draft/submission-packages/{pkg.id}",
            headers=auth_headers,
            json={"title": "Volume I - Updated"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Volume I - Updated"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.patch(
            "/api/v1/draft/submission-packages/99999",
            headers=auth_headers,
            json={"title": "Updated"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        db_session: AsyncSession,
    ):
        pkg = SubmissionPackage(
            proposal_id=test_proposal.id,
            title="Volume I",
            checklist=[],
        )
        db_session.add(pkg)
        await db_session.commit()
        await db_session.refresh(pkg)

        other = User(
            email="other2@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"/api/v1/draft/submission-packages/{pkg.id}",
            headers=headers,
            json={"title": "Hacked"},
        )
        assert response.status_code == 404


class TestSubmitSubmissionPackage:
    """Tests for POST /api/v1/draft/submission-packages/{id}/submit."""

    @pytest.mark.asyncio
    async def test_submit_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/draft/submission-packages/1/submit")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
        db_session: AsyncSession,
    ):
        pkg = SubmissionPackage(
            proposal_id=test_proposal.id,
            title="Volume I",
            checklist=[],
        )
        db_session.add(pkg)
        await db_session.commit()
        await db_session.refresh(pkg)

        response = await client.post(
            f"/api/v1/draft/submission-packages/{pkg.id}/submit",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None

    @pytest.mark.asyncio
    async def test_submit_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/draft/submission-packages/99999/submit",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_idor(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        db_session: AsyncSession,
    ):
        pkg = SubmissionPackage(
            proposal_id=test_proposal.id,
            title="Volume I",
            checklist=[],
        )
        db_session.add(pkg)
        await db_session.commit()
        await db_session.refresh(pkg)

        other = User(
            email="other3@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/draft/submission-packages/{pkg.id}/submit",
            headers=headers,
        )
        assert response.status_code == 404
