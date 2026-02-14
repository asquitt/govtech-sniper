"""
RFP Sniper - Email Ingestion Tasks
====================================
Celery tasks for polling IMAP inboxes and processing ingested emails into RFPs.
"""

import asyncio
import hashlib
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_celery_session_context
from app.models.collaboration import SharedWorkspace, WorkspaceMember
from app.models.email_ingest import EmailIngestConfig, EmailProcessingStatus, IngestedEmail
from app.models.inbox import InboxMessage, InboxMessageType
from app.models.rfp import RFP, RFPStatus
from app.services.email_ingest_service import EmailIngestService
from app.services.encryption_service import decrypt_value
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# RFP keyword signals and extraction patterns
# ---------------------------------------------------------------------------
_RFP_KEYWORDS = [
    "request for proposal",
    "request for quotation",
    "rfp",
    "rfq",
    "rfi",
    "solicitation",
    "notice id",
    "sam.gov",
    "naics",
    "statement of work",
    "scope of work",
    "period of performance",
    "proposal due",
    "response deadline",
    "contracting officer",
    "procurement",
    "amendment",
]

_SOLICITATION_PATTERNS = [
    re.compile(
        r"(?i)\b(?:solicitation(?:\s+number)?|notice(?:\s+id)?|rfp|rfq|rfi)\b"
        r"\s*(?:number|no\.?|id|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-_/]{3,})"
    ),
]


def _extract_solicitation_number(subject: str, body: str) -> str | None:
    combined = f"{subject}\n{body}"
    for pattern in _SOLICITATION_PATTERNS:
        match = pattern.search(combined)
        if not match:
            continue
        candidate = re.sub(r"[^A-Za-z0-9\-_/.]", "", match.group(1)).upper()
        if len(candidate) >= 4:
            return candidate[:100]
    return None


def _fallback_solicitation_number(message_id: str) -> str:
    digest = hashlib.sha256(message_id.encode("utf-8", errors="ignore")).hexdigest()[:12].upper()
    return f"EMAIL-{digest}"


def _normalize_message_id(parsed_email: dict[str, Any]) -> str:
    message_id = (parsed_email.get("message_id") or "").strip()
    if message_id:
        return message_id[:500]
    subject = (parsed_email.get("subject") or "").strip()
    sender = (parsed_email.get("sender") or "").strip()
    sent_at = (parsed_email.get("date") or "").strip()
    return f"{subject}|{sender}|{sent_at}"[:500]


def _parse_received_at(raw_date: str | None) -> datetime:
    if not raw_date:
        return datetime.utcnow()
    try:
        parsed = parsedate_to_datetime(raw_date)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed
    except Exception:
        return datetime.utcnow()


def _extract_agency(sender: str) -> str:
    """Best-effort agency extraction from sender email domain."""
    _, sender_email = parseaddr(sender)
    domain = sender_email.lower().split("@")[-1] if "@" in sender_email else ""
    if domain.endswith(".gov"):
        agency_part = domain.split(".")[0].strip()
        if agency_part:
            return agency_part.upper()
    return "Unknown"


def _extract_sender_email(sender: str) -> str | None:
    _, sender_email = parseaddr(sender)
    return sender_email.lower() if sender_email else None


def _clean_subject(subject: str) -> str:
    cleaned = re.sub(r"(?i)^\s*(re|fw|fwd)\s*:\s*", "", subject).strip()
    return cleaned or "Forwarded Opportunity"


def _classify_rfp_likelihood(
    *,
    subject: str,
    body: str,
    sender: str,
    attachment_names: Sequence[str],
) -> tuple[float, list[str]]:
    combined = f"{subject}\n{body}".lower()
    score = 0.0
    reasons: list[str] = []

    keyword_hits = [kw for kw in _RFP_KEYWORDS if kw in combined]
    if keyword_hits:
        score += min(0.5, 0.08 * len(keyword_hits))
        reasons.append(f"Keyword hits: {', '.join(keyword_hits[:4])}")

    solicitation_number = _extract_solicitation_number(subject, body)
    if solicitation_number:
        score += 0.32
        reasons.append(f"Detected solicitation identifier `{solicitation_number}`")

    lower_attachments = [name.lower() for name in attachment_names]
    if any(name.endswith(".pdf") for name in lower_attachments):
        score += 0.1
        reasons.append("Email includes PDF attachment(s)")
    if any(name.endswith((".doc", ".docx")) for name in lower_attachments):
        score += 0.06
        reasons.append("Email includes Word attachment(s)")

    sender_email = _extract_sender_email(sender)
    if sender_email and sender_email.endswith(".gov"):
        score += 0.08
        reasons.append("Sender domain is .gov")

    confidence = round(min(score, 1.0), 3)
    if not reasons:
        reasons.append("No strong solicitation signals detected")
    return confidence, reasons


