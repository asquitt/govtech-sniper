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


class TestPastPerformanceFlows:
    """Tests for past performance tagging, matching, and narrative generation."""

    @pytest.mark.asyncio
    async def test_past_performance_metadata_match_and_narrative(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        # Create an RFP target for matching.
        create_rfp = await client.post(
            "/api/v1/rfps",
            headers=auth_headers,
            json={
                "title": "Cybersecurity Modernization Support",
                "solicitation_number": "PP-001",
                "agency": "Department of Defense",
                "naics_code": "541512",
                "estimated_value": 1000000,
                "description": "Support cloud cybersecurity modernization and compliance operations.",
            },
        )
        assert create_rfp.status_code == 200
        rfp_id = create_rfp.json()["id"]

        # Convert the document into a past-performance record.
        to_past_performance = await client.patch(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"document_type": "past_performance"},
        )
        assert to_past_performance.status_code == 200

        metadata = await client.post(
            f"/api/v1/documents/{test_document.id}/past-performance-metadata",
            headers=auth_headers,
            json={
                "contract_number": "W91-TEST-42",
                "performing_agency": "Department of Defense",
                "contract_value": 1200000,
                "naics_code": "541512",
                "relevance_tags": ["cybersecurity", "cloud"],
            },
        )
        assert metadata.status_code == 200
        assert metadata.json()["contract_number"] == "W91-TEST-42"

        list_past_performance = await client.get(
            "/api/v1/documents/past-performances/list",
            headers=auth_headers,
        )
        assert list_past_performance.status_code == 200
        assert list_past_performance.json()["total"] == 1

        match = await client.post(
            f"/api/v1/documents/past-performances/match/{rfp_id}",
            headers=auth_headers,
        )
        assert match.status_code == 200
        assert match.json()["total"] >= 1

        narrative = await client.post(
            f"/api/v1/documents/past-performances/{test_document.id}/narrative/{rfp_id}",
            headers=auth_headers,
        )
        assert narrative.status_code == 200
        assert "Past Performance" in narrative.json()["narrative"]
