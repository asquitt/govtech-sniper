"""
Email Ingest Service Unit Tests
================================
Tests for static/pure methods: _parse_email, _extract_attachment_text, _extract_pdf_text.
"""

from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

from app.services.email_ingest_service import EmailIngestService

# ---------------------------------------------------------------------------
# _parse_email (static)
# ---------------------------------------------------------------------------


class TestParseEmail:
    def test_simple_text_email(self):
        msg = Message()
        msg["Message-ID"] = "<test@example.com>"
        msg["Subject"] = "RFP for IT Services"
        msg["From"] = "sender@agency.gov"
        msg["Date"] = "Mon, 01 Jan 2025 10:00:00 +0000"
        msg.set_payload(b"This is the body text", charset="utf-8")

        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert result["message_id"] == "<test@example.com>"
        assert result["subject"] == "RFP for IT Services"
        assert result["sender"] == "sender@agency.gov"
        assert "body text" in result["body_text"]
        assert result["attachment_count"] == 0

    def test_multipart_email_with_text_and_html(self):
        msg = MIMEMultipart()
        msg["Message-ID"] = "<multi@example.com>"
        msg["Subject"] = "Multi-part test"
        msg["From"] = "sender@example.com"
        msg["Date"] = "Tue, 02 Jan 2025 12:00:00 +0000"

        text_part = MIMEText("Plain text body", "plain")
        html_part = MIMEText("<p>HTML body</p>", "html")
        msg.attach(text_part)
        msg.attach(html_part)

        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert "Plain text body" in result["body_text"]
        assert "<p>HTML body</p>" in result["body_html"]
        assert result["attachment_count"] == 0

    def test_multipart_email_with_attachment(self):
        msg = MIMEMultipart()
        msg["Message-ID"] = "<attach@example.com>"
        msg["Subject"] = "With attachment"
        msg["From"] = "sender@example.com"

        text_part = MIMEText("Body", "plain")
        msg.attach(text_part)

        # Simulate a text attachment
        attachment = MIMEText("Attachment content", "plain")
        attachment.add_header("Content-Disposition", "attachment", filename="doc.txt")
        msg.attach(attachment)

        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert result["attachment_count"] == 1
        assert result["attachment_names"] == ["doc.txt"]
        assert "Attachment content" in result["attachment_text"]

    def test_missing_headers(self):
        msg = Message()
        msg.set_payload(b"body", charset="utf-8")
        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert result["message_id"] == ""
        assert result["subject"] == ""
        assert result["sender"] == ""


# ---------------------------------------------------------------------------
# _extract_attachment_text (static)
# ---------------------------------------------------------------------------


class TestExtractAttachmentText:
    def test_text_file(self):
        result = EmailIngestService._extract_attachment_text(
            filename="readme.txt",
            content_type="text/plain",
            payload=b"Hello world",
        )
        assert result == "Hello world"

    def test_csv_file(self):
        result = EmailIngestService._extract_attachment_text(
            filename="data.csv",
            content_type="text/csv",
            payload=b"col1,col2\nval1,val2",
        )
        assert "col1" in result

    def test_markdown_file_by_extension(self):
        result = EmailIngestService._extract_attachment_text(
            filename="notes.md",
            content_type="application/octet-stream",
            payload=b"# Heading\nContent",
        )
        assert "Heading" in result

    def test_pdf_file_calls_extract(self):
        with patch.object(
            EmailIngestService, "_extract_pdf_text", return_value="PDF text"
        ) as mock_pdf:
            result = EmailIngestService._extract_attachment_text(
                filename="doc.pdf",
                content_type="application/pdf",
                payload=b"fake-pdf-bytes",
            )
            assert result == "PDF text"
            mock_pdf.assert_called_once_with(b"fake-pdf-bytes")

    def test_unknown_type_returns_empty(self):
        result = EmailIngestService._extract_attachment_text(
            filename="image.png",
            content_type="image/png",
            payload=b"\x89PNG...",
        )
        assert result == ""

    def test_text_truncated_to_40k(self):
        long_text = b"x" * 50000
        result = EmailIngestService._extract_attachment_text(
            filename="big.txt",
            content_type="text/plain",
            payload=long_text,
        )
        assert len(result) <= 40000


# ---------------------------------------------------------------------------
# _extract_pdf_text (static)
# ---------------------------------------------------------------------------


class TestExtractPdfText:
    def test_success(self):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 text"

        with patch("app.services.email_ingest_service.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_reader_cls.return_value = mock_reader

            result = EmailIngestService._extract_pdf_text(b"fake-pdf")
            assert result == "Page 1 text"

    def test_multiple_pages_limited_to_3(self):
        pages = []
        for i in range(5):
            p = MagicMock()
            p.extract_text.return_value = f"Page {i}"
            pages.append(p)

        with patch("app.services.email_ingest_service.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.pages = pages
            mock_reader_cls.return_value = mock_reader

            result = EmailIngestService._extract_pdf_text(b"fake-pdf")
            assert "Page 0" in result
            assert "Page 2" in result
            # Only first 3 pages
            assert "Page 3" not in result

    def test_invalid_pdf_returns_empty(self):
        with patch("app.services.email_ingest_service.PdfReader", side_effect=Exception("bad pdf")):
            result = EmailIngestService._extract_pdf_text(b"not-a-pdf")
            assert result == ""

    def test_page_with_no_text(self):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None

        with patch("app.services.email_ingest_service.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_reader_cls.return_value = mock_reader

            result = EmailIngestService._extract_pdf_text(b"fake-pdf")
            assert result == ""


# ---------------------------------------------------------------------------
# Constructor + init
# ---------------------------------------------------------------------------


class TestEmailIngestServiceInit:
    def test_constructor(self):
        svc = EmailIngestService(
            host="imap.example.com",
            port=993,
            username="user@example.com",
            password="secret",
        )
        assert svc.host == "imap.example.com"
        assert svc.port == 993
        assert svc.use_ssl is True

    def test_constructor_no_ssl(self):
        svc = EmailIngestService(
            host="imap.example.com",
            port=143,
            username="user@example.com",
            password="secret",
            use_ssl=False,
        )
        assert svc.use_ssl is False
