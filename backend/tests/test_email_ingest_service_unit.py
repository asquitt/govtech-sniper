"""Unit tests for EmailIngestService."""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.email_ingest_service import EmailIngestService


class TestParseEmail:
    def test_simple_plain_text(self):
        msg = email.message_from_string(
            "From: sender@example.com\r\n"
            "Subject: Test RFP\r\n"
            "Message-ID: <abc123>\r\n"
            "Date: Mon, 1 Jan 2025 12:00:00 +0000\r\n"
            "\r\n"
            "This is the body text."
        )
        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert result["subject"] == "Test RFP"
        assert result["sender"] == "sender@example.com"
        assert result["message_id"] == "<abc123>"
        assert "body text" in result["body_text"]
        assert result["attachment_count"] == 0

    def test_multipart_with_text_and_html(self):
        msg = MIMEMultipart("alternative")
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Multipart Test"
        msg["Message-ID"] = "<multi123>"
        msg.attach(MIMEText("Plain text body", "plain"))
        msg.attach(MIMEText("<html><body>HTML body</body></html>", "html"))

        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert "Plain text body" in result["body_text"]
        assert "HTML body" in result["body_html"]
        assert result["attachment_count"] == 0

    def test_multipart_with_attachment(self):
        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "With Attachment"
        msg["Message-ID"] = "<attach123>"
        msg.attach(MIMEText("Body text", "plain"))

        attachment = MIMEText("attachment content", "plain")
        attachment.add_header("Content-Disposition", "attachment", filename="doc.txt")
        msg.attach(attachment)

        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert result["attachment_count"] == 1
        assert result["attachment_names"] == ["doc.txt"]

    def test_missing_headers(self):
        msg = email.message_from_string("\r\nJust a body with no headers.")
        result = EmailIngestService._parse_email(msg)
        assert result is not None
        assert result["subject"] == ""
        assert result["sender"] == ""
        assert result["message_id"] == ""


class TestExtractAttachmentText:
    def test_text_file(self):
        result = EmailIngestService._extract_attachment_text(
            filename="readme.txt",
            content_type="text/plain",
            payload=b"Hello world content",
        )
        assert result == "Hello world content"

    def test_csv_file(self):
        result = EmailIngestService._extract_attachment_text(
            filename="data.csv",
            content_type="text/csv",
            payload=b"col1,col2\nval1,val2",
        )
        assert "col1" in result

    def test_unknown_type_returns_empty(self):
        result = EmailIngestService._extract_attachment_text(
            filename="image.png",
            content_type="image/png",
            payload=b"\x89PNG\r\n",
        )
        assert result == ""

    def test_truncates_long_text(self):
        payload = b"x" * 50000
        result = EmailIngestService._extract_attachment_text(
            filename="huge.txt",
            content_type="text/plain",
            payload=payload,
        )
        assert len(result) <= 40000


class TestExtractPdfText:
    def test_invalid_pdf_returns_empty(self):
        result = EmailIngestService._extract_pdf_text(b"not a pdf")
        assert result == ""

    def test_empty_bytes_returns_empty(self):
        result = EmailIngestService._extract_pdf_text(b"")
        assert result == ""


class TestInit:
    def test_constructor(self):
        svc = EmailIngestService(
            host="imap.example.com",
            port=993,
            username="user@example.com",
            password="secret",
            use_ssl=True,
        )
        assert svc.host == "imap.example.com"
        assert svc.port == 993
        assert svc.use_ssl is True