async def _workspace_routing_allowed(
    session: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
) -> bool:
    workspace = await session.get(SharedWorkspace, workspace_id)
    if not workspace:
        return False
    if workspace.owner_id == user_id:
        return True

    member_result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    return member_result.scalars().first() is not None


async def poll_email_configs(
    session: AsyncSession,
    *,
    configs: Sequence[EmailIngestConfig],
    limit: int = 50,
) -> dict[str, int]:
    fetched_total = 0
    duplicates = 0
    errors = 0

    for config in configs:
        if not config.is_enabled:
            continue

        try:
            password = decrypt_value(config.encrypted_password)
            service = EmailIngestService(
                host=config.imap_server,
                port=config.imap_port,
                username=config.email_address,
                password=password,
                use_ssl=config.imap_port == 993,
            )
            emails = await service.connect_and_fetch(folder=config.folder, limit=limit)

            for parsed in emails:
                msg_id = _normalize_message_id(parsed)
                existing = await session.execute(
                    select(IngestedEmail).where(
                        IngestedEmail.config_id == config.id,
                        IngestedEmail.message_id == msg_id,
                    )
                )
                if existing.scalar_one_or_none():
                    duplicates += 1
                    continue

                body_text = (parsed.get("body_text") or "").strip()
                if not body_text:
                    body_text = (parsed.get("body_html") or "").strip()
                attachment_text = (parsed.get("attachment_text") or "").strip()
                if attachment_text:
                    body_text = (
                        f"{body_text}\n\nAttachment Extracts:\n{attachment_text}".strip()
                        if body_text
                        else attachment_text
                    )

                attachment_names = [
                    str(name)[:255]
                    for name in (parsed.get("attachment_names") or [])
                    if isinstance(name, str)
                ]
                ingested = IngestedEmail(
                    config_id=config.id,
                    message_id=msg_id,
                    subject=str(parsed.get("subject") or "")[:500],
                    sender=str(parsed.get("sender") or "")[:255],
                    received_at=_parse_received_at(parsed.get("date")),
                    body_text=body_text or None,
                    attachment_count=len(attachment_names),
                    attachment_names=attachment_names[:20],
                    processing_status=EmailProcessingStatus.PENDING,
                )
                session.add(ingested)
                fetched_total += 1

            config.last_checked_at = datetime.utcnow()

        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "IMAP poll failed",
                config_id=config.id,
                host=config.imap_server,
                error=str(exc),
            )
            errors += 1

    await session.flush()
    return {
        "configs_checked": len(configs),
        "fetched": fetched_total,
        "duplicates": duplicates,
        "errors": errors,
    }


