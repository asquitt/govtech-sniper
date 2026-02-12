"""
Draft Routes - Section Generation & Status
"""

import re
import socket
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from kombu.exceptions import OperationalError
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user_optional, resolve_user_id
from app.config import settings
from app.database import get_session
from app.models.proposal import Proposal, ProposalSection, SectionStatus
from app.models.rfp import ComplianceMatrix
from app.schemas.proposal import (
    DraftRequest,
    DraftResponse,
    ExpandRequest,
    ProposalScorecard,
    ProposalSectionRead,
    RewriteRequest,
    SectionScoreRead,
)
from app.services.auth_service import UserAuth
from app.tasks.generation_tasks import (
    generate_all_sections,
    generate_proposal_section,
    refresh_context_cache,
)

router = APIRouter()
_SYNC_GENERATION_RESULTS: dict[str, dict] = {}
_GEMINI_RETRY_PATTERN = re.compile(
    r"retry in(?:\s+about)?\s+([0-9]+(?:\.[0-9]+)?)(?:\s*seconds|\s*s)?",
    re.IGNORECASE,
)

try:
    from google.api_core.exceptions import ResourceExhausted as GeminiResourceExhausted
except Exception:  # pragma: no cover - dependency may be absent in some environments
    GeminiResourceExhausted = None


def _raise_http_from_generation_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc

    message = str(exc)
    lowered = message.lower()
    is_quota_error = (
        (GeminiResourceExhausted is not None and isinstance(exc, GeminiResourceExhausted))
        or "quota exceeded" in lowered
        or "resourceexhausted" in lowered
        or "rate limit reached" in lowered
    )
    if is_quota_error:
        retry_after = None
        retry_match = _GEMINI_RETRY_PATTERN.search(message)
        if retry_match:
            retry_after = max(1, int(float(retry_match.group(1))))
        is_limit_zero = "limit: 0" in lowered
        if is_limit_zero:
            detail = (
                "Gemini quota is unavailable for the configured model. "
                "Enable billing or configure GEMINI_FALLBACK_MODELS."
            )
        else:
            detail = "Gemini API rate limit reached. Please retry shortly."
        if retry_after:
            if is_limit_zero:
                detail = (
                    "Gemini quota is unavailable for the configured model. "
                    "Enable billing or configure GEMINI_FALLBACK_MODELS. "
                    f"Retry in about {retry_after} seconds."
                )
            else:
                detail = f"Gemini API rate limit reached. Retry in about {retry_after} seconds."
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        raise HTTPException(status_code=429, detail=detail, headers=headers)

    raise exc


