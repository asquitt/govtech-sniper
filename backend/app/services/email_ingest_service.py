"""Email ingestion service for forwarded RFP solicitations."""

import asyncio
import email
import imaplib
from email.message import Message

import structlog

logger = structlog.get_logger(__name__)


class EmailIngestService:
    """Fetches and parses forwarded RFP emails from an IMAP mailbox."""

    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl

    async def connect_and_fetch(self, folder: str = "INBOX", limit: int = 50) -> list[dict]:
        """Connect to IMAP server and fetch unread emails."""
        return await asyncio.to_thread(self._fetch_sync, folder, limit)

    def _fetch_sync(self, folder: str, limit: int) -> list[dict]:
        """Synchronous IMAP fetch (run in thread pool)."""
        try:
            if self.use_ssl:
                conn = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                conn = imaplib.IMAP4(self.host, self.port)

            conn.login(self.username, self.password)
            conn.select(folder)

            _, msg_ids = conn.search(None, "UNSEEN")
            if not msg_ids[0]:
                conn.logout()
                return []

            ids = msg_ids[0].split()[:limit]
            results: list[dict] = []

            for msg_id in ids:
                _, data = conn.fetch(msg_id, "(RFC822)")
                if not data or not data[0]:
                    continue
                raw = data[0][1]
                if isinstance(raw, bytes):
                    msg = email.message_from_bytes(raw)
                else:
                    msg = email.message_from_string(raw)
                parsed = self._parse_email(msg)
                if parsed:
                    results.append(parsed)

            conn.logout()
            return results

        except imaplib.IMAP4.error as exc:
            logger.error("IMAP connection failed", error=str(exc))
            return []
        except Exception as exc:
            logger.error("Email ingestion error", error=str(exc))
            return []

    @staticmethod
    def _parse_email(msg: Message) -> dict | None:
        """Parse an email message into a structured dict."""
        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        date = msg.get("Date", "")

        # Extract body
        body_text = ""
        body_html = ""
        attachments: list[dict] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition:
                    filename = part.get_filename() or "unnamed"
                    payload = part.get_payload(decode=True)
                    if payload:
                        attachments.append(
                            {
                                "filename": filename,
                                "content_type": content_type,
                                "size": len(payload),
                                "data": payload,
                            }
                        )
                elif content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode("utf-8", errors="replace")

        return {
            "subject": subject,
            "sender": sender,
            "date": date,
            "body_text": body_text,
            "body_html": body_html,
            "attachments": attachments,
            "attachment_count": len(attachments),
        }

    async def test_connection(self) -> dict:
        """Test IMAP connection without fetching emails."""
        try:
            result = await asyncio.to_thread(self._test_sync)
            return result
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _test_sync(self) -> dict:
        try:
            if self.use_ssl:
                conn = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                conn = imaplib.IMAP4(self.host, self.port)
            conn.login(self.username, self.password)
            _, folders = conn.list()
            folder_names = []
            if folders:
                for f in folders:
                    if isinstance(f, bytes):
                        folder_names.append(f.decode("utf-8", errors="replace"))
            conn.logout()
            return {"status": "connected", "folders": folder_names}
        except imaplib.IMAP4.error as exc:
            return {"status": "auth_error", "message": str(exc)}
