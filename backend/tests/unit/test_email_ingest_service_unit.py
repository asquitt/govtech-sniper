"""Unit tests for email_ingest_service."""

from email.message import EmailMessage
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email_ingest_service import EmailIngestService


@pytest.fixture
def service():
    return EmailIngestService(
        host="imap.test.com",
        port=993,
        username="user@test.com",
        password="secret",
        use_ssl=True,
    )


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_init_ssl():
    svc = EmailIngestService("host", 993, "user", "pass", use_ssl=True)
    assert svc.host == "host"
    assert svc.port == 993
    assert svc.use_ssl is True


def test_init_non_ssl():
    svc = EmailIngestService("host", 143, "user", "pass", use_ssl=False)
    assert svc.use_ssl is False


# ---------------------------------------------------------------------------
# _parse_email
# ---------------------------------------------------------------------------


def test_parse_simple_email(service):
    msg = EmailMessage()
    msg["Subject"] = "Test Subject"
    msg["From"] = "sender@example.com"
    msg["Date"] = "Mon, 24 Feb 2026 12:00:00 +0000"
    msg["Message-ID"] = "<test123@example.com>"
    msg.set_content("Plain text body")

    result = service._parse_email(msg)
    assert result is not None
    assert result["subject"] == "Test Subject"
    assert result["sender"] == "sender@example.com"
    assert "Plain text body" in result["body_text"]
    assert result["attachment_count"] == 0


def test_parse_email_missing_subject(service):
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["Message-ID"] = "<test456@example.com>"
    msg.set_content("Body")

    result = service._parse_email(msg)
    assert result is not None
    # Missing subject should not crash
    assert result["subject"] is None or result["subject"] == ""


def test_parse_email_with_html(service):
    msg = EmailMessage()
    msg["Subject"] = "HTML Email"
    msg["From"] = "sender@example.com"
    msg["Message-ID"] = "<html123@example.com>"
    msg.set_content("Plain text version")
    msg.add_alternative("<h1>HTML version</h1>", subtype="html")

    result = service._parse_email(msg)
    assert result is not None
    assert result["body_text"] is not None
    assert result["body_html"] is not None


def test_parse_email_with_attachment(service):
    msg = EmailMessage()
    msg["Subject"] = "With Attachment"
    msg["From"] = "sender@example.com"
    msg["Message-ID"] = "<attach123@example.com>"
    msg.set_content("Body text")
    msg.add_attachment(
        b"fake pdf content",
        maintype="application",
        subtype="pdf",
        filename="document.pdf",
    )

    result = service._parse_email(msg)
    assert result is not None
    assert result["attachment_count"] >= 1
    assert "document.pdf" in result["attachment_names"]


# ---------------------------------------------------------------------------
# _extract_attachment_text
# ---------------------------------------------------------------------------


def test_extract_text_attachment(service):
    result = service._extract_attachment_text(
        filename="readme.txt",
        content_type="text/plain",
        payload=b"Hello world from text file",
    )
    assert "Hello world" in result


def test_extract_unsupported_attachment(service):
    result = service._extract_attachment_text(
        filename="image.png",
        content_type="image/png",
        payload=b"\x89PNG...",
    )
    assert result == ""


@patch("app.services.email_ingest_service.EmailIngestService._extract_pdf_text")
def test_extract_pdf_attachment(mock_pdf, service):
    mock_pdf.return_value = "Extracted PDF text"
    result = service._extract_attachment_text(
        filename="report.pdf",
        content_type="application/pdf",
        payload=b"fake-pdf",
    )
    assert result == "Extracted PDF text"
    mock_pdf.assert_called_once_with(b"fake-pdf")


def test_extract_text_attachment_large(service):
    """Text attachments should be limited to ~40k chars."""
    large_text = "x" * 50000
    result = service._extract_attachment_text(
        filename="big.txt",
        content_type="text/plain",
        payload=large_text.encode(),
    )
    assert len(result) <= 41000  # 40k + some margin


# ---------------------------------------------------------------------------
# _extract_pdf_text
# ---------------------------------------------------------------------------


@patch("app.services.email_ingest_service.PdfReader")
def test_extract_pdf_text_success(mock_reader_cls, service):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page text"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page, mock_page, mock_page]
    mock_reader_cls.return_value = mock_reader

    result = service._extract_pdf_text(b"fake-pdf")
    assert "Page text" in result


@patch("app.services.email_ingest_service.PdfReader")
def test_extract_pdf_text_limits_to_3_pages(mock_reader_cls, service):
    pages = [MagicMock() for _ in range(10)]
    for p in pages:
        p.extract_text.return_value = "text"
    mock_reader = MagicMock()
    mock_reader.pages = pages
    mock_reader_cls.return_value = mock_reader

    service._extract_pdf_text(b"fake-pdf")
    # Should only extract first 3 pages
    assert pages[0].extract_text.called
    assert pages[3].extract_text.call_count == 0


@patch("app.services.email_ingest_service.PdfReader")
def test_extract_pdf_text_error(mock_reader_cls, service):
    mock_reader_cls.side_effect = Exception("Corrupt PDF")
    result = service._extract_pdf_text(b"bad-pdf")
    assert result == ""


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.email_ingest_service.asyncio")
async def test_test_connection_success(mock_asyncio, service):
    mock_asyncio.to_thread = AsyncMock(
        return_value={"status": "connected", "folders": ["INBOX", "Sent"]}
    )
    result = await service.test_connection()
    assert result["status"] == "connected"
    assert "folders" in result


@pytest.mark.asyncio
@patch("app.services.email_ingest_service.asyncio")
async def test_test_connection_auth_failure(mock_asyncio, service):
    mock_asyncio.to_thread = AsyncMock(
        return_value={"status": "auth_error", "message": "Invalid credentials"}
    )
    result = await service.test_connection()
    assert result["status"] == "auth_error"


# ---------------------------------------------------------------------------
# connect_and_fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.email_ingest_service.asyncio")
async def test_connect_and_fetch_returns_list(mock_asyncio, service):
    mock_asyncio.to_thread = AsyncMock(
        return_value=[
            {"subject": "Test 1", "sender": "a@b.com"},
            {"subject": "Test 2", "sender": "c@d.com"},
        ]
    )
    results = await service.connect_and_fetch(folder="INBOX", limit=10)
    assert isinstance(results, list)
    assert len(results) == 2


@pytest.mark.asyncio
@patch("app.services.email_ingest_service.asyncio")
async def test_connect_and_fetch_empty(mock_asyncio, service):
    mock_asyncio.to_thread = AsyncMock(return_value=[])
    results = await service.connect_and_fetch()
    assert results == []
