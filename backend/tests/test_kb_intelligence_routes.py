"""
Integration tests for kb_intelligence.py — /api/v1/kb-intelligence/
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestContentFreshness:
    """Tests for GET /api/v1/kb-intelligence/freshness."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/kb-intelligence/freshness")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_freshness_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/kb-intelligence/freshness", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 0
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_freshness_with_document(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.get("/api/v1/kb-intelligence/freshness", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] >= 1
        assert len(data["documents"]) >= 1

    @pytest.mark.asyncio
    async def test_freshness_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_document: KnowledgeBaseDocument,
    ):
        """User B should not see User A's documents."""
        user_b = User(
            email="other@example.com",
            hashed_password=hash_password("Pwd123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user_b)
        await db_session.commit()
        await db_session.refresh(user_b)
        tokens = create_token_pair(user_b.id, user_b.email, user_b.tier)
        headers_b = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/kb-intelligence/freshness", headers=headers_b)
        assert response.status_code == 200
        assert response.json()["total_documents"] == 0


class TestGapAnalysis:
    """Tests for GET /api/v1/kb-intelligence/gap-analysis."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/kb-intelligence/gap-analysis")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_gap_analysis_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/kb-intelligence/gap-analysis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "type_coverage" in data
        assert "type_gaps" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_gap_analysis_with_document(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.get("/api/v1/kb-intelligence/gap-analysis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have at least capability_statement count
        assert data["type_coverage"]["capability_statement"] >= 1


class TestAutoTag:
    """Tests for POST /api/v1/kb-intelligence/{document_id}/auto-tag."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/kb-intelligence/1/auto-tag")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_auto_tag_document(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.post(
            f"/api/v1/kb-intelligence/{test_document.id}/auto-tag",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_document.id
        assert isinstance(data["tags"], list)
        # Should at least have the type tag
        assert any("type:" in t for t in data["tags"])

    @pytest.mark.asyncio
    async def test_auto_tag_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/v1/kb-intelligence/99999/auto-tag", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_auto_tag_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_document: KnowledgeBaseDocument,
    ):
        """User B cannot auto-tag User A's document."""
        user_b = User(
            email="other@example.com",
            hashed_password=hash_password("Pwd123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user_b)
        await db_session.commit()
        await db_session.refresh(user_b)
        tokens = create_token_pair(user_b.id, user_b.email, user_b.tier)
        headers_b = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(
            f"/api/v1/kb-intelligence/{test_document.id}/auto-tag",
            headers=headers_b,
        )
        assert response.status_code == 404


class TestDuplicateDetection:
    """Tests for GET /api/v1/kb-intelligence/duplicates."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/kb-intelligence/duplicates")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_duplicates_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/kb-intelligence/duplicates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_potential_duplicates"] == 0
        assert data["duplicate_groups"] == []

    @pytest.mark.asyncio
    async def test_duplicates_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Two documents with the same normalized title should flag as duplicates."""
        doc1 = KnowledgeBaseDocument(
            user_id=test_user.id,
            title="Capability Statement",
            document_type="capability_statement",
            original_filename="cap1.pdf",
            file_path="/uploads/cap1.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status="ready",
            is_ready=True,
        )
        doc2 = KnowledgeBaseDocument(
            user_id=test_user.id,
            title="Capability Statement (1)",
            document_type="capability_statement",
            original_filename="cap2.pdf",
            file_path="/uploads/cap2.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status="ready",
            is_ready=True,
        )
        db_session.add(doc1)
        db_session.add(doc2)
        await db_session.commit()

        response = await client.get("/api/v1/kb-intelligence/duplicates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_potential_duplicates"] >= 2
