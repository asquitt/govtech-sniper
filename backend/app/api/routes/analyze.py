"""
RFP Sniper - Analysis Routes
=============================
Endpoints for RFP analysis using Gemini AI.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select

from app.api.deps import get_current_user_optional, resolve_user_id
from app.config import settings
from app.database import get_session
from app.models.rfp import RFP, ComplianceMatrix, RFPStatus
from app.schemas.rfp import (
    AnalyzeResponse,
    ComplianceMatrixRead,
    ComplianceRequirementCreate,
    ComplianceRequirementRead,
    ComplianceRequirementUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.webhook_service import dispatch_webhook_event
from app.tasks.analysis_tasks import analyze_rfp, run_killer_filter

router = APIRouter(prefix="/analyze", tags=["Analysis"])


class ComplianceGapSummary(BaseModel):
    rfp_id: int
    total_open: int
    mandatory_open: int
    gaps: list[ComplianceRequirementRead]


@router.post("/{rfp_id}", response_model=AnalyzeResponse)
async def trigger_rfp_analysis(
    rfp_id: int = Path(..., description="RFP ID to analyze"),
    force_reanalyze: bool = Query(False, description="Re-analyze even if already done"),
    session: AsyncSession = Depends(get_session),
) -> AnalyzeResponse:
    """
    Trigger Deep Read analysis on an RFP.

    This uses Gemini 1.5 Pro to:
    1. Extract all compliance requirements
    2. Categorize by importance (Mandatory, Evaluated, etc.)
    3. Generate a summary

    The analysis runs as a background task. Poll the status endpoint
    or check the RFP's status field for completion.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured. Set GEMINI_API_KEY environment variable.",
        )

    # Verify RFP exists
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    # Check if already analyzed
    if rfp.status == RFPStatus.ANALYZED and not force_reanalyze:
        return AnalyzeResponse(
            task_id="none",
            rfp_id=rfp_id,
            message="RFP already analyzed. Set force_reanalyze=true to re-analyze.",
            status="already_completed",
        )

    # Check if has content to analyze
    if not rfp.full_text and not rfp.description:
        raise HTTPException(
            status_code=400,
            detail="RFP has no text content to analyze. Upload a PDF first.",
        )

    # Queue the analysis task
    task = analyze_rfp.delay(rfp_id=rfp_id, force_reanalyze=force_reanalyze)

    return AnalyzeResponse(
        task_id=task.id,
        rfp_id=rfp_id,
        message="Deep Read analysis started",
        status="analyzing",
    )


@router.get("/{rfp_id}/status/{task_id}")
async def get_analysis_status(
    rfp_id: int = Path(..., description="RFP ID"),
    task_id: str = Path(..., description="Task ID from analyze endpoint"),
) -> dict:
    """
    Get the status of an analysis task.
    """
    from celery.result import AsyncResult

    from app.tasks.celery_app import celery_app

    def normalize_status(result: AsyncResult) -> str:
        if result.ready():
            return "completed" if result.successful() else "failed"
        state = (result.state or "").lower()
        if state in {"pending", "received"}:
            return "pending"
        return "processing"

    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        if result.successful():
            return {
                "task_id": task_id,
                "rfp_id": rfp_id,
                "status": "completed",
                "result": result.get(),
            }
        else:
            return {
                "task_id": task_id,
                "rfp_id": rfp_id,
                "status": "failed",
                "error": str(result.result),
            }
    else:
        return {
            "task_id": task_id,
            "rfp_id": rfp_id,
            "status": normalize_status(result),
        }


@router.get("/{rfp_id}/matrix", response_model=ComplianceMatrixRead)
async def get_compliance_matrix(
    rfp_id: int = Path(..., description="RFP ID"),
    session: AsyncSession = Depends(get_session),
) -> ComplianceMatrixRead:
    """
    Get the extracted compliance matrix for an RFP.

    Returns all requirements with their importance levels,
    categories, and addressed status.
    """
    # Get the compliance matrix
    result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = result.scalar_one_or_none()

    if not matrix:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance matrix not found for RFP {rfp_id}. Run analysis first.",
        )

    # Parse requirements
    requirements = [ComplianceRequirementRead(**req) for req in matrix.requirements]

    return ComplianceMatrixRead(
        id=matrix.id,
        rfp_id=matrix.rfp_id,
        requirements=requirements,
        total_requirements=matrix.total_requirements,
        mandatory_count=matrix.mandatory_count,
        addressed_count=matrix.addressed_count,
        extraction_confidence=matrix.extraction_confidence,
        created_at=matrix.created_at,
        updated_at=matrix.updated_at,
    )