async def process_pending_ingested_emails(
    session: AsyncSession,
    *,
    config_ids: Sequence[int] | None = None,
    limit: int = 100,
) -> dict[str, int]:
    query = select(IngestedEmail).where(
        IngestedEmail.processing_status == EmailProcessingStatus.PENDING
    )
    if config_ids:
        query = query.where(IngestedEmail.config_id.in_(config_ids))
    query = query.order_by(IngestedEmail.created_at.asc()).limit(limit)
    pending = (await session.execute(query)).scalars().all()
    if not pending:
        return {"processed": 0, "created_rfps": 0, "inbox_forwarded": 0, "errors": 0}

    config_lookup_query = select(EmailIngestConfig).where(
        EmailIngestConfig.id.in_({email.config_id for email in pending})
    )
    configs = (await session.execute(config_lookup_query)).scalars().all()
    config_map = {config.id: config for config in configs}

    processed = 0
    created_rfps = 0
    inbox_forwarded = 0
    errors = 0

    for ingested in pending:
        now = datetime.utcnow()
        config = config_map.get(ingested.config_id)
        if not config:
            ingested.processing_status = EmailProcessingStatus.ERROR
            ingested.error_message = "Config not found"
            ingested.processed_at = now
            processed += 1
            errors += 1
            continue

        body_text = ingested.body_text or ""
        confidence, reasons = _classify_rfp_likelihood(
            subject=ingested.subject,
            body=body_text,
            sender=ingested.sender,
            attachment_names=ingested.attachment_names or [],
        )
        ingested.classification_confidence = confidence
        ingested.classification_reasons = reasons

        threshold = max(0.0, min(1.0, float(config.min_rfp_confidence)))
        if confidence < threshold:
            ingested.processing_status = EmailProcessingStatus.IGNORED
            ingested.error_message = (
                f"Below confidence threshold ({confidence:.2f} < {threshold:.2f})"
            )
            ingested.processed_at = now
            processed += 1
            continue

        if not config.auto_create_rfps:
            ingested.processing_status = EmailProcessingStatus.PROCESSED
            ingested.error_message = None
            ingested.processed_at = now
            processed += 1
            continue

        try:
            solicitation_number = _extract_solicitation_number(
                ingested.subject, body_text
            ) or _fallback_solicitation_number(ingested.message_id)
            existing_rfp = (
                await session.execute(
                    select(RFP).where(
                        RFP.user_id == config.user_id,
                        RFP.solicitation_number == solicitation_number,
                    )
                )
            ).scalar_one_or_none()

            if existing_rfp:
                rfp = existing_rfp
            else:
                title = _clean_subject(ingested.subject)
                sender_email = _extract_sender_email(ingested.sender)
                rfp = RFP(
                    user_id=config.user_id,
                    title=title[:500],
                    solicitation_number=solicitation_number[:100],
                    agency=_extract_agency(ingested.sender),
                    source_type="email",
                    posted_date=ingested.received_at,
                    status=RFPStatus.NEW,
                    description=f"Ingested from email sender {ingested.sender}",
                    full_text=body_text[:50000] if body_text else None,
                    buyer_contact_email=sender_email[:255] if sender_email else None,
                )
                session.add(rfp)
                await session.flush()
                created_rfps += 1

            ingested.created_rfp_id = rfp.id
            ingested.processing_status = EmailProcessingStatus.PROCESSED
            ingested.error_message = None
            ingested.processed_at = now
            processed += 1

            if config.workspace_id and await _workspace_routing_allowed(
                session,
                workspace_id=config.workspace_id,
                user_id=config.user_id,
            ):
                message_body = (
                    f"Auto-created opportunity from forwarded email.\n\n"
                    f"Title: {rfp.title}\n"
                    f"Solicitation: {rfp.solicitation_number}\n"
                    f"Sender: {ingested.sender}\n"
                    f"Confidence: {confidence:.2f}\n"
                    f"Signals: {', '.join(reasons[:3])}"
                )
                session.add(
                    InboxMessage(
                        workspace_id=config.workspace_id,
                        sender_id=config.user_id,
                        subject=f"Email ingest created RFP: {rfp.solicitation_number}",
                        body=message_body,
                        message_type=InboxMessageType.RFP_FORWARD.value,
                        attachments=(
                            json.dumps(ingested.attachment_names)
                            if ingested.attachment_names
                            else None
                        ),
                    )
                )
                inbox_forwarded += 1

        except Exception as exc:  # pragma: no cover - defensive guard
            ingested.processing_status = EmailProcessingStatus.ERROR
            ingested.error_message = str(exc)[:500]
            ingested.processed_at = now
            processed += 1
            errors += 1
            logger.error("Email processing failed", email_id=ingested.id, error=str(exc))

    await session.flush()
    return {
        "processed": processed,
        "created_rfps": created_rfps,
        "inbox_forwarded": inbox_forwarded,
        "errors": errors,
    }


@celery_app.task(name="app.tasks.email_ingest_tasks.poll_email_inboxes")
def poll_email_inboxes() -> dict:
    """Poll all enabled IMAP configs and store new emails."""

    async def _poll() -> dict:
        async with get_celery_session_context() as session:
            configs = (
                (
                    await session.execute(
                        select(EmailIngestConfig).where(EmailIngestConfig.is_enabled == True)
                    )
                )
                .scalars()
                .all()
            )
            result = await poll_email_configs(session, configs=configs, limit=50)
        return result

    result = run_async(_poll())
    logger.info("Email inbox poll complete", **result)
    return {"status": "ok", **result}


@celery_app.task(name="app.tasks.email_ingest_tasks.process_ingested_emails")
def process_ingested_emails() -> dict:
    """Classify pending ingested emails and create RFP records for matches."""

    async def _process() -> dict:
        async with get_celery_session_context() as session:
            result = await process_pending_ingested_emails(session, limit=100)
        return result

    result = run_async(_process())
    logger.info("Email processing complete", **result)
    return {"status": "ok", **result}
