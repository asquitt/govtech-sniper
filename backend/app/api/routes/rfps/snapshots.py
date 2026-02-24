"""
RFP Routes - Snapshots & Amendment Impact
==========================================
SAM.gov snapshot listing, diffing, amendment impact analysis, and match scoring.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import check_rate_limit, get_current_user
from app.database import get_session
from app.models.opportunity_snapshot import SAMOpportunitySnapshot
from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP, ComplianceMatrix
from app.schemas.rfp import (
    AmendmentImpactSignal,
    AmendmentSectionRemediation,
    SAMOpportunityAmendmentImpact,
    SAMOpportunitySnapshotDiff,
    SAMOpportunitySnapshotRead,
)
from app.services.auth_service import UserAuth
from app.services.snapshot_service import build_snapshot_summary, diff_snapshot_summaries

from .helpers import _as_text, _impact_level, _impact_profile, _tokenize

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/{rfp_id}/snapshots", response_model=list[SAMOpportunitySnapshotRead])
async def list_rfp_snapshots(
    rfp_id: int = Path(..., description="RFP ID"),
    include_raw: bool = Query(False, description="Include raw SAM.gov payload"),
    limit: int = Query(20, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SAMOpportunitySnapshotRead]:
    """
    List SAM.gov opportunity snapshots for an RFP.
    """
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    result = await session.execute(
        select(SAMOpportunitySnapshot)
        .where(SAMOpportunitySnapshot.rfp_id == rfp_id)
        .order_by(desc(SAMOpportunitySnapshot.fetched_at))
        .limit(limit)
    )
    snapshots = result.scalars().all()

    response = []
    for snapshot in snapshots:
        summary = build_snapshot_summary(snapshot.raw_payload)
        response.append(
            SAMOpportunitySnapshotRead(
                id=snapshot.id,
                notice_id=snapshot.notice_id,
                solicitation_number=snapshot.solicitation_number,
                rfp_id=snapshot.rfp_id,
                user_id=snapshot.user_id,
                fetched_at=snapshot.fetched_at,
                posted_date=snapshot.posted_date,
                response_deadline=snapshot.response_deadline,
                raw_hash=snapshot.raw_hash,
                summary=summary,
                raw_payload=snapshot.raw_payload if include_raw else None,
            )
        )

    return response


@router.get("/{rfp_id}/snapshots/diff", response_model=SAMOpportunitySnapshotDiff)
async def diff_rfp_snapshots(
    rfp_id: int = Path(..., description="RFP ID"),
    from_snapshot_id: int | None = Query(
        None, description="Snapshot ID to diff from (defaults to previous)"
    ),
    to_snapshot_id: int | None = Query(
        None, description="Snapshot ID to diff to (defaults to latest)"
    ),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SAMOpportunitySnapshotDiff:
    """
    Diff two snapshots for an RFP.
    """
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    if from_snapshot_id and to_snapshot_id:
        snapshots_result = await session.execute(
            select(SAMOpportunitySnapshot).where(
                SAMOpportunitySnapshot.id.in_([from_snapshot_id, to_snapshot_id]),
                SAMOpportunitySnapshot.rfp_id == rfp_id,
            )
        )
        snapshots = {s.id: s for s in snapshots_result.scalars().all()}
        from_snapshot = snapshots.get(from_snapshot_id)
        to_snapshot = snapshots.get(to_snapshot_id)
    else:
        snapshots_result = await session.execute(
            select(SAMOpportunitySnapshot)
            .where(SAMOpportunitySnapshot.rfp_id == rfp_id)
            .order_by(desc(SAMOpportunitySnapshot.fetched_at))
            .limit(2)
        )
        snapshots = snapshots_result.scalars().all()
        if len(snapshots) < 2:
            raise HTTPException(
                status_code=404,
                detail="Not enough snapshots to diff",
            )
        to_snapshot = snapshots[0]
        from_snapshot = snapshots[1]

    if not from_snapshot or not to_snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found for this RFP")

    summary_from = build_snapshot_summary(from_snapshot.raw_payload)
    summary_to = build_snapshot_summary(to_snapshot.raw_payload)
    changes = diff_snapshot_summaries(summary_from, summary_to)

    return SAMOpportunitySnapshotDiff(
        from_snapshot_id=from_snapshot.id,
        to_snapshot_id=to_snapshot.id,
        changes=changes,
        summary_from=summary_from,
        summary_to=summary_to,
    )


@router.get(
    "/{rfp_id}/snapshots/amendment-impact",
    response_model=SAMOpportunityAmendmentImpact,
)
async def get_snapshot_amendment_impact(
    rfp_id: int = Path(..., description="RFP ID"),
    from_snapshot_id: int | None = Query(
        None, description="Snapshot ID to diff from (defaults to previous)"
    ),
    to_snapshot_id: int | None = Query(
        None, description="Snapshot ID to diff to (defaults to latest)"
    ),
    top_n: int = Query(12, ge=1, le=50),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SAMOpportunityAmendmentImpact:
    """
    Build an amendment impact map with section-level remediation recommendations.
    """
    diff = await diff_rfp_snapshots(
        rfp_id=rfp_id,
        from_snapshot_id=from_snapshot_id,
        to_snapshot_id=to_snapshot_id,
        current_user=current_user,
        session=session,
    )

    proposals = list(
        (
            await session.execute(
                select(Proposal)
                .where(Proposal.rfp_id == rfp_id)
                .order_by(desc(Proposal.updated_at))
            )
        )
        .scalars()
        .all()
    )
    proposal_ids = [proposal.id for proposal in proposals if proposal.id is not None]

    sections: list[ProposalSection] = []
    if proposal_ids:
        sections = list(
            (
                await session.execute(
                    select(ProposalSection)
                    .where(ProposalSection.proposal_id.in_(proposal_ids))
                    .order_by(ProposalSection.display_order.asc())
                )
            )
            .scalars()
            .all()
        )

    matrix = (
        await session.execute(select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id))
    ).scalar_one_or_none()
    requirements_by_id: dict[str, str] = {}
    if matrix:
        for requirement in matrix.requirements:
            requirement_id = _as_text(requirement.get("id")).strip().lower()
            requirement_text = _as_text(requirement.get("requirement_text"))
            if requirement_id and requirement_text:
                requirements_by_id[requirement_id] = requirement_text.lower()

    change_token_map: dict[str, set[str]] = {}
    all_change_tokens: set[str] = set()
    signals: list[AmendmentImpactSignal] = []
    severity_order = {"low": 1, "medium": 2, "high": 3}

    for change in diff.changes:
        impact_area, severity, actions = _impact_profile(change.field)
        tokens = (
            _tokenize(change.field.replace("_", " "))
            | _tokenize(_as_text(change.from_value))
            | _tokenize(_as_text(change.to_value))
        )
        change_token_map[change.field] = tokens
        all_change_tokens.update(tokens)
        signals.append(
            AmendmentImpactSignal(
                field=change.field,
                from_value=change.from_value,
                to_value=change.to_value,
                impact_area=impact_area,
                severity=severity,
                recommended_actions=actions,
            )
        )

    proposals_by_id = {proposal.id: proposal for proposal in proposals if proposal.id is not None}
    impacted_sections: list[AmendmentSectionRemediation] = []

    for section in sections:
        section_text = " ".join(
            part
            for part in [
                section.title,
                section.section_number,
                section.requirement_id,
                section.requirement_text,
                section.final_content,
                (section.generated_content or {}).get("clean_text")
                if isinstance(section.generated_content, dict)
                else None,
            ]
            if part
        ).lower()
        section_tokens = _tokenize(section_text)

        matched_fields: list[str] = []
        recommended_actions: set[str] = set()
        rationale_parts: list[str] = []
        score = 0.0

        for signal in signals:
            tokens = change_token_map.get(signal.field, set())
            overlap = section_tokens.intersection(tokens)
            signal_score = min(len(overlap) * 8.0, 32.0) if overlap else 0.0

            if signal.impact_area == "timeline" and any(
                token in section_text
                for token in (
                    "timeline",
                    "schedule",
                    "milestone",
                    "phase",
                    "transition",
                    "delivery",
                )
            ):
                signal_score += 20.0
            if signal.impact_area == "eligibility" and any(
                token in section_text
                for token in (
                    "naics",
                    "set-aside",
                    "small business",
                    "8(a)",
                    "hubzone",
                    "sdvosb",
                    "wosb",
                    "vehicle",
                )
            ):
                signal_score += 24.0
            if signal.impact_area == "scope" and any(
                token in section_text
                for token in (
                    "technical",
                    "approach",
                    "scope",
                    "requirement",
                    "performance",
                    "task",
                    "compliance",
                )
            ):
                signal_score += 18.0
            if signal.impact_area == "attachments" and any(
                token in section_text
                for token in ("attachment", "appendix", "reference", "evidence", "document")
            ):
                signal_score += 18.0

            if signal_score <= 0:
                continue

            matched_fields.append(signal.field)
            score += signal_score
            recommended_actions.update(signal.recommended_actions)
            if overlap:
                overlap_preview = ", ".join(sorted(overlap)[:3])
                rationale_parts.append(f"{signal.field} overlap ({overlap_preview})")
            else:
                rationale_parts.append(f"{signal.field} semantic alignment")

        requirement_id = _as_text(section.requirement_id).strip().lower()
        requirement_text = requirements_by_id.get(requirement_id, "")
        if requirement_text and any(token in requirement_text for token in all_change_tokens):
            score += 12.0
            rationale_parts.append("linked compliance requirement text changed context")

        score = min(score, 100.0)
        if score < 25.0:
            continue

        section_status = (
            section.status.value if hasattr(section.status, "value") else str(section.status)
        )
        impact_level = _impact_level(score)
        proposal = proposals_by_id.get(section.proposal_id)
        if not proposal:
            continue

        matched_unique = sorted(set(matched_fields))
        field_summary = ", ".join(matched_unique[:3]) if matched_unique else "amendment deltas"
        impacted_sections.append(
            AmendmentSectionRemediation(
                proposal_id=proposal.id,  # type: ignore[arg-type]
                proposal_title=proposal.title,
                section_id=section.id,  # type: ignore[arg-type]
                section_number=section.section_number,
                section_title=section.title,
                section_status=section_status,
                impact_score=round(score, 1),
                impact_level=impact_level,
                matched_change_fields=matched_unique,
                rationale="; ".join(rationale_parts[:3])
                if rationale_parts
                else "Section likely impacted.",
                proposed_patch=(
                    f"Reconcile section language with amendment fields: {field_summary}. "
                    f"Re-run compliance checks before approval."
                ),
                recommended_actions=sorted(recommended_actions),
                approval_required=impact_level in {"high", "medium"},
            )
        )

    impacted_sections.sort(
        key=lambda item: (
            -item.impact_score,
            -severity_order.get(item.impact_level, 1),
            item.proposal_id,
            item.section_id,
        )
    )
    impacted_sections = impacted_sections[:top_n]

    max_signal_severity = max(
        (severity_order.get(signal.severity, 1) for signal in signals),
        default=1,
    )
    max_section_impact = max((item.impact_score for item in impacted_sections), default=0.0)
    if max_signal_severity >= 3 and max_section_impact >= 70:
        amendment_risk_level = "high"
    elif max_signal_severity >= 2 or max_section_impact >= 40 or len(diff.changes) >= 3:
        amendment_risk_level = "medium"
    else:
        amendment_risk_level = "low"

    return SAMOpportunityAmendmentImpact(
        rfp_id=rfp_id,
        from_snapshot_id=diff.from_snapshot_id,
        to_snapshot_id=diff.to_snapshot_id,
        generated_at=datetime.utcnow(),
        amendment_risk_level=amendment_risk_level,
        changed_fields=[signal.field for signal in signals],
        signals=signals,
        impacted_sections=impacted_sections,
        summary={
            "changed_fields": len(signals),
            "impacted_sections": len(impacted_sections),
            "high_impact_sections": sum(
                1 for item in impacted_sections if item.impact_level == "high"
            ),
            "medium_impact_sections": sum(
                1 for item in impacted_sections if item.impact_level == "medium"
            ),
            "low_impact_sections": sum(
                1 for item in impacted_sections if item.impact_level == "low"
            ),
            "risk_level": amendment_risk_level,
        },
        approval_workflow=[
            "1) Proposal manager reviews high/medium impact sections and confirms assignment owners.",
            "2) Section owners apply remediation updates and attach amendment evidence references.",
            "3) Compliance reviewer validates updates and approves closure before submission gate.",
        ],
    )


@router.post("/{rfp_id}/match-score", dependencies=[Depends(check_rate_limit)])
async def compute_match_score(
    rfp_id: int = Path(..., description="RFP ID"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Compute AI match score for an RFP against the user's profile."""
    from app.models.user import UserProfile
    from app.services.matching_service import OpportunityMatchingService

    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()
    if not rfp or rfp.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == rfp.user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=400, detail="User profile not found. Create a profile first."
        )

    service = OpportunityMatchingService()
    match = await service.score_opportunity(rfp, profile)

    rfp.match_score = match.overall_score
    rfp.match_reasoning = match.reasoning
    rfp.match_details = match.to_dict()

    rfp.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfp)

    return {
        "rfp_id": rfp.id,
        "match_score": match.overall_score,
        "category_scores": match.category_scores,
        "strengths": match.strengths,
        "gaps": match.gaps,
        "reasoning": match.reasoning,
    }