@router.get("/{rfp_id}/gaps", response_model=ComplianceGapSummary)
async def get_compliance_gaps(
    rfp_id: int = Path(..., description="RFP ID"),
    session: AsyncSession = Depends(get_session),
) -> ComplianceGapSummary:
    result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = result.scalar_one_or_none()
    if not matrix:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance matrix not found for RFP {rfp_id}. Run analysis first.",
        )

    gaps = []
    mandatory_open = 0
    for req in matrix.requirements:
        is_addressed = req.get("is_addressed")
        status = req.get("status")
        if is_addressed or status == "addressed":
            continue
        if req.get("importance") == "mandatory":
            mandatory_open += 1
        gaps.append(ComplianceRequirementRead(**req))

    return ComplianceGapSummary(
        rfp_id=rfp_id,
        total_open=len(gaps),
        mandatory_open=mandatory_open,
        gaps=gaps,
    )


def _recalculate_matrix_counts(matrix: ComplianceMatrix) -> None:
    total = len(matrix.requirements)
    mandatory_count = 0
    addressed_count = 0
    for req in matrix.requirements:
        if req.get("importance") == "mandatory":
            mandatory_count += 1
        if req.get("is_addressed"):
            addressed_count += 1
    matrix.total_requirements = total
    matrix.mandatory_count = mandatory_count
    matrix.addressed_count = addressed_count


def _generate_requirement_id(existing: list[dict]) -> str:
    existing_ids = {req.get("id") for req in existing}
    index = len(existing) + 1
    while True:
        candidate = f"REQ-{index:03d}"
        if candidate not in existing_ids:
            return candidate
        index += 1


def _normalize_requirement_status(data: dict) -> dict:
    if data.get("is_addressed"):
        data["status"] = "addressed"
    elif data.get("status") == "addressed":
        data["is_addressed"] = True
    elif "is_addressed" in data and not data["is_addressed"] and data.get("status") == "addressed":
        data["status"] = "open"
    if data.get("status") is None:
        data.pop("status", None)
    return data


@router.post("/{rfp_id}/matrix", response_model=ComplianceMatrixRead)
async def add_compliance_requirement(
    rfp_id: int,
    requirement: ComplianceRequirementCreate,
    session: AsyncSession = Depends(get_session),
) -> ComplianceMatrixRead:
    """
    Add a new requirement to the compliance matrix.
    """
    result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = result.scalar_one_or_none()
    if not matrix:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance matrix not found for RFP {rfp_id}. Run analysis first.",
        )

    req_dict = requirement.model_dump()
    req_dict = _normalize_requirement_status(req_dict)
    if not req_dict.get("id"):
        req_dict["id"] = _generate_requirement_id(matrix.requirements)
    else:
        existing_ids = {req.get("id") for req in matrix.requirements}
        if req_dict["id"] in existing_ids:
            raise HTTPException(
                status_code=409,
                detail=f"Requirement ID {req_dict['id']} already exists.",
            )

    matrix.requirements.append(req_dict)
    flag_modified(matrix, "requirements")
    _recalculate_matrix_counts(matrix)
    matrix.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=matrix.rfp.user_id if matrix.rfp else None,
        entity_type="compliance_matrix",
        entity_id=matrix.id,
        action="compliance.requirement.added",
        metadata={"requirement_id": req_dict["id"], "rfp_id": rfp_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=matrix.rfp.user_id if matrix.rfp else None,
        event_type="compliance.requirement.added",
        payload={"rfp_id": rfp_id, "requirement_id": req_dict["id"]},
    )

    await session.commit()
    await session.refresh(matrix)

    requirements = [ComplianceRequirementRead(**req) for req in matrix.requirements]
    return ComplianceMatrixRead(
        id=matrix.id,
        rfp_id=matrix.rfp_id,
        requirements=requirements,
        total_requirements=matrix.total_requirements,
        mandatory_count=matrix.mandatory_count,
        addressed_count=matrix.addressed_count,
        extraction_confidence=matrix.extraction_confidence,
        created_at=matrix.created_at,
        updated_at=matrix.updated_at,
    )


