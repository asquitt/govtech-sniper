"""
RFP Sniper - Knowledge Base Document Tests
==========================================
Tests for document management in the knowledge base.
"""

import pytest
from httpx import AsyncClient

from app.models.knowledge_base import KnowledgeBaseDocument


class TestDocumentList:
    """Tests for document listing."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing documents when none exist."""
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_documents_with_data(
        self, client: AsyncClient, auth_headers: dict, test_document: KnowledgeBaseDocument
    ):
        """Test listing documents with existing data."""
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["documents"][0]["id"] == test_document.id

    @pytest.mark.asyncio
    async def test_list_documents_filter_by_type(
        self, client: AsyncClient, auth_headers: dict, test_document: KnowledgeBaseDocument
    ):
        """Test filtering documents by type."""
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
            params={"document_type": "capability_statement"},
        )
        assert response.status_code == 200
        assert len(response.json()["documents"]) == 1

        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
            params={"document_type": "past_performance"},
        )
        assert response.status_code == 200
        assert len(response.json()["documents"]) == 0


class TestDocumentDetail:
    """Tests for document detail retrieval."""

    @pytest.mark.asyncio
    async def test_get_document_success(
        self, client: AsyncClient, auth_headers: dict, test_document: KnowledgeBaseDocument
    ):
        """Test getting document details."""
        response = await client.get(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document.id
        assert data["title"] == test_document.title

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent document."""
        response = await client.get(
            "/api/v1/documents/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_document_unauthorized(
        self, client: AsyncClient, test_document: KnowledgeBaseDocument
    ):
        """Test getting document without auth."""
        response = await client.get(f"/api/v1/documents/{test_document.id}")
        assert response.status_code == 401


class TestDocumentUpdate:
    """Tests for document updates."""

    @pytest.mark.asyncio
    async def test_update_document_title(
        self, client: AsyncClient, auth_headers: dict, test_document: KnowledgeBaseDocument
    ):
        """Test updating document title."""
        response = await client.patch(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_document_type(
        self, client: AsyncClient, auth_headers: dict, test_document: KnowledgeBaseDocument
    ):
        """Test updating document type."""
        response = await client.patch(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"document_type": "past_performance"},
        )
        assert response.status_code == 200
        assert response.json()["document_type"] == "past_performance"


class TestDocumentDelete:
    """Tests for document deletion."""

    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, client: AsyncClient, auth_headers: dict, test_document: KnowledgeBaseDocument
    ):
        """Test deleting a document."""
        response = await client.delete(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify deletion
        response = await client.get(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test deleting non-existent document."""
        response = await client.delete(
            "/api/v1/documents/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDocumentStats:
    """Tests for document statistics."""

    @pytest.mark.asyncio
    async def test_get_document_stats(
        self, client: AsyncClient, auth_headers: dict, test_document: KnowledgeBaseDocument
    ):
        """Test getting document statistics."""
        response = await client.get(
            "/api/v1/documents/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "by_type" in data
        assert data["total_documents"] == 1
