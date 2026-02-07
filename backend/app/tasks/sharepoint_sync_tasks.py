"""
RFP Sniper - SharePoint Sync Celery Tasks
==========================================
Periodic and on-demand sync between proposals and SharePoint.
"""

import asyncio
import logging
from datetime import datetime

from sqlmodel import select

from app.database import get_celery_session_context
from app.models.integration import IntegrationConfig, IntegrationProvider
from app.models.proposal import Proposal
from app.models.sharepoint_sync import SharePointSyncConfig, SharePointSyncLog
from app.services.sharepoint_service import create_sharepoint_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.sharepoint_sync_tasks.sync_proposal_to_sharepoint",
    max_retries=3,
    default_retry_delay=60,
)
def sync_proposal_to_sharepoint(self, config_id: int) -> dict:
    """Export proposal as DOCX and upload to configured SharePoint folder."""
    return asyncio.get_event_loop().run_until_complete(_sync_proposal(config_id))


async def _sync_proposal(config_id: int) -> dict:
    async with get_celery_session_context() as session:
        # Load sync config
        result = await session.execute(
            select(SharePointSyncConfig).where(SharePointSyncConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            return {"error": "Config not found", "config_id": config_id}

        # Load proposal
        result = await session.execute(select(Proposal).where(Proposal.id == config.proposal_id))
        proposal = result.scalar_one_or_none()
        if not proposal:
            return {"error": "Proposal not found", "proposal_id": config.proposal_id}

        # Load SharePoint integration
        result = await session.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.user_id == config.user_id,
                IntegrationConfig.provider == IntegrationProvider.SHAREPOINT,
                IntegrationConfig.is_enabled == True,  # noqa: E712
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            log = SharePointSyncLog(
                config_id=config_id,
                action="push",
                status="failed",
                details={"error": "SharePoint integration not configured"},
            )
            session.add(log)
            await session.commit()
            return {"error": "No SharePoint integration"}

        try:
            sp = create_sharepoint_service(integration.config)

            # Generate DOCX via internal export endpoint
            import httpx

            export_url = f"http://localhost:8000/api/v1/export/proposals/{proposal.id}/docx"
            async with httpx.AsyncClient() as client:
                resp = await client.get(export_url, timeout=60.0)
                resp.raise_for_status()
                docx_bytes = resp.content

            # Upload to SharePoint
            filename = f"{proposal.title.replace(' ', '_')}.docx"
            upload_result = await sp.upload_file(config.sharepoint_folder, filename, docx_bytes)

            # Update config timestamp
            config.last_synced_at = datetime.utcnow()
            session.add(config)

            # Log success
            log = SharePointSyncLog(
                config_id=config_id,
                action="push",
                status="success",
                details={
                    "file_name": filename,
                    "file_id": upload_result.get("id"),
                    "size": upload_result.get("size", 0),
                    "web_url": upload_result.get("web_url"),
                },
            )
            session.add(log)
            await session.commit()

            logger.info(
                "SharePoint sync completed",
                extra={"config_id": config_id, "proposal_id": proposal.id},
            )
            return {
                "status": "success",
                "file_name": filename,
                "web_url": upload_result.get("web_url"),
            }

        except Exception as e:
            log = SharePointSyncLog(
                config_id=config_id,
                action="push",
                status="failed",
                details={"error": str(e)},
            )
            session.add(log)
            await session.commit()
            logger.error(f"SharePoint sync failed: {e}", extra={"config_id": config_id})
            return {"error": str(e)}


@celery_app.task(
    bind=True,
    name="app.tasks.sharepoint_sync_tasks.watch_sharepoint_folders",
    max_retries=2,
    default_retry_delay=120,
)
def watch_sharepoint_folders(self) -> dict:
    """Periodic task: check watched SharePoint folders for new files."""
    return asyncio.get_event_loop().run_until_complete(_watch_folders())


async def _watch_folders() -> dict:
    detected = 0
    errors = 0

    async with get_celery_session_context() as session:
        result = await session.execute(
            select(SharePointSyncConfig).where(
                SharePointSyncConfig.watch_for_rfps == True,  # noqa: E712
                SharePointSyncConfig.auto_sync_enabled == True,  # noqa: E712
            )
        )
        configs = result.scalars().all()

        for config in configs:
            try:
                # Load user's SharePoint integration
                int_result = await session.execute(
                    select(IntegrationConfig).where(
                        IntegrationConfig.user_id == config.user_id,
                        IntegrationConfig.provider == IntegrationProvider.SHAREPOINT,
                        IntegrationConfig.is_enabled == True,  # noqa: E712
                    )
                )
                integration = int_result.scalar_one_or_none()
                if not integration:
                    continue

                sp = create_sharepoint_service(integration.config)
                files = await sp.list_files(config.sharepoint_folder)

                # Filter for new files since last sync
                cutoff = config.last_synced_at
                new_files = []
                for f in files:
                    if f.get("is_folder"):
                        continue
                    modified = f.get("last_modified")
                    if modified and cutoff:
                        from datetime import datetime as dt

                        try:
                            file_dt = dt.fromisoformat(modified.replace("Z", "+00:00"))
                            if file_dt <= cutoff.replace(tzinfo=file_dt.tzinfo):
                                continue
                        except (ValueError, TypeError):
                            pass
                    new_files.append(f)

                if new_files:
                    log = SharePointSyncLog(
                        config_id=config.id,
                        action="watch_detect",
                        status="success",
                        details={
                            "new_files": [
                                {"name": f["name"], "id": f["id"]} for f in new_files[:20]
                            ],
                            "count": len(new_files),
                        },
                    )
                    session.add(log)
                    detected += len(new_files)

                # Update last_synced_at for the watch
                config.last_synced_at = datetime.utcnow()
                session.add(config)

            except Exception as e:
                logger.warning(
                    f"Watch failed for config {config.id}: {e}",
                    extra={"config_id": config.id},
                )
                errors += 1

        await session.commit()

    return {"detected": detected, "configs_checked": len(configs), "errors": errors}
