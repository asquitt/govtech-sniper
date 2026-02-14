"""
RFP Sniper - RFP Management Routes
===================================
CRUD operations for RFPs.
"""

import re
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_current_user_optional, resolve_user_id
from app.database import get_session
from app.models.opportunity_snapshot import SAMOpportunitySnapshot
from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP, ComplianceMatrix, RFPStatus
from app.schemas.rfp import (
    AmendmentImpactSignal,
    AmendmentSectionRemediation,
    RFPCreate,
    RFPListItem,
    RFPRead,
    RFPUpdate,
    SAMOpportunityAmendmentImpact,
    SAMOpportunitySnapshotDiff,
    SAMOpportunitySnapshotRead,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.cache_service import cache_clear_prefix, cache_get, cache_set
from app.services.embedding_service import (
    compose_rfp_text,
    delete_entity_embeddings,
    index_entity,
)
from app.services.snapshot_service import build_snapshot_summary, diff_snapshot_summaries
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/rfps", tags=["RFPs"])
logger = structlog.get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")

_AMENDMENT_IMPACT_PROFILES: dict[str, dict[str, str | list[str]]] = {
    "response_deadline": {
        "impact_area": "timeline",
        "severity": "high",
        "actions": [
            "Update schedule, staffing ramp, and delivery dates impacted by the new deadline.",
            "Re-validate review calendar and approval gates against the updated amendment timeline.",
        ],
    },
    "posted_date": {
        "impact_area": "timeline",
        "severity": "medium",
        "actions": [
            "Reconfirm pursuit timeline assumptions tied to amendment publication timing.",
        ],
    },
    "naics_code": {
        "impact_area": "eligibility",
        "severity": "high",
        "actions": [
            "Re-check NAICS alignment and update qualification assertions where referenced.",
            "Validate teaming/vehicle assumptions still satisfy revised NAICS posture.",
        ],
    },
    "set_aside": {
        "impact_area": "eligibility",
        "severity": "high",
        "actions": [
            "Re-validate set-aside eligibility claims and subcontracting strategy references.",
            "Update compliance matrix entries for socioeconomic requirements.",
        ],
    },
    "rfp_type": {
        "impact_area": "eligibility",
        "severity": "medium",
        "actions": [
            "Adjust proposal framing and compliance rationale to match solicitation type changes.",
        ],
    },
    "resource_links_count": {
        "impact_area": "attachments",
        "severity": "medium",
        "actions": [
            "Review newly added attachments and map them to affected sections and requirements.",
        ],
    },
    "resource_links_hash": {
        "impact_area": "attachments",
        "severity": "medium",
        "actions": [
            "Review attachment deltas and trace source updates into section evidence links.",
        ],
    },
    "description_hash": {
        "impact_area": "scope",
        "severity": "high",
        "actions": [
            "Reconcile technical narrative with amended scope language before next review cycle.",
        ],
    },
    "description_length": {
        "impact_area": "scope",
        "severity": "medium",
        "actions": [
            "Re-read amended narrative and update sections where requirement interpretation changed.",
        ],
    },
}


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _tokenize(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


def _impact_profile(field: str) -> tuple[str, str, list[str]]:
    profile = _AMENDMENT_IMPACT_PROFILES.get(field)
    if not profile:
        return (
            "scope",
            "low",
            [
                "Review this section for amendment alignment and update discriminator language as needed."
            ],
        )
    return (
        str(profile["impact_area"]),
        str(profile["severity"]),
        list(profile["actions"]),  # type: ignore[arg-type]
    )


def _impact_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


@router.get("", response_model=list[RFPListItem])
async def list_rfps(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    status: RFPStatus | None = Query(None, description="Filter by status"),
    qualified_only: bool = Query(False, description="Only show qualified RFPs"),
    source_type: str | None = Query(None, description="Filter by source type"),
    jurisdiction: str | None = Query(None, description="Filter by jurisdiction"),
    currency: str | None = Query(None, description="Filter by currency code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> list[RFPListItem]:
    """
    List RFPs for a user with optional filtering.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)
    cache_key = (
        f"rfps:list:{resolved_user_id}:{status}:{qualified_only}:{source_type}:"
        f"{jurisdiction}:{currency}:{skip}:{limit}"
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    query = select(RFP).where(RFP.user_id == resolved_user_id)

    if status:
        query = query.where(RFP.status == status)

    if qualified_only:
        query = query.where(RFP.is_qualified == True)

    if source_type:
        source_values = [item.strip() for item in source_type.split(",") if item.strip()]
        if len(source_values) == 1:
            query = query.where(RFP.source_type == source_values[0])
        elif source_values:
            query = query.where(RFP.source_type.in_(source_values))

    if jurisdiction:
        jurisdiction_values = [item.strip() for item in jurisdiction.split(",") if item.strip()]
        if len(jurisdiction_values) == 1:
            query = query.where(RFP.jurisdiction == jurisdiction_values[0])
        elif jurisdiction_values:
            query = query.where(RFP.jurisdiction.in_(jurisdiction_values))

    if currency:
        currency_values = [item.strip().upper() for item in currency.split(",") if item.strip()]
        if len(currency_values) == 1:
            query = query.where(RFP.currency == currency_values[0])
        elif currency_values:
            query = query.where(RFP.currency.in_(currency_values))

    query = query.order_by(RFP.created_at.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    rfps = result.scalars().all()
    payload = [RFPListItem.model_validate(rfp).model_dump() for rfp in rfps]
    await cache_set(cache_key, payload)
    return payload


@router.get("/{rfp_id}", response_model=RFPRead)
async def get_rfp(
    rfp_id: int = Path(..., description="RFP ID"),
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Get detailed RFP information.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    return RFPRead.model_validate(rfp)


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


@router.post("", response_model=RFPRead)
async def create_rfp(
    rfp_data: RFPCreate,
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Manually create an RFP record.

    Use this for RFPs not found via SAM.gov or imported from other sources.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Check for duplicate solicitation number within the same user scope.
    existing = await session.execute(
        select(RFP).where(
            RFP.user_id == resolved_user_id,
            RFP.solicitation_number == rfp_data.solicitation_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"RFP with solicitation number {rfp_data.solicitation_number} already exists",
        )

    rfp = RFP(
        user_id=resolved_user_id,
        **rfp_data.model_dump(),
    )
    session.add(rfp)
    await session.flush()
    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="rfp",
        entity_id=rfp.id,
        action="rfp.created",
        metadata={"title": rfp.title, "solicitation_number": rfp.solicitation_number},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="rfp.created",
        payload={
            "rfp_id": rfp.id,
            "title": rfp.title,
            "solicitation_number": rfp.solicitation_number,
            "agency": rfp.agency,
            "status": rfp.status,
        },
    )
    try:
        await index_entity(
            session,
            user_id=resolved_user_id,
            entity_type="rfp",
            entity_id=rfp.id,
            text=compose_rfp_text(
                title=rfp.title,
                solicitation_number=rfp.solicitation_number,
                agency=rfp.agency,
                sub_agency=rfp.sub_agency,
                naics_code=rfp.naics_code,
                set_aside=rfp.set_aside,
                description=rfp.description,
                full_text=rfp.full_text,
                summary=rfp.summary,
            ),
        )
    except Exception as exc:
        logger.warning("RFP semantic index update failed", rfp_id=rfp.id, error=str(exc))
    await session.commit()
    await session.refresh(rfp)
    await cache_clear_prefix(f"rfps:list:{resolved_user_id}:")

    return RFPRead.model_validate(rfp)


@router.patch("/{rfp_id}", response_model=RFPRead)
async def update_rfp(
    rfp_id: int,
    update_data: RFPUpdate,
    session: AsyncSession = Depends(get_session),
) -> RFPRead:
    """
    Update RFP fields.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(rfp, field, value)

    from datetime import datetime

    rfp.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=rfp.user_id,
        entity_type="rfp",
        entity_id=rfp.id,
        action="rfp.updated",
        metadata={"updated_fields": list(update_dict.keys())},
    )
    await dispatch_webhook_event(
        session,
        user_id=rfp.user_id,
        event_type="rfp.updated",
        payload={
            "rfp_id": rfp.id,
            "updated_fields": list(update_dict.keys()),
        },
    )
    try:
        await index_entity(
            session,
            user_id=rfp.user_id,
            entity_type="rfp",
            entity_id=rfp.id,
            text=compose_rfp_text(
                title=rfp.title,
                solicitation_number=rfp.solicitation_number,
                agency=rfp.agency,
                sub_agency=rfp.sub_agency,
                naics_code=rfp.naics_code,
                set_aside=rfp.set_aside,
                description=rfp.description,
                full_text=rfp.full_text,
                summary=rfp.summary,
            ),
        )
    except Exception as exc:
        logger.warning("RFP semantic reindex failed", rfp_id=rfp.id, error=str(exc))
    await session.commit()
    await session.refresh(rfp)
    await cache_clear_prefix(f"rfps:list:{rfp.user_id}:")

    return RFPRead.model_validate(rfp)


@router.delete("/{rfp_id}")
async def delete_rfp(
    rfp_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Delete an RFP and all related data.
    """
    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")

    await log_audit_event(
        session,
        user_id=rfp.user_id,
        entity_type="rfp",
        entity_id=rfp.id,
        action="rfp.deleted",
        metadata={"title": rfp.title, "solicitation_number": rfp.solicitation_number},
    )
    await dispatch_webhook_event(
        session,
        user_id=rfp.user_id,
        event_type="rfp.deleted",
        payload={
            "rfp_id": rfp.id,
            "title": rfp.title,
            "solicitation_number": rfp.solicitation_number,
        },
    )
    try:
        await delete_entity_embeddings(
            session,
            user_id=rfp.user_id,
            entity_type="rfp",
            entity_id=rfp.id,
        )
    except Exception as exc:
        logger.warning("RFP embedding cleanup failed", rfp_id=rfp.id, error=str(exc))
    await session.delete(rfp)
    await session.commit()
    await cache_clear_prefix(f"rfps:list:{rfp.user_id}:")

    return {"message": f"RFP {rfp_id} deleted"}


@router.post("/{rfp_id}/match-score")
async def compute_match_score(
    rfp_id: int = Path(..., description="RFP ID"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Compute AI match score for an RFP against the user's profile."""
    from app.models.user import UserProfile
    from app.services.matching_service import OpportunityMatchingService

    result = await session.execute(select(RFP).where(RFP.id == rfp_id))
    rfp = result.scalar_one_or_none()
    if not rfp:
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

    from datetime import datetime

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


@router.post("/{rfp_id}/upload-pdf")
async def upload_rfp_pdf(
    rfp_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upload a PDF for an RFP.

    **TODO:** Implement file upload handling.
    This endpoint will:
    1. Accept a PDF file upload
    2. Extract text using pdfplumber
    3. Store the text in rfp.full_text
    4. Trigger analysis
    """
    # Placeholder for file upload implementation
    raise HTTPException(
        status_code=501,
        detail="PDF upload not yet implemented",
    )


@router.get("/stats/summary")
async def get_rfp_stats(
    user_id: int | None = Query(None, description="User ID (optional if authenticated)"),
    current_user: UserAuth | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get summary statistics for a user's RFPs.
    """
    from sqlalchemy import func

    resolved_user_id = resolve_user_id(user_id, current_user)

    # Total count
    total_result = await session.execute(
        select(func.count(RFP.id)).where(RFP.user_id == resolved_user_id)
    )
    total = total_result.scalar()

    # By status
    status_result = await session.execute(
        select(RFP.status, func.count(RFP.id))
        .where(RFP.user_id == resolved_user_id)
        .group_by(RFP.status)
    )
    by_status = {status.value: count for status, count in status_result.all()}

    # Qualified vs not
    qualified_result = await session.execute(
        select(func.count(RFP.id)).where(RFP.user_id == resolved_user_id, RFP.is_qualified == True)
    )
    qualified = qualified_result.scalar()

    disqualified_result = await session.execute(
        select(func.count(RFP.id)).where(RFP.user_id == resolved_user_id, RFP.is_qualified == False)
    )
    disqualified = disqualified_result.scalar()

    return {
        "total": total,
        "by_status": by_status,
        "qualified": qualified,
        "disqualified": disqualified,
        "pending_filter": total - (qualified or 0) - (disqualified or 0),
    }