@router.patch("/{rfp_id}/matrix/{requirement_id}", response_model=ComplianceMatrixRead)
async def update_compliance_requirement(
    rfp_id: int,
    requirement_id: str,
    update: ComplianceRequirementUpdate,
    session: AsyncSession = Depends(get_session),
) -> ComplianceMatrixRead:
    """
    Update a requirement in the compliance matrix.
    """
    result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = result.scalar_one_or_none()
    if not matrix:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance matrix not found for RFP {rfp_id}. Run analysis first.",
        )

    update_data = update.model_dump(exclude_unset=True)
    update_data = _normalize_requirement_status(update_data)
    found = False
    for req in matrix.requirements:
        if req.get("id") == requirement_id:
            req.update(update_data)
            found = True
            break

    flag_modified(matrix, "requirements")

    if not found:
        raise HTTPException(status_code=404, detail="Requirement not found")

    _recalculate_matrix_counts(matrix)
    matrix.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=matrix.rfp.user_id if matrix.rfp else None,
        entity_type="compliance_matrix",
        entity_id=matrix.id,
        action="compliance.requirement.updated",
        metadata={"requirement_id": requirement_id, "rfp_id": rfp_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=matrix.rfp.user_id if matrix.rfp else None,
        event_type="compliance.requirement.updated",
        payload={"rfp_id": rfp_id, "requirement_id": requirement_id},
    )

    await session.commit()
    await session.refresh(matrix)

    requirements = [ComplianceRequirementRead(**req) for req in matrix.requirements]
    return ComplianceMatrixRead(
        id=matrix.id,
        rfp_id=matrix.rfp_id,
        requirements=requirements,
        total_requirements=matrix.total_requirements,
        mandatory_count=matrix.mandatory_count,
        addressed_count=matrix.addressed_count,
        extraction_confidence=matrix.extraction_confidence,
        created_at=matrix.created_at,
        updated_at=matrix.updated_at,
    )


@router.delete("/{rfp_id}/matrix/{requirement_id}")
async def delete_compliance_requirement(
    rfp_id: int,
    requirement_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Delete a requirement from the compliance matrix.
    """
    result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = result.scalar_one_or_none()
    if not matrix:
        raise HTTPException(
            status_code=404,
            detail=f"Compliance matrix not found for RFP {rfp_id}. Run analysis first.",
        )

    original_len = len(matrix.requirements)
    matrix.requirements = [req for req in matrix.requirements if req.get("id") != requirement_id]
    flag_modified(matrix, "requirements")

    if len(matrix.requirements) == original_len:
        raise HTTPException(status_code=404, detail="Requirement not found")

    _recalculate_matrix_counts(matrix)
    matrix.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=matrix.rfp.user_id if matrix.rfp else None,
        entity_type="compliance_matrix",
        entity_id=matrix.id,
        action="compliance.requirement.deleted",
        metadata={"requirement_id": requirement_id, "rfp_id": rfp_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=matrix.rfp.user_id if matrix.rfp else None,
        event_type="compliance.requirement.deleted",
        payload={"rfp_id": rfp_id, "requirement_id": requirement_id},
    )

    await session.commit()

    return {"message": "Requirement deleted", "requirement_id": requirement_id}


@router.post("/{rfp_id}/filter")
async def trigger_killer_filter(
    rfp_id: int = Path(..., description="RFP ID to filter"),
    user_id: int | None = Query(
        None, description="User ID for profile lookup (optional if authenticated)"
    ),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Run the Killer Filter on an RFP.

    Uses Gemini 1.5 Flash to quickly determine if the user
    should pursue this opportunity based on their profile.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured",
        )

    # Verify RFP exists
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    resolved_user_id = resolve_user_id(user_id, current_user)

    # Queue the filter task
    task = run_killer_filter.delay(rfp_id=rfp_id, user_id=resolved_user_id)

    return {
        "task_id": task.id,
        "rfp_id": rfp_id,
        "message": "Killer Filter analysis started",
        "status": "processing",
    }