def _celery_broker_available() -> bool:
    """
    Best-effort broker probe for local/dev fallback when Redis/Celery is down.
    """
    broker_url = settings.celery_broker_url
    parsed = urlparse(broker_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return True

    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def _celery_worker_available() -> bool:
    """Best-effort worker probe for local/dev sync fallback behavior."""
    try:
        from app.tasks.celery_app import celery_app

        replies = celery_app.control.inspect(timeout=0.5).ping() or {}
        return len(replies) > 0
    except Exception:
        return False


async def _run_synchronous_generation(
    *,
    section: ProposalSection,
    session: AsyncSession,
    max_words: int,
    tone: str,
    additional_context: str | None = None,
) -> dict:
    """
    Local/dev synchronous generation fallback when Celery is unavailable.
    """
    from app.services.compliance_checker import AIQualityScorer
    from app.services.gemini_service import GeminiService

    gemini_service = GeminiService()
    requirement_text = section.requirement_text or section.title
    if section.writing_plan:
        requirement_text += f"\n\nWRITING PLAN:\n{section.writing_plan}"
    if additional_context:
        requirement_text += f"\n\nAdditional Context: {additional_context}"

    try:
        generated = await gemini_service.generate_section(
            requirement_text=requirement_text,
            section=section.section_number,
            category=None,
            max_words=max_words,
            tone=tone,
        )
    except Exception as exc:
        _raise_http_from_generation_error(exc)
    section.set_generated_content(generated)
    section.updated_at = datetime.utcnow()

    scorer = AIQualityScorer()
    scores = scorer.score_content(generated.clean_text, section.requirement_text)
    section.quality_score = scores["overall_score"]
    section.quality_breakdown = scores

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == section.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if proposal:
        completed_result = await session.execute(
            select(ProposalSection).where(
                ProposalSection.proposal_id == proposal.id,
                ProposalSection.status.in_([SectionStatus.GENERATED, SectionStatus.APPROVED]),
            )
        )
        proposal.completed_sections = len(completed_result.scalars().all())

    await session.commit()

    return {
        "section_id": section.id,
        "requirement_id": section.requirement_id,
        "word_count": section.word_count or 0,
        "generated_at": section.generated_at.isoformat() if section.generated_at else None,
    }


@router.post("/proposals/{proposal_id}/generate-from-matrix")
async def generate_sections_from_matrix(
    proposal_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Auto-generate proposal sections from the RFP's compliance matrix.

    Creates a section for each mandatory and evaluated requirement.
    """
    # Get proposal and RFP
    result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    # Get compliance matrix
    matrix_result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == proposal.rfp_id)
    )
    matrix = matrix_result.scalar_one_or_none()

    if not matrix:
        raise HTTPException(
            status_code=400,
            detail="RFP has no compliance matrix. Run analysis first.",
        )

    existing_sections_result = await session.execute(
        select(ProposalSection).where(ProposalSection.proposal_id == proposal_id)
    )
    existing_sections = existing_sections_result.scalars().all()
    existing_requirement_ids = {s.requirement_id for s in existing_sections if s.requirement_id}
    display_order_start = len(existing_sections)

    # Create sections for requirements not already represented on the proposal
    sections_created = 0
    for req in matrix.requirements:
        requirement_id = req.get("id")
        if requirement_id and requirement_id in existing_requirement_ids:
            continue

        section = ProposalSection(
            proposal_id=proposal_id,
            title=f"Response to {req.get('section', 'Requirement')}",
            section_number=f"R{display_order_start + sections_created + 1:03d}",
            requirement_id=requirement_id,
            requirement_text=req.get("requirement_text"),
            display_order=display_order_start + sections_created,
        )
        session.add(section)
        sections_created += 1

    proposal.total_sections = len(existing_sections) + sections_created
    await session.commit()

    return {
        "proposal_id": proposal_id,
        "sections_created": sections_created,
        "message": f"Created {sections_created} sections from compliance matrix",
    }


@router.post("/sections/{section_id}/rewrite", response_model=ProposalSectionRead)
async def rewrite_section(
    section_id: int,
    request: RewriteRequest,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """Rewrite a section's content with a new tone or custom instructions."""
    resolved_user_id = resolve_user_id(user_id, current_user)

    section_result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == section.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Section not found")

    content = section.final_content or (
        section.get_generated_content().clean_text if section.generated_content else None
    )
    if not content:
        raise HTTPException(status_code=400, detail="Section has no content to rewrite")

    from app.services.gemini_service import GeminiService

    gemini = GeminiService()
    try:
        generated = await gemini.rewrite_section(
            content=content,
            requirement_text=section.requirement_text or section.title,
            tone=request.tone,
            instructions=request.instructions,
        )
    except Exception as exc:
        _raise_http_from_generation_error(exc)

    section.set_generated_content(generated)
    section.updated_at = datetime.utcnow()

    from app.services.compliance_checker import AIQualityScorer

    scorer = AIQualityScorer()
    scores = scorer.score_content(generated.clean_text, section.requirement_text)
    section.quality_score = scores["overall_score"]
    section.quality_breakdown = scores

    await session.commit()
    await session.refresh(section)
    return ProposalSectionRead.model_validate(section)


@router.post("/sections/{section_id}/expand", response_model=ProposalSectionRead)
async def expand_section(
    section_id: int,
    request: ExpandRequest,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """Expand a section's content with more detail."""
    resolved_user_id = resolve_user_id(user_id, current_user)

    section_result = await session.execute(
        select(ProposalSection).where(ProposalSection.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == section.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Section not found")

    content = section.final_content or (
        section.get_generated_content().clean_text if section.generated_content else None
    )
    if not content:
        raise HTTPException(status_code=400, detail="Section has no content to expand")

    from app.services.gemini_service import GeminiService

    gemini = GeminiService()
    try:
        generated = await gemini.expand_section(
            content=content,
            requirement_text=section.requirement_text or section.title,
            target_words=request.target_words,
            focus_area=request.focus_area,
        )
    except Exception as exc:
        _raise_http_from_generation_error(exc)

    section.set_generated_content(generated)
    section.updated_at = datetime.utcnow()

    from app.services.compliance_checker import AIQualityScorer

    scorer = AIQualityScorer()
    scores = scorer.score_content(generated.clean_text, section.requirement_text)
    section.quality_score = scores["overall_score"]
    section.quality_breakdown = scores

    await session.commit()
    await session.refresh(section)
    return ProposalSectionRead.model_validate(section)


@router.get("/proposals/{proposal_id}/generation-progress")
async def get_generation_progress(
    proposal_id: int,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get aggregate generation progress for all sections in a proposal."""
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    sections_result = await session.execute(
        select(ProposalSection).where(ProposalSection.proposal_id == proposal_id)
    )
    sections = sections_result.scalars().all()

    total = len(sections)
    counts: dict[str, int] = {
        "pending": 0,
        "generating": 0,
        "generated": 0,
        "editing": 0,
        "approved": 0,
    }
    for s in sections:
        status_key = s.status.value if hasattr(s.status, "value") else s.status
        if status_key in counts:
            counts[status_key] += 1

    completed = counts["generated"] + counts["editing"] + counts["approved"]
    return {
        "proposal_id": proposal_id,
        "total": total,
        "completed": completed,
        "pending": counts["pending"],
        "generating": counts["generating"],
        "generated": counts["generated"],
        "editing": counts["editing"],
        "approved": counts["approved"],
        "completion_percentage": round((completed / total * 100) if total > 0 else 0, 1),
    }


@router.post("/{requirement_id}", response_model=DraftResponse)
async def generate_section_draft(
    requirement_id: str = Path(..., description="Requirement ID from compliance matrix"),
    request: DraftRequest = None,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> DraftResponse:
    """
    Generate a draft response for a specific requirement.

    This is the core RAG endpoint that:
    1. Retrieves the user's Knowledge Base documents
    2. Uses Gemini 1.5 Pro's context caching for efficient lookups
    3. Generates compliant text with source citations

    **Citation Format:** Generated text includes [[Source: filename.pdf, Page XX]] markers.
    """
    if not settings.gemini_api_key and not settings.mock_ai:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured",
        )

    # Parse request
    if request is None:
        request = DraftRequest(requirement_id=requirement_id)

    resolved_user_id = resolve_user_id(user_id, current_user)

    # Find the section for this requirement that belongs to the requesting user
    section_query = (
        select(ProposalSection)
        .join(Proposal, ProposalSection.proposal_id == Proposal.id)
        .where(
            ProposalSection.requirement_id == requirement_id,
            Proposal.user_id == resolved_user_id,
        )
        .order_by(desc(ProposalSection.created_at))
        .limit(1)
    )
    if request.rfp_id is not None:
        section_query = section_query.where(Proposal.rfp_id == request.rfp_id)

    result = await session.execute(section_query)
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(
            status_code=404,
            detail=f"No section found for requirement {requirement_id}. Create proposal sections first.",
        )

    # Fall back to sync generation in local/dev when broker or worker is unavailable.
    should_fallback_sync = (settings.debug or settings.mock_ai) and (
        not _celery_broker_available() or not _celery_worker_available()
    )
    if should_fallback_sync:
        sync_task_id = f"sync-{section.id}-{int(datetime.utcnow().timestamp())}"
        try:
            sync_result = await _run_synchronous_generation(
                section=section,
                session=session,
                max_words=request.max_words,
                tone=request.tone,
                additional_context=request.additional_context,
            )
        except Exception as exc:
            _raise_http_from_generation_error(exc)
        _SYNC_GENERATION_RESULTS[sync_task_id] = sync_result
        return DraftResponse(
            task_id=sync_task_id,
            requirement_id=requirement_id,
            section_id=section.id,
            message="Draft generation completed synchronously.",
            status="completed",
        )

    # Queue generation task
    try:
        task = generate_proposal_section.delay(
            section_id=section.id,
            user_id=resolved_user_id,
            max_words=request.max_words,
            tone=request.tone,
            additional_context=request.additional_context,
        )
    except OperationalError as exc:
        if settings.debug or settings.mock_ai:
            sync_task_id = f"sync-{section.id}-{int(datetime.utcnow().timestamp())}"
            try:
                sync_result = await _run_synchronous_generation(
                    section=section,
                    session=session,
                    max_words=request.max_words,
                    tone=request.tone,
                    additional_context=request.additional_context,
                )
            except Exception as sync_exc:
                _raise_http_from_generation_error(sync_exc)
            _SYNC_GENERATION_RESULTS[sync_task_id] = sync_result
            return DraftResponse(
                task_id=sync_task_id,
                requirement_id=requirement_id,
                section_id=section.id,
                message="Draft generation completed synchronously.",
                status="completed",
            )
        raise HTTPException(
            status_code=503,
            detail="Draft generation worker unavailable. Please try again shortly.",
        ) from exc

    return DraftResponse(
        task_id=task.id,
        requirement_id=requirement_id,
        section_id=section.id,
        message="Draft generation started",
        status="generating",
    )


@router.post("/proposals/{proposal_id}/generate-all")
async def generate_all_proposal_sections(
    proposal_id: int,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    max_words: int = Query(500, ge=100, le=2000),
    tone: str = Query("professional", pattern="^(professional|technical|executive)$"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Generate all pending sections for a proposal.

    Queues generation tasks for each section that hasn't been written yet.
    """
    if not settings.gemini_api_key and not settings.mock_ai:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    # Verify proposal exists
    result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    resolved_user_id = resolve_user_id(user_id, current_user)

    # Queue batch generation
    task = generate_all_sections.delay(
        proposal_id=proposal_id,
        user_id=resolved_user_id,
        max_words_per_section=max_words,
        tone=tone,
    )

    return {
        "task_id": task.id,
        "proposal_id": proposal_id,
        "message": "Batch generation queued",
        "status": "processing",
    }


@router.post("/refresh-cache")
async def trigger_cache_refresh(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    ttl_hours: int = Query(24, ge=1, le=168, description="Cache TTL in hours"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
) -> dict:
    """
    Refresh the Gemini context cache for a user's Knowledge Base.

    Call this after uploading new documents to ensure they're included
    in the AI's context during generation.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    task = refresh_context_cache.delay(
        user_id=resolved_user_id,
        ttl_hours=ttl_hours,
    )

    return {
        "task_id": task.id,
        "message": "Cache refresh started",
        "ttl_hours": ttl_hours,
    }


@router.get("/{task_id}/status")
async def get_generation_status(task_id: str) -> dict:
    """
    Get the status of a generation task.
    """
    sync_result = _SYNC_GENERATION_RESULTS.get(task_id)
    if sync_result is not None:
        return {
            "task_id": task_id,
            "status": "completed",
            "result": sync_result,
        }

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
                "status": "completed",
                "result": result.get(),
            }
        else:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(result.result),
            }
    else:
        return {
            "task_id": task_id,
            "status": normalize_status(result),
        }


# =============================================================================
# Quality Scorecard
# =============================================================================


@router.get("/proposals/{proposal_id}/scorecard", response_model=ProposalScorecard)
async def get_proposal_scorecard(
    proposal_id: int = Path(...),
    user_id: int | None = Query(default=None),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
):
    """Aggregated quality scorecard for all sections in a proposal."""
    uid = resolve_user_id(user_id, current_user)

    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id, Proposal.user_id == uid)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    sections_result = await session.execute(
        select(ProposalSection)
        .where(ProposalSection.proposal_id == proposal_id)
        .order_by(ProposalSection.display_order)
    )
    sections = list(sections_result.scalars().all())

    section_scores = []
    scored_values = []
    for s in sections:
        has_content = bool(s.final_content or s.generated_content)
        section_scores.append(
            SectionScoreRead(
                section_id=s.id,
                section_number=s.section_number,
                title=s.title,
                quality_score=s.quality_score,
                quality_breakdown=s.quality_breakdown,
                word_count=s.word_count,
                has_content=has_content,
            )
        )
        if s.quality_score is not None:
            scored_values.append(s.quality_score)

    overall = round(sum(scored_values) / len(scored_values), 1) if scored_values else None
    pink_team_ready = overall is not None and overall >= 70 and all(v >= 50 for v in scored_values)

    return ProposalScorecard(
        proposal_id=proposal_id,
        proposal_title=proposal.title,
        overall_score=overall,
        sections_scored=len(scored_values),
        sections_total=len(sections),
        pink_team_ready=pink_team_ready,
        section_scores=section_scores,
    )
