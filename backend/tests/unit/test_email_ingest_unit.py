"""
Email Ingest Service Unit Tests
=================================
Tests for EmailIngestService parsing logic — body extraction, attachment
detection, and RFC parsing. All IMAP and PDF calls are mocked.
"""

import email
from email.message import Message
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_ingest_service import EmailIngestService

# =============================================================================
# Helpers
# =============================================================================


def make_service() -> EmailIngestService:
    return EmailIngestService(
        host="imap.example.com",
        port=993,
        username="test@example.com",
        password="secret",
        use_ssl=True,
    )


def make_simple_text_message(subject: str, body: str, sender: str = "sender@gov.mil") -> Message:
    """Create a plain-text non-multipart email."""
    msg = Message()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["Date"] = "Mon, 01 Jan 2025 12:00:00 +0000"
    msg["Message-ID"] = "<test-id@example.com>"
    msg.set_payload(body.encode("utf-8"), charset="utf-8")
    msg.set_type("text/plain")
    return msg


def make_multipart_message(
    subject: str,
    body_text: str = "",
    body_html: str = "",
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> Message:
    """Build a multipart email with optional attachments."""
    msg = email.message.MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = "rfp@agency.gov"
    msg["Date"] = "Mon, 01 Jan 2025 12:00:00 +0000"
    msg["Message-ID"] = "<multi@example.com>"

    if body_text:
        part = email.mime.text.MIMEText(body_text, "plain")
        msg.attach(part)
    if body_html:
        part = email.mime.text.MIMEText(body_html, "html")
        msg.attach(part)

    for filename, payload, content_type in attachments or []:
        att = email.mime.base.MIMEBase(*content_type.split("/", 1))
        att.set_payload(payload)
        att["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(att)

    return msg


# Need these imports for make_multipart_message
import email.mime.application
import email.mime.base
import email.mime.multipart
import email.mime.text

# Patch Message to use MIMEMultipart
email.message.MIMEMultipart = email.mime.multipart.MIMEMultipart


# =============================================================================
# _parse_email — basic fields
# =============================================================================


class TestParseEmailBasicFields:
    def test_subject_extracted(self):
        msg = make_simple_text_message("RFP-2025-001 Solicitation", "body text")
        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert result["subject"] == "RFP-2025-001 Solicitation"

    def test_sender_extracted(self):
        msg = make_simple_text_message("Subject", "body", sender="contracting@dod.mil")
        result = EmailIngestService._parse_email(msg)
        assert result["sender"] == "contracting@dod.mil"

    def test_date_extracted(self):
        msg = make_simple_text_message("Subject", "body")
        result = EmailIngestService._parse_email(msg)
        assert result["date"] == "Mon, 01 Jan 2025 12:00:00 +0000"

    def test_message_id_stripped(self):
        msg = make_simple_text_message("Subject", "body")
        result = EmailIngestService._parse_email(msg)
        assert result["message_id"] == "<test-id@example.com>"

    def test_result_is_dict(self):
        msg = make_simple_text_message("Subj", "Body")
        result = EmailIngestService._parse_email(msg)
        assert isinstance(result, dict)


# =============================================================================
# _parse_email — body extraction
# =============================================================================


class TestParseEmailBodyExtraction:
    def test_plain_text_body_extracted_for_simple_message(self):
        msg = make_simple_text_message("Subject", "Plain text body here.")
        result = EmailIngestService._parse_email(msg)
        assert "Plain text body here." in result["body_text"]

    def test_body_html_empty_for_plain_message(self):
        msg = make_simple_text_message("Subject", "body")
        result = EmailIngestService._parse_email(msg)
        assert result["body_html"] == ""

    def test_multipart_plain_text_extracted(self):
        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg["Subject"] = "Test"
        msg["From"] = "a@b.com"
        msg["Date"] = "Mon, 01 Jan 2025 12:00:00 +0000"
        msg["Message-ID"] = "<id>"
        txt = email.mime.text.MIMEText("Hello from multipart.", "plain")
        msg.attach(txt)

        result = EmailIngestService._parse_email(msg)
        assert "Hello from multipart." in result["body_text"]

    def test_multipart_html_extracted(self):
        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg["Subject"] = "HTML Test"
        msg["From"] = "a@b.com"
        msg["Date"] = "Mon, 01 Jan 2025 12:00:00 +0000"
        msg["Message-ID"] = "<id2>"
        html = email.mime.text.MIMEText("<p>Hello</p>", "html")
        msg.attach(html)

        result = EmailIngestService._parse_email(msg)
        assert "<p>Hello</p>" in result["body_html"]


# =============================================================================
# _parse_email — attachment detection
# =============================================================================


class TestParseEmailAttachments:
    def test_no_attachments_returns_empty_list(self):
        msg = make_simple_text_message("Subject", "body")
        result = EmailIngestService._parse_email(msg)
        assert result["attachments"] == []
        assert result["attachment_count"] == 0

    def test_attachment_count_correct(self):
        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg["Subject"] = "With Attachment"
        msg["From"] = "a@b.com"
        msg["Date"] = "Mon, 01 Jan 2025 12:00:00 +0000"
        msg["Message-ID"] = "<id3>"

        att = email.mime.base.MIMEBase("application", "octet-stream")
        att.set_payload(b"binary data")
        att["Content-Disposition"] = 'attachment; filename="doc.bin"'
        msg.attach(att)

        result = EmailIngestService._parse_email(msg)
        assert result["attachment_count"] == 1

    def test_attachment_filename_captured(self):
        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg["Subject"] = "Subj"
        msg["From"] = "a@b.com"
        msg["Date"] = "Mon, 01 Jan 2025 12:00:00 +0000"
        msg["Message-ID"] = "<id4>"

        att = email.mime.base.MIMEBase("application", "pdf")
        att.set_payload(b"pdf bytes")
        att["Content-Disposition"] = 'attachment; filename="RFP.pdf"'
        msg.attach(att)

        result = EmailIngestService._parse_email(msg)
        assert "RFP.pdf" in result["attachment_names"]

    def test_attachment_size_captured(self):
        payload = b"x" * 100
        msg = email.mime.multipart.MIMEMultipart("mixed")
        msg["Subject"] = "Subj"
        msg["From"] = "a@b.com"
        msg["Date"] = "Mon, 01 Jan 2025 12:00:00 +0000"
        msg["Message-ID"] = "<id5>"

        att = email.mime.base.MIMEBase("application", "pdf")
        att.set_payload(payload)
        att["Content-Disposition"] = 'attachment; filename="file.pdf"'
        msg.attach(att)

        result = EmailIngestService._parse_email(msg)
        assert result["attachments"][0]["size"] == 100


# =============================================================================
# _extract_attachment_text
# =============================================================================


class TestExtractAttachmentText:
    def test_text_file_decoded_as_utf8(self):
        text = "Solicitation details for NAICS 541512."
        result = EmailIngestService._extract_attachment_text(
            filename="details.txt",
            content_type="text/plain",
            payload=text.encode("utf-8"),
        )
        assert result == text

    def test_text_extraction_truncated_at_40000(self):
        long_text = "x" * 50000
        result = EmailIngestService._extract_attachment_text(
            filename="long.txt",
            content_type="text/plain",
            payload=long_text.encode("utf-8"),
        )
        assert len(result) <= 40000

    def test_csv_extracted_as_text(self):
        csv_data = "col1,col2\nval1,val2\n"
        result = EmailIngestService._extract_attachment_text(
            filename="data.csv",
            content_type="text/csv",
            payload=csv_data.encode("utf-8"),
        )
        assert "col1" in result

    def test_unknown_binary_returns_empty_string(self):
        result = EmailIngestService._extract_attachment_text(
            filename="archive.zip",
            content_type="application/zip",
            payload=b"PK\x03\x04",
        )
        assert result == ""

    def test_pdf_extraction_uses_pypdf(self):
        with patch("app.services.email_ingest_service.PdfReader") as mock_reader_cls:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF page content"
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_reader_cls.return_value = mock_reader

            result = EmailIngestService._extract_attachment_text(
                filename="rfp.pdf",
                content_type="application/pdf",
                payload=b"fake-pdf-bytes",
            )

        assert "PDF page content" in result

    def test_pdf_extraction_returns_empty_on_error(self):
        with patch("app.services.email_ingest_service.PdfReader", side_effect=Exception("bad")):
            result = EmailIngestService._extract_attachment_text(
                filename="broken.pdf",
                content_type="application/pdf",
                payload=b"garbage",
            )
        assert result == ""

    def test_pdf_detected_by_extension(self):
        with patch("app.services.email_ingest_service.PdfReader") as mock_reader_cls:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Content from ext-based pdf"
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_reader_cls.return_value = mock_reader

            # content_type is generic but filename ends in .pdf
            result = EmailIngestService._extract_attachment_text(
                filename="solicitation.pdf",
                content_type="application/octet-stream",
                payload=b"fake",
            )

        assert "Content from ext-based pdf" in result


# =============================================================================
# _extract_pdf_text
# =============================================================================


class TestExtractPdfText:
    def test_extracts_up_to_first_3_pages(self):
        with patch("app.services.email_ingest_service.PdfReader") as mock_cls:
            pages = []
            for i in range(5):
                p = MagicMock()
                p.extract_text.return_value = f"page {i}"
                pages.append(p)
            mock_reader = MagicMock()
            mock_reader.pages = pages
            mock_cls.return_value = mock_reader

            result = EmailIngestService._extract_pdf_text(b"fake")

        assert "page 0" in result
        assert "page 1" in result
        assert "page 2" in result
        assert "page 3" not in result

    def test_returns_empty_string_on_exception(self):
        with patch(
            "app.services.email_ingest_service.PdfReader", side_effect=Exception("parse error")
        ):
            result = EmailIngestService._extract_pdf_text(b"garbage")
        assert result == ""

    def test_skips_none_page_text(self):
        with patch("app.services.email_ingest_service.PdfReader") as mock_cls:
            p1 = MagicMock()
            p1.extract_text.return_value = None
            p2 = MagicMock()
            p2.extract_text.return_value = "real text"
            mock_reader = MagicMock()
            mock_reader.pages = [p1, p2]
            mock_cls.return_value = mock_reader

            result = EmailIngestService._extract_pdf_text(b"fake")
        assert "real text" in result


# =============================================================================
# _fetch_sync — IMAP interaction
# =============================================================================


class TestFetchSync:
    def test_returns_empty_list_when_no_unseen(self):
        svc = make_service()
        mock_conn = MagicMock()
        mock_conn.search.return_value = (None, [b""])
        mock_conn.select.return_value = (None, None)

        with patch("app.services.email_ingest_service.imaplib.IMAP4_SSL", return_value=mock_conn):
            result = svc._fetch_sync("INBOX", 50)

        assert result == []

    def test_returns_empty_list_on_imap_error(self):
        svc = make_service()
        with patch(
            "app.services.email_ingest_service.imaplib.IMAP4_SSL",
            side_effect=Exception("conn failed"),
        ):
            result = svc._fetch_sync("INBOX", 50)
        assert result == []

    def test_respects_limit(self):
        svc = make_service()
        mock_conn = MagicMock()
        # 10 unseen messages, limit=3
        msg_ids = b" ".join(str(i).encode() for i in range(1, 11))
        mock_conn.search.return_value = (None, [msg_ids])
        mock_conn.select.return_value = (None, None)
        mock_conn.fetch.return_value = (None, None)

        with patch("app.services.email_ingest_service.imaplib.IMAP4_SSL", return_value=mock_conn):
            svc._fetch_sync("INBOX", 3)

        # fetch called 3 times (once per limited id)
        assert mock_conn.fetch.call_count == 3


# =============================================================================
# test_connection
# =============================================================================


class TestTestConnection:
    @pytest.mark.asyncio
    async def test_returns_connected_on_success(self):
        svc = make_service()
        mock_conn = MagicMock()
        mock_conn.list.return_value = (None, [b"INBOX", b"Sent"])

        with patch("app.services.email_ingest_service.imaplib.IMAP4_SSL", return_value=mock_conn):
            result = await svc.test_connection()

        assert result["status"] == "connected"

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_login_failure(self):
        svc = make_service()
        import imaplib

        mock_conn = MagicMock()
        mock_conn.login.side_effect = imaplib.IMAP4.error("LOGIN failed")

        with patch("app.services.email_ingest_service.imaplib.IMAP4_SSL", return_value=mock_conn):
            result = await svc.test_connection()

        assert result["status"] == "auth_error"
