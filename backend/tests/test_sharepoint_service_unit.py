"""Unit tests for SharePoint service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.sharepoint_service import SharePointService, create_sharepoint_service

VALID_CONFIG = {
    "tenant_id": "tenant-123",
    "client_id": "client-456",
    "client_secret": "secret-789",
    "site_id": "site-abc",
    "drive_id": "drive-xyz",
}


def _make_service() -> SharePointService:
    return SharePointService(**VALID_CONFIG)


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------
class TestCreateSharePointService:
    def test_creates_service_with_valid_config(self):
        svc = create_sharepoint_service(VALID_CONFIG)
        assert isinstance(svc, SharePointService)
        assert svc.tenant_id == "tenant-123"
        assert svc.drive_id == "drive-xyz"

    def test_raises_on_missing_tenant_id(self):
        config = {k: v for k, v in VALID_CONFIG.items() if k != "tenant_id"}
        with pytest.raises(ValueError, match="tenant_id"):
            create_sharepoint_service(config)

    def test_raises_on_missing_multiple_keys(self):
        config = {"tenant_id": "t"}
        with pytest.raises(ValueError, match="Missing SharePoint config keys"):
            create_sharepoint_service(config)

    def test_raises_on_empty_config(self):
        with pytest.raises(ValueError):
            create_sharepoint_service({})


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------
class TestGetToken:
    @pytest.mark.asyncio
    async def test_fetches_token_from_azure(self):
        svc = _make_service()
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "tok-abc"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.sharepoint_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            token = await svc._get_token()
            assert token == "tok-abc"

    @pytest.mark.asyncio
    async def test_caches_token(self):
        svc = _make_service()
        svc._token = "cached-token"
        token = await svc._get_token()
        assert token == "cached-token"


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------
class TestHeaders:
    def test_headers_include_bearer_token(self):
        svc = _make_service()
        headers = svc._headers("my-token")
        assert headers["Authorization"] == "Bearer my-token"
        assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# List files
# ---------------------------------------------------------------------------
class TestListFiles:
    @pytest.mark.asyncio
    async def test_list_files_root(self):
        svc = _make_service()
        svc._token = "tok"

        items = [
            {
                "id": "f1",
                "name": "doc.pdf",
                "size": 1024,
                "lastModifiedDateTime": "2025-01-01T00:00:00Z",
                "webUrl": "https://sp.example.com/doc.pdf",
            },
            {
                "id": "d1",
                "name": "Reports",
                "folder": {},
                "size": 0,
            },
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": items}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.sharepoint_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.list_files("/")
            assert len(result) == 2
            assert result[0]["name"] == "doc.pdf"
            assert result[0]["is_folder"] is False
            assert result[1]["is_folder"] is True

    @pytest.mark.asyncio
    async def test_list_files_subfolder(self):
        svc = _make_service()
        svc._token = "tok"

        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.sharepoint_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.list_files("subfolder/path")
            assert result == []
            # Verify the URL construction
            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "root:/subfolder/path:/children" in url


# ---------------------------------------------------------------------------
# Download file
# ---------------------------------------------------------------------------
class TestDownloadFile:
    @pytest.mark.asyncio
    async def test_download_returns_bytes(self):
        svc = _make_service()
        svc._token = "tok"

        mock_response = MagicMock()
        mock_response.content = b"file-content-here"
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.sharepoint_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            content = await svc.download_file("file-id-123")
            assert content == b"file-content-here"


# ---------------------------------------------------------------------------
# Upload file
# ---------------------------------------------------------------------------
class TestUploadFile:
    @pytest.mark.asyncio
    async def test_upload_returns_metadata(self):
        svc = _make_service()
        svc._token = "tok"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "new-id",
            "name": "upload.docx",
            "webUrl": "https://sp.example.com/upload.docx",
            "size": 2048,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.sharepoint_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.put.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.upload_file("/proposals", "upload.docx", b"data")
            assert result["id"] == "new-id"
            assert result["name"] == "upload.docx"
            assert result["size"] == 2048


# ---------------------------------------------------------------------------
# Get file versions
# ---------------------------------------------------------------------------
class TestGetFileVersions:
    @pytest.mark.asyncio
    async def test_returns_version_list(self):
        svc = _make_service()
        svc._token = "tok"

        versions = [
            {
                "id": "1.0",
                "lastModifiedDateTime": "2025-01-01T00:00:00Z",
                "size": 1024,
                "lastModifiedBy": {"user": {"displayName": "John"}},
            },
            {
                "id": "2.0",
                "size": 2048,
            },
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": versions}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.sharepoint_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.get_file_versions("file-id")
            assert len(result) == 2
            assert result[0]["id"] == "1.0"
            assert result[0]["modified_by"] == "John"
            assert result[1]["modified_by"] is None


# ---------------------------------------------------------------------------
# Create subscription
# ---------------------------------------------------------------------------
class TestCreateSubscription:
    @pytest.mark.asyncio
    async def test_creates_webhook_subscription(self):
        svc = _make_service()
        svc._token = "tok"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "sub-123",
            "expirationDateTime": "2025-02-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.sharepoint_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.create_subscription(
                resource="/drives/drv/root",
                notification_url="https://example.com/webhook",
                expiration="2025-02-01T00:00:00Z",
            )
            assert result["id"] == "sub-123"
