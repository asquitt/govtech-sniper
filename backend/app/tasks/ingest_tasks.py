"""
RFP Sniper - Ingest Tasks
==========================
Celery tasks for SAM.gov data ingestion.
"""

import asyncio
import hashlib
import json

import structlog
from sqlalchemy import desc
from sqlmodel import select

from app.config import settings
from app.database import get_celery_session_context
from app.models.opportunity_snapshot import SAMOpportunitySnapshot
from app.models.rfp import RFP, RFPStatus
from app.models.user import User, UserProfile
from app.schemas.rfp import SAMSearchParams
from app.services.filters import KillerFilterService, quick_disqualify
from app.services.ingest_service import SAMGovAPIError, SAMGovService
from app.services.rfp_downloader import get_rfp_downloader
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_tasks.ingest_sam_opportunities",
    max_retries=3,
    default_retry_delay=60,
)
def ingest_sam_opportunities(
    self,
    user_id: int,
    keywords: str,
    days_back: int = 90,
    limit: int = 25,
    naics_codes: list[str] | None = None,
    apply_filter: bool = True,
    mock_variant: str | None = None,
) -> dict:
    """
    Celery task to ingest opportunities from SAM.gov.

    Args:
        user_id: User requesting the ingest
        keywords: Search keywords
        days_back: How many days back to search
        limit: Maximum results
        naics_codes: Filter by NAICS codes
        apply_filter: Whether to run Killer Filter

    Returns:
        Summary of ingested opportunities
    """
    task_id = self.request.id
    logger.info(
        "Starting SAM.gov ingest task",
        task_id=task_id,
        user_id=user_id,
        keywords=keywords,
    )

    async def _ingest():
        sam_service = SAMGovService(mock_variant=mock_variant)
        filter_service = KillerFilterService() if apply_filter else None

        def _hash_payload(payload: dict) -> str:
            payload_str = json.dumps(payload, sort_keys=True, default=str)
            return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        # Search SAM.gov (raw + parsed for snapshotting)
        params = SAMSearchParams(
            keywords=keywords,
            days_back=days_back,
            limit=limit,
            naics_codes=naics_codes,
        )

        try:
            raw_opportunities = await sam_service.search_opportunities_with_raw(params)
        except SAMGovAPIError as e:
            logger.error(f"SAM.gov API error: {e.message}")
            if e.retryable:
                raise self.retry(exc=e)
            raise e

        parsed_opportunities = []
        for raw_opp in raw_opportunities:
            try:
                opp = sam_service.parse_opportunity(raw_opp)
                parsed_opportunities.append((opp, raw_opp))
            except Exception as e:
                logger.warning(f"Failed to parse opportunity: {e}", raw=raw_opp)

        if not parsed_opportunities:
            return {
                "task_id": task_id,
                "status": "completed",
                "total_found": 0,
                "saved": 0,
                "filtered_out": 0,
                "snapshots_created": 0,
                "snapshots_skipped": 0,
                "attachments_downloaded": 0,
            }

        # Get user profile for filtering
        user_profile = None
        if apply_filter:
            async with get_celery_session_context() as session:
                result = await session.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
                user_profile = result.scalar_one_or_none()

        saved_count = 0
        filtered_count = 0
        snapshots_created = 0
        snapshots_skipped = 0
        attachments_downloaded = 0

        download_enabled = settings.sam_download_attachments and (
            not settings.mock_sam_gov or settings.sam_mock_attachments_dir
        )
        download_queue = []

        async with get_celery_session_context() as session:
            for opp, raw_opp in parsed_opportunities:
                notice_id = (
                    raw_opp.get("noticeId")
                    or raw_opp.get("noticeID")
                    or raw_opp.get("solicitationNumber")
                    or opp.solicitation_number
                )

                # Check if already exists
                existing = await session.execute(
                    select(RFP).where(RFP.solicitation_number == opp.solicitation_number)
                )
                existing_rfp = existing.scalar_one_or_none()

                is_new_rfp = existing_rfp is None

                if is_new_rfp:
                    # Create RFP record
                    rfp = RFP(
                        user_id=user_id,
                        title=opp.title,
                        solicitation_number=opp.solicitation_number,
                        agency=opp.agency,
                        sub_agency=opp.sub_agency,
                        naics_code=opp.naics_code,
                        set_aside=opp.set_aside,
                        rfp_type=opp.rfp_type,
                        posted_date=opp.posted_date,
                        response_deadline=opp.response_deadline,
                        sam_gov_link=opp.ui_link,
                        description=opp.description,
                        status=RFPStatus.NEW,
                    )

                    # Apply quick rule-based filter
                    if user_profile:
                        disqualify_reason = quick_disqualify(rfp, user_profile)
                        if disqualify_reason:
                            rfp.is_qualified = False
                            rfp.qualification_reason = disqualify_reason
                            filtered_count += 1

                    session.add(rfp)
                    await session.flush()
                    rfp_id = rfp.id
                    saved_count += 1

                    if download_enabled and notice_id:
                        download_queue.append((rfp_id, notice_id))
                else:
                    rfp_id = existing_rfp.id
                    logger.debug(f"Skipping existing RFP: {opp.solicitation_number}")
                    if (
                        download_enabled
                        and notice_id
                        and (
                            existing_rfp.attachment_paths is None
                            or len(existing_rfp.attachment_paths) == 0
                        )
                    ):
                        download_queue.append((rfp_id, notice_id))

                # Snapshot raw payload for change tracking
                if notice_id:
                    raw_hash = _hash_payload(raw_opp)
                    latest_snapshot = await session.execute(
                        select(SAMOpportunitySnapshot)
                        .where(SAMOpportunitySnapshot.notice_id == notice_id)
                        .order_by(desc(SAMOpportunitySnapshot.fetched_at))
                        .limit(1)
                    )
                    latest_snapshot = latest_snapshot.scalar_one_or_none()
                    if not latest_snapshot or latest_snapshot.raw_hash != raw_hash:
                        session.add(
                            SAMOpportunitySnapshot(
                                notice_id=notice_id,
                                solicitation_number=opp.solicitation_number,
                                rfp_id=rfp_id,
                                user_id=user_id,
                                posted_date=opp.posted_date,
                                response_deadline=opp.response_deadline,
                                raw_hash=raw_hash,
                                raw_payload=raw_opp,
                            )
                        )
                        snapshots_created += 1
                    else:
                        snapshots_skipped += 1

            await session.commit()

        if download_enabled and download_queue:
            downloader = get_rfp_downloader()
            async with get_celery_session_context() as session:
                for rfp_id, notice_id in download_queue:
                    try:
                        downloaded = await downloader.download_all_attachments(
                            notice_id,
                            rfp_id,
                            max_attachments=settings.sam_max_attachments,
                        )
                    except Exception as e:
                        logger.warning(
                            "Attachment download failed",
                            notice_id=notice_id,
                            rfp_id=rfp_id,
                            error=str(e),
                        )
                        continue

                    if not downloaded:
                        continue

                    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
                    rfp = result.scalar_one_or_none()
                    if not rfp:
                        continue

                    rfp.attachment_paths = [doc.file_path for doc in downloaded]
                    attachments_downloaded += len(downloaded)

                    if not rfp.full_text:
                        for doc in downloaded:
                            if doc.extracted_text:
                                rfp.full_text = doc.extracted_text
                                rfp.pdf_file_path = doc.file_path
                                break

                await session.commit()

        # Run AI Killer Filter on remaining RFPs (if enabled)
        if apply_filter and filter_service and user_profile:
            async with get_celery_session_context() as session:
                result = await session.execute(
                    select(RFP)
                    .where(
                        RFP.user_id == user_id,
                        RFP.is_qualified.is_(None),
                        RFP.status == RFPStatus.NEW,
                    )
                    .limit(10)  # Batch limit to control costs
                )
                rfps_to_filter = result.scalars().all()

                for rfp in rfps_to_filter:
                    filter_result = await filter_service.filter_rfp(rfp, user_profile)
                    rfp.is_qualified = filter_result.is_qualified
                    rfp.qualification_reason = filter_result.reason
                    rfp.qualification_score = filter_result.confidence * 100

                    if not filter_result.is_qualified:
                        filtered_count += 1

                await session.commit()

        return {
            "task_id": task_id,
            "status": "completed",
            "total_found": len(parsed_opportunities),
            "saved": saved_count,
            "filtered_out": filtered_count,
            "qualified": saved_count - filtered_count,
            "snapshots_created": snapshots_created,
            "snapshots_skipped": snapshots_skipped,
            "attachments_downloaded": attachments_downloaded,
        }

    return run_async(_ingest())


@celery_app.task(name="app.tasks.ingest_tasks.periodic_sam_scan")
def periodic_sam_scan():
    """
    Periodic task to scan SAM.gov for all active users.
    Runs via Celery Beat schedule.
    """
    logger.info("Running periodic SAM.gov scan")

    async def _scan_all():
        async with get_celery_session_context() as session:
            # Get all active users with profiles
            result = await session.execute(
                select(User, UserProfile)
                .join(UserProfile, User.id == UserProfile.user_id)
                .where(User.is_active == True)
            )
            users_with_profiles = result.all()

            for user, profile in users_with_profiles:
                if profile.include_keywords:
                    # Queue individual ingest task for each user
                    for keyword in profile.include_keywords[:3]:  # Limit keywords
                        ingest_sam_opportunities.delay(
                            user_id=user.id,
                            keywords=keyword,
                            days_back=7,  # Only check last week
                            limit=10,
                            naics_codes=profile.naics_codes or None,
                            apply_filter=True,
                        )
                        logger.info(
                            f"Queued SAM scan for user {user.id}",
                            keyword=keyword,
                        )

    run_async(_scan_all())
    return {"status": "scans_queued"}
