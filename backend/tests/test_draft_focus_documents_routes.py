"""
Integration tests for draft/focus_documents.py:
  - GET  /draft/proposals/{id}/focus-documents
  - PUT  /draft/proposals/{id}/focus-documents
  - DELETE /draft/proposals/{id}/focus-documents/{document_id}
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.proposal import Proposal
from app.models.proposal_focus_document import ProposalFocusDocument
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestListFocusDocuments:
    """Tests for GET /api/v1/draft/proposals/{id}/focus-documents."""

    @pytest.mark.asyncio
    async def test_list_focus_documents_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/draft/proposals/999/focus-documents")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_focus_documents_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_focus_documents_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_document: KnowledgeBaseDocument,
        test_user: User,
        db_session: AsyncSession,
    ):
        fd = ProposalFocusDocument(
            proposal_id=test_proposal.id,
            document_id=test_document.id,
            priority_order=0,
        )
        db_session.add(fd)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_id"] == test_document.id
        assert data[0]["document_title"] == test_document.title

    @pytest.mark.asyncio
    async def test_list_focus_documents_not_found_proposal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        response = await client.get(
            "/api/v1/draft/proposals/99999/focus-documents",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_focus_documents_idor(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        db_session: AsyncSession,
    ):
        """Another user cannot list focus documents for a proposal they don't own."""
        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
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
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents",
            headers=headers,
        )
        assert response.status_code == 404


class TestSetFocusDocuments:
    """Tests for PUT /api/v1/draft/proposals/{id}/focus-documents."""

    @pytest.mark.asyncio
    async def test_set_focus_documents_requires_auth(self, client: AsyncClient):
        response = await client.put(
            "/api/v1/draft/proposals/999/focus-documents",
            json={"document_ids": [1]},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_set_focus_documents_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_document: KnowledgeBaseDocument,
        test_user: User,
    ):
        response = await client.put(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents",
            headers=auth_headers,
            json={"document_ids": [test_document.id]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_id"] == test_document.id
        assert data[0]["priority_order"] == 0

    @pytest.mark.asyncio
    async def test_set_focus_documents_replaces_existing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_document: KnowledgeBaseDocument,
        test_user: User,
        db_session: AsyncSession,
    ):
        # Create initial focus document
        fd = ProposalFocusDocument(
            proposal_id=test_proposal.id,
            document_id=test_document.id,
            priority_order=0,
        )
        db_session.add(fd)
        await db_session.commit()

        # Set empty list replaces
        response = await client.put(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents",
            headers=auth_headers,
            json={"document_ids": []},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_set_focus_documents_proposal_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        response = await client.put(
            "/api/v1/draft/proposals/99999/focus-documents",
            headers=auth_headers,
            json={"document_ids": [1]},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_set_focus_documents_skips_other_users_docs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Documents owned by a different user are silently skipped."""
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

        other_doc = KnowledgeBaseDocument(
            user_id=other.id,
            title="Other Doc",
            document_type="other",
            original_filename="other.pdf",
            file_path="/uploads/other.pdf",
            file_size_bytes=100,
            mime_type="application/pdf",
            processing_status="ready",
            is_ready=True,
        )
        db_session.add(other_doc)
        await db_session.commit()
        await db_session.refresh(other_doc)

        response = await client.put(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents",
            headers=auth_headers,
            json={"document_ids": [other_doc.id]},
        )
        assert response.status_code == 200
        assert response.json() == []


class TestRemoveFocusDocument:
    """Tests for DELETE /api/v1/draft/proposals/{id}/focus-documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_remove_focus_document_requires_auth(self, client: AsyncClient):
        response = await client.delete(
            "/api/v1/draft/proposals/1/focus-documents/1",
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_remove_focus_document_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_document: KnowledgeBaseDocument,
        test_user: User,
        db_session: AsyncSession,
    ):
        fd = ProposalFocusDocument(
            proposal_id=test_proposal.id,
            document_id=test_document.id,
            priority_order=0,
        )
        db_session.add(fd)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents/{test_document.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["document_id"] == test_document.id

    @pytest.mark.asyncio
    async def test_remove_focus_document_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_proposal: Proposal,
        test_user: User,
    ):
        response = await client.delete(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_focus_document_idor(
        self,
        client: AsyncClient,
        test_proposal: Proposal,
        test_document: KnowledgeBaseDocument,
        db_session: AsyncSession,
    ):
        fd = ProposalFocusDocument(
            proposal_id=test_proposal.id,
            document_id=test_document.id,
            priority_order=0,
        )
        db_session.add(fd)
        await db_session.commit()

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

        response = await client.delete(
            f"/api/v1/draft/proposals/{test_proposal.id}/focus-documents/{test_document.id}",
            headers=headers,
        )
        assert response.status_code == 404
