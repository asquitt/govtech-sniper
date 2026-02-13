"""
RFP Sniper - Email Ingestion Tasks
====================================
Celery tasks for polling IMAP inboxes and processing ingested emails into RFPs.
"""

import asyncio
from datetime import datetime

import structlog
from sqlmodel import select

from app.database import get_celery_session_context
from app.models.email_ingest import EmailIngestConfig, EmailProcessingStatus, IngestedEmail
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
# RFP keyword signals — simple heuristic for classifying emails
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
]


def _looks_like_rfp(subject: str, body: str) -> bool:
    """Quick heuristic: does the email text contain enough RFP-related terms?"""
    combined = f"{subject} {body}".lower()
    hits = sum(1 for kw in _RFP_KEYWORDS if kw in combined)
    return hits >= 2


@celery_app.task(name="app.tasks.email_ingest_tasks.poll_email_inboxes")
def poll_email_inboxes() -> dict:
    """Poll all enabled IMAP configs and store new emails."""

    async def _poll() -> dict:
        fetched_total = 0
        errors = 0

        async with get_celery_session_context() as session:
            result = await session.execute(
                select(EmailIngestConfig).where(EmailIngestConfig.is_enabled == True)
            )
            configs = result.scalars().all()

            for config in configs:
                try:
                    password = decrypt_value(config.encrypted_password)
                    service = EmailIngestService(
                        host=config.imap_server,
                        port=config.imap_port,
                        username=config.email_address,
                        password=password,
                        use_ssl=config.imap_port == 993,
                    )
                    emails = await service.connect_and_fetch(folder=config.folder, limit=50)

                    for em in emails:
                        # Deduplicate by a hash of subject+sender+date
                        msg_id = f"{em['subject']}|{em['sender']}|{em['date']}"

                        existing = await session.execute(
                            select(IngestedEmail).where(IngestedEmail.message_id == msg_id)
                        )
                        if existing.scalar_one_or_none():
                            continue

                        ingested = IngestedEmail(
                            config_id=config.id,
                            message_id=msg_id,
                            subject=em.get("subject", "")[:500],
                            sender=em.get("sender", "")[:255],
                            body_text=em.get("body_text"),
                            processing_status=EmailProcessingStatus.PENDING,
                        )
                        session.add(ingested)
                        fetched_total += 1

                    config.last_checked_at = datetime.utcnow()

                except Exception as exc:
                    logger.error(
                        "IMAP poll failed",
                        config_id=config.id,
                        host=config.imap_server,
                        error=str(exc),
                    )
                    errors += 1

            await session.commit()

        return {"fetched": fetched_total, "errors": errors, "configs": len(configs)}

    result = run_async(_poll())
    logger.info("Email inbox poll complete", **result)
    return {"status": "ok", **result}


@celery_app.task(name="app.tasks.email_ingest_tasks.process_ingested_emails")
def process_ingested_emails() -> dict:
    """Classify pending ingested emails and create RFP records for matches."""

    async def _process() -> dict:
        processed = 0
        created_rfps = 0

        async with get_celery_session_context() as session:
            result = await session.execute(
                select(IngestedEmail)
                .where(IngestedEmail.processing_status == EmailProcessingStatus.PENDING)
                .limit(100)
            )
            pending = result.scalars().all()

            for em in pending:
                try:
                    # Get the config to find user_id
                    config_result = await session.execute(
                        select(EmailIngestConfig).where(EmailIngestConfig.id == em.config_id)
                    )
                    config = config_result.scalar_one_or_none()
                    if not config:
                        em.processing_status = EmailProcessingStatus.ERROR
                        em.error_message = "Config not found"
                        processed += 1
                        continue

                    if _looks_like_rfp(em.subject, em.body_text or ""):
                        rfp = RFP(
                            user_id=config.user_id,
                            title=em.subject[:255],
                            description=f"Ingested from email: {em.sender}",
                            agency=_extract_agency(em.sender),
                            status=RFPStatus.NEW,
                        )
                        session.add(rfp)
                        await session.flush()

                        em.created_rfp_id = rfp.id
                        em.processing_status = EmailProcessingStatus.PROCESSED
                        created_rfps += 1
                    else:
                        em.processing_status = EmailProcessingStatus.IGNORED

                    processed += 1

                except Exception as exc:
                    em.processing_status = EmailProcessingStatus.ERROR
                    em.error_message = str(exc)[:500]
                    processed += 1
                    logger.error("Email processing failed", email_id=em.id, error=str(exc))

            await session.commit()

        return {"processed": processed, "created_rfps": created_rfps}

    result = run_async(_process())
    logger.info("Email processing complete", **result)
    return {"status": "ok", **result}


def _extract_agency(sender: str) -> str:
    """Best-effort agency extraction from sender email domain."""
    if "@" in sender:
        domain = sender.split("@")[-1].strip(">").lower()
        if ".gov" in domain:
            # e.g. john@gsa.gov -> GSA
            parts = domain.split(".")
            idx = parts.index("gov") if "gov" in parts else 0
            if idx > 0:
                return parts[idx - 1].upper()
    return "Unknown"
