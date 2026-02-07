"""
RFP Sniper - SharePoint Integration Routes
=============================================
Browse, download, and upload files to SharePoint via Microsoft Graph API.
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.integration import IntegrationConfig, IntegrationProvider
from app.services.auth_service import UserAuth
from app.services.sharepoint_service import create_sharepoint_service

router = APIRouter(prefix="/sharepoint", tags=["SharePoint"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SharePointFile(BaseModel):
    id: str
    name: str
    is_folder: bool
    size: int
    last_modified: str | None = None
    web_url: str | None = None


class UploadResult(BaseModel):
    id: str
    name: str
    web_url: str | None = None
    size: int


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_sp_service(user_id: int, session: AsyncSession):
    """Load the user's SharePoint integration config and build a service."""
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == user_id,
            IntegrationConfig.provider == IntegrationProvider.SHAREPOINT,
            IntegrationConfig.is_enabled == True,  # noqa: E712
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "SharePoint integration not configured or disabled")
    try:
        return create_sharepoint_service(config.config)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/browse", response_model=list[SharePointFile])
async def browse_files(
    path: str = Query("/", description="Folder path to list"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SharePointFile]:
    """List files and folders at a given SharePoint path."""
    sp = await _get_sp_service(current_user.id, session)
    try:
        items = await sp.list_files(path)
        return [SharePointFile(**item) for item in items]
    except Exception as e:
        raise HTTPException(502, f"SharePoint API error: {e}")


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Download a file from SharePoint by its ID."""
    sp = await _get_sp_service(current_user.id, session)
    try:
        content = await sp.download_file(file_id)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="download"'},
        )
    except Exception as e:
        raise HTTPException(502, f"SharePoint API error: {e}")


@router.post("/upload", response_model=UploadResult)
async def upload_file(
    folder: str = Query(..., description="Target folder path"),
    name: str = Query(..., description="File name"),
    content: bytes = b"",
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UploadResult:
    """Upload a file to SharePoint."""
    sp = await _get_sp_service(current_user.id, session)
    try:
        result = await sp.upload_file(folder, name, content)
        return UploadResult(**result)
    except Exception as e:
        raise HTTPException(502, f"SharePoint API error: {e}")


@router.post("/export", response_model=UploadResult)
async def export_to_sharepoint(
    proposal_id: int = Query(...),
    folder: str = Query("/Proposals"),
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UploadResult:
    """Export a proposal (DOCX/PDF) directly to SharePoint.

    Internally calls the export service to generate bytes, then uploads.
    """
    from app.models.proposal import Proposal

    # Verify ownership
    result = await session.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "Proposal not found")

    # Generate export bytes via internal API call
    # Uses httpx to call the existing export endpoint on this same server
    import httpx

    base = "http://localhost:8000/api/v1"
    export_url = f"{base}/export/proposals/{proposal_id}/{format}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(export_url, timeout=60.0)
            resp.raise_for_status()
            content_bytes = resp.content
    except Exception as e:
        raise HTTPException(500, f"Export generation failed: {e}")

    # Upload to SharePoint
    sp = await _get_sp_service(current_user.id, session)
    filename = f"{proposal.title.replace(' ', '_')}.{format}"
    try:
        upload_result = await sp.upload_file(folder, filename, content_bytes)
        return UploadResult(**upload_result)
    except Exception as e:
        raise HTTPException(502, f"SharePoint upload failed: {e}")


@router.get("/status")
async def sharepoint_status(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check if SharePoint integration is configured and reachable."""
    result = await session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.user_id == current_user.id,
            IntegrationConfig.provider == IntegrationProvider.SHAREPOINT,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False, "enabled": False, "connected": False}

    if not config.is_enabled:
        return {"configured": True, "enabled": False, "connected": False}

    try:
        sp = create_sharepoint_service(config.config)
        await sp.list_files("/")
        return {"configured": True, "enabled": True, "connected": True}
    except Exception as e:
        return {"configured": True, "enabled": True, "connected": False, "error": str(e)}
