"""
Tests for document routes - Knowledge Base CRUD and past performance.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import DocumentType, KnowledgeBaseDocument, ProcessingStatus
from app.models.user import User
from app.services.auth_service import create_token_pair


@pytest_asyncio.fixture
async def test_document(db_session: AsyncSession, test_user: User) -> KnowledgeBaseDocument:
    doc = KnowledgeBaseDocument(
        user_id=test_user.id,
        title="Test Document",
        document_type=DocumentType.PAST_PERFORMANCE,
        original_filename="test.txt",
        file_path="/tmp/test.txt",
        file_size_bytes=100,
        mime_type="text/plain",
        processing_status=ProcessingStatus.READY,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


class TestListDocuments:
    """Tests for GET /api/v1/documents."""

    @pytest.mark.asyncio
    async def test_list_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/documents")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["documents"] == []

    @pytest.mark.asyncio
    async def test_list_returns_owned(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["documents"][0]["title"] == "Test Document"

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_document: KnowledgeBaseDocument,
    ):
        other = User(
            email="doc_idor@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_filter_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
            params={"document_type": "past_performance"},
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1


class TestGetDocument:
    """Tests for GET /api/v1/documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_get_unauthenticated(
        self, client: AsyncClient, test_document: KnowledgeBaseDocument
    ):
        response = await client.get(f"/api/v1/documents/{test_document.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Test Document"

    @pytest.mark.asyncio
    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/documents/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_document: KnowledgeBaseDocument,
    ):
        other = User(
            email="doc_get_idor@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=headers)
        assert response.status_code == 404


class TestUploadDocument:
    """Tests for POST /api/v1/documents."""

    @pytest.mark.asyncio
    async def test_upload_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/documents",
            data={"title": "Uploaded"},
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            data={"title": "Uploaded Doc"},
            files={"file": ("test.txt", b"hello world content", "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Uploaded Doc"
        assert data["original_filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_upload_unsupported_type(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            data={"title": "Bad File"},
            files={"file": ("test.exe", b"binary", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]


class TestUpdateDocument:
    """Tests for PATCH /api/v1/documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_update_unauthenticated(
        self, client: AsyncClient, test_document: KnowledgeBaseDocument
    ):
        response = await client.patch(
            f"/api/v1/documents/{test_document.id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.patch(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/documents/99999",
            headers=auth_headers,
            json={"title": "Updated"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_document: KnowledgeBaseDocument,
    ):
        other = User(
            email="doc_up_idor@example.com",
            hashed_password="hashed",
            full_name="Other",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"/api/v1/documents/{test_document.id}",
            headers=headers,
            json={"title": "Hacked"},
        )
        assert response.status_code == 404


class TestDeleteDocument:
    """Tests for DELETE /api/v1/documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_delete_unauthenticated(
        self, client: AsyncClient, test_document: KnowledgeBaseDocument
    ):
        response = await client.delete(f"/api/v1/documents/{test_document.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_document: KnowledgeBaseDocument,
    ):
        response = await client.delete(
            f"/api/v1/documents/{test_document.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/documents/99999", headers=auth_headers)
        assert response.status_code == 404


class TestDocumentTypes:
    """Tests for GET /api/v1/documents/types/list."""

    @pytest.mark.asyncio
    async def test_list_types(self, client: AsyncClient):
        response = await client.get("/api/v1/documents/types/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "value" in data[0]
        assert "label" in data[0]


class TestDocumentStats:
    """Tests for GET /api/v1/documents/stats."""

    @pytest.mark.asyncio
    async def test_stats_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/documents/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/documents/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "by_type" in data


class TestPastPerformances:
    """Tests for past performance endpoints."""

    @pytest.mark.asyncio
    async def test_list_past_performances_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/documents/past-performances/list")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_past_performances_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/documents/past-performances/list", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
