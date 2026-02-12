"""
RFP Sniper - Onboarding Routes
================================
Track user onboarding progress through the first-proposal wizard.
"""

from datetime import datetime
from statistics import median

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import JSON, Column, Field, SQLModel, select

from app.api.deps import UserAuth, get_current_user, resolve_user_id
from app.database import get_session
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.proposal import Proposal
from app.models.rfp import RFP

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =============================================================================
# Model
# =============================================================================


class OnboardingProgress(SQLModel, table=True):
    """Tracks user onboarding step completion."""

    __tablename__ = "onboarding_progress"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    completed_steps: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    step_timestamps: dict = Field(default_factory=dict, sa_column=Column(JSON))
    is_dismissed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Step definitions
# =============================================================================

ONBOARDING_STEPS = [
    {
        "id": "create_account",
        "title": "Create your account",
        "description": "Sign up and set up your profile",
        "href": "/settings",
    },
    {
        "id": "upload_rfp",
        "title": "Upload your first RFP",
        "description": "Upload a solicitation document to get started",
        "href": "/opportunities",
    },
    {
        "id": "analyze_rfp",
        "title": "Analyze an RFP",
        "description": "Run AI analysis on your uploaded solicitation",
        "href": "/analysis",
    },
    {
        "id": "upload_documents",
        "title": "Build your Knowledge Base",
        "description": "Upload resumes, past performance, and capability docs",
        "href": "/knowledge-base",
    },
    {
        "id": "create_proposal",
        "title": "Create a proposal",
        "description": "Generate your first AI-assisted proposal draft",
        "href": "/proposals",
    },
    {
        "id": "export_proposal",
        "title": "Export a proposal",
        "description": "Export to Word or PDF for submission",
        "href": "/proposals",
    },
]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/progress")
async def get_progress(
    user_id: int | None = Query(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get onboarding progress with auto-detection of completed steps."""
    uid = resolve_user_id(user_id, current_user)

    progress = (
        await session.execute(select(OnboardingProgress).where(OnboardingProgress.user_id == uid))
    ).scalar_one_or_none()

    if not progress:
        now_iso = datetime.utcnow().isoformat()
        progress = OnboardingProgress(
            user_id=uid,
            completed_steps=["create_account"],
            step_timestamps={"create_account": now_iso},
        )
        session.add(progress)
        await session.flush()

    # Auto-detect completed steps from actual data
    completed = set(progress.completed_steps)
    timestamps = dict(progress.step_timestamps or {})
    now_iso = datetime.utcnow().isoformat()
    if "create_account" not in timestamps:
        timestamps["create_account"] = now_iso
    completed.add("create_account")  # Always true if they're calling this

    rfp_count = (
        await session.execute(select(func.count()).where(RFP.user_id == uid))
    ).scalar() or 0
    if rfp_count > 0:
        completed.add("upload_rfp")
        if "upload_rfp" not in timestamps:
            timestamps["upload_rfp"] = now_iso

    analyzed_count = (
        await session.execute(
            select(func.count()).where(RFP.user_id == uid, RFP.status == "analyzed")
        )
    ).scalar() or 0
    if analyzed_count > 0:
        completed.add("analyze_rfp")
        if "analyze_rfp" not in timestamps:
            timestamps["analyze_rfp"] = now_iso

    doc_count = (
        await session.execute(select(func.count()).where(KnowledgeBaseDocument.user_id == uid))
    ).scalar() or 0
    if doc_count > 0:
        completed.add("upload_documents")
        if "upload_documents" not in timestamps:
            timestamps["upload_documents"] = now_iso

    proposal_count = (
        await session.execute(select(func.count()).where(Proposal.user_id == uid))
    ).scalar() or 0
    if proposal_count > 0:
        completed.add("create_proposal")
        if "create_proposal" not in timestamps:
            timestamps["create_proposal"] = now_iso

    # Update stored progress
    progress.completed_steps = sorted(completed)
    progress.step_timestamps = timestamps
    progress.updated_at = datetime.utcnow()
    session.add(progress)
    await session.commit()

    # Build response
    steps = []
    for step_def in ONBOARDING_STEPS:
        is_done = step_def["id"] in completed
        steps.append(
            {
                "id": step_def["id"],
                "title": step_def["title"],
                "description": step_def["description"],
                "href": step_def["href"],
                "completed": is_done,
                "completed_at": progress.updated_at.isoformat() if is_done else None,
            }
        )

    return {
        "steps": steps,
        "completed_count": len(completed),
        "total_steps": len(ONBOARDING_STEPS),
        "is_complete": len(completed) >= len(ONBOARDING_STEPS),
        "is_dismissed": progress.is_dismissed,
        "step_timestamps": progress.step_timestamps,
    }


@router.post("/steps/{step_id}/complete")
async def mark_step_complete(
    step_id: str,
    user_id: int | None = Query(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Manually mark a step as complete."""
    uid = resolve_user_id(user_id, current_user)

    valid_ids = {s["id"] for s in ONBOARDING_STEPS}
    if step_id not in valid_ids:
        return {"error": "Invalid step ID"}

    progress = (
        await session.execute(select(OnboardingProgress).where(OnboardingProgress.user_id == uid))
    ).scalar_one_or_none()

    if not progress:
        progress = OnboardingProgress(user_id=uid, completed_steps=[], step_timestamps={})
        session.add(progress)

    completed = set(progress.completed_steps)
    completed.add(step_id)
    progress.completed_steps = sorted(completed)

    timestamps = dict(progress.step_timestamps or {})
    if step_id not in timestamps:
        timestamps[step_id] = datetime.utcnow().isoformat()
    progress.step_timestamps = timestamps
    progress.updated_at = datetime.utcnow()
    session.add(progress)
    await session.commit()

    return {"status": "completed", "step_id": step_id}


@router.post("/dismiss")
async def dismiss_onboarding(
    user_id: int | None = Query(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Dismiss the onboarding wizard."""
    uid = resolve_user_id(user_id, current_user)

    progress = (
        await session.execute(select(OnboardingProgress).where(OnboardingProgress.user_id == uid))
    ).scalar_one_or_none()

    if not progress:
        progress = OnboardingProgress(user_id=uid, completed_steps=[], is_dismissed=True)
    else:
        progress.is_dismissed = True

    session.add(progress)
    await session.commit()

    return {"status": "dismissed"}


@router.get("/activation-metrics")
async def get_activation_metrics(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Activation telemetry for admin dashboards."""
    if current_user.tier not in ("admin", "enterprise"):
        raise HTTPException(status_code=403, detail="Admin access required")

    all_progress = (await session.execute(select(OnboardingProgress))).scalars().all()
    total_users = len(all_progress)
    step_ids = [s["id"] for s in ONBOARDING_STEPS]
    fully_activated = sum(
        1 for p in all_progress if len(set(p.completed_steps) & set(step_ids)) >= len(step_ids)
    )

    step_completion_counts: dict[str, int] = {sid: 0 for sid in step_ids}
    time_deltas: list[float] = []
    for p in all_progress:
        completed = set(p.completed_steps)
        for sid in step_ids:
            if sid in completed:
                step_completion_counts[sid] += 1
        ts = p.step_timestamps or {}
        if "create_account" in ts and "create_proposal" in ts:
            try:
                t0 = datetime.fromisoformat(ts["create_account"])
                t1 = datetime.fromisoformat(ts["create_proposal"])
                delta_hours = (t1 - t0).total_seconds() / 3600
                if delta_hours >= 0:
                    time_deltas.append(delta_hours)
            except (ValueError, TypeError):
                pass

    step_completion_rates = {
        sid: round(count / total_users * 100, 1) if total_users else 0.0
        for sid, count in step_completion_counts.items()
    }
    median_time = round(median(time_deltas), 2) if time_deltas else None

    return {
        "total_users": total_users,
        "fully_activated": fully_activated,
        "step_completion_rates": step_completion_rates,
        "median_time_to_first_proposal_hours": median_time,
    }
