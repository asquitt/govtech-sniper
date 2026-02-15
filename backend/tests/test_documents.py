"""
RFP Sniper - Knowledge Base Document Tests
==========================================
Tests for document management in the knowledge base.
"""

import pytest
from httpx import AsyncClient

from app.config import settings
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
        assert data["documents"][0]["classification"] == "internal"

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


class TestDocumentUpload:
    """Tests for document upload behavior."""

    @pytest.mark.asyncio
    async def test_upload_text_document_processes_inline_with_sync_fallback(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        monkeypatch,
    ):
        from app.api.routes import documents as document_routes

        monkeypatch.setattr(
            document_routes, "_should_process_documents_synchronously", lambda: True
        )

        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("inline.txt", b"Inline processing text", "text/plain")},
            data={
                "title": "Inline Processing Upload",
                "document_type": "other",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["processing_status"] == "ready"

        uploaded = await db_session.get(KnowledgeBaseDocument, payload["id"])
        assert uploaded is not None
        status_value = (
            uploaded.processing_status.value
            if hasattr(uploaded.processing_status, "value")
            else uploaded.processing_status
        )
        assert status_value == "ready"
        assert uploaded.full_text == "Inline processing text"

    @pytest.mark.asyncio
    async def test_upload_document_falls_back_when_upload_dir_is_read_only(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        monkeypatch,
        tmp_path,
    ):
        read_only_root = tmp_path / "readonly_upload_root"
        read_only_root.mkdir()
        read_only_root.chmod(0o555)

        original_upload_dir = settings.upload_dir
        monkeypatch.setattr(settings, "upload_dir", str(read_only_root))

        try:
            response = await client.post(
                "/api/v1/documents",
                headers=auth_headers,
                files={"file": ("upload.txt", b"Capability statement", "text/plain")},
                data={
                    "title": "Read-Only Upload",
                    "document_type": "capability_statement",
                },
            )
        finally:
            # Restore write permissions for tmp cleanup.
            read_only_root.chmod(0o755)
            monkeypatch.setattr(settings, "upload_dir", original_upload_dir)

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] > 0

        uploaded = await db_session.get(KnowledgeBaseDocument, payload["id"])
        assert uploaded is not None
        assert "/rfp-sniper-uploads/" in uploaded.file_path.replace("\\", "/")


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
        assert data["classification"] == "internal"

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
            json={"document_type": "past_performance", "classification": "fci"},
        )
        assert response.status_code == 200
        assert response.json()["document_type"] == "past_performance"
        assert response.json()["classification"] == "fci"


class TestDocumentDelete:
    """Tests for document deletion."""

    @pytest.mark.asyncio
    async def test_delete_document_with_chunks_created_by_inline_processing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        from app.api.routes import documents as document_routes

        monkeypatch.setattr(
            document_routes, "_should_process_documents_synchronously", lambda: True
        )

        upload_response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            files={"file": ("delete-inline.txt", b"Delete inline chunk", "text/plain")},
            data={
                "title": "Delete Inline Document",
                "document_type": "other",
            },
        )
        assert upload_response.status_code == 200
        uploaded = upload_response.json()
        assert uploaded["processing_status"] == "ready"

        delete_response = await client.delete(
            f"/api/v1/documents/{uploaded['id']}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200

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
