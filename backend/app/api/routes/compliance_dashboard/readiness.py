"""
Compliance Dashboard - Readiness Routes
========================================
Readiness programs, checkpoints, evidence management, signoffs,
GovCloud profile, SOC2 readiness, and 3PAO package export.
"""

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.audit import AuditEvent
from app.models.compliance_registry import (
    CheckpointEvidenceStatus,
    CheckpointSignoffStatus,
    ComplianceCheckpointEvidenceLink,
    ComplianceCheckpointSignoff,
    ComplianceEvidence,
)
from app.models.organization import OrgRole
from app.schemas.compliance import (
    ComplianceCheckpointEvidenceCreate,
    ComplianceCheckpointEvidenceRead,
    ComplianceCheckpointEvidenceUpdate,
    ComplianceCheckpointSignoffRead,
    ComplianceCheckpointSignoffWrite,
    ComplianceReadinessCheckpointResponse,
    ComplianceReadinessResponse,
    GovCloudDeploymentProfile,
    SOC2ReadinessResponse,
)
from app.services.auth_service import UserAuth
from app.services.compliance_readiness_service import (
    get_checkpoint_signoff,
    list_checkpoint_evidence_snapshots,
    overlay_registry_readiness,
)
from app.services.export_signing import signed_headers

from .helpers import (
    build_govcloud_profile,
    build_soc2_readiness,
    build_trust_center_profile,
    checkpoint_exists,
    current_user_with_org,
    is_org_admin,
    readiness_checkpoints,
    readiness_programs,
    serialize_checkpoint_evidence,
)

router = APIRouter()


@router.get("/readiness", response_model=ComplianceReadinessResponse)
async def readiness_status(
    current_user: UserAuth = Depends(get_current_user),
) -> dict:
    """Marketplace and certification readiness tracker."""
    now = datetime.utcnow()
    return {
        "programs": readiness_programs(),
        "last_updated": now.isoformat(),
    }


@router.get(
    "/readiness-checkpoints",
    response_model=ComplianceReadinessCheckpointResponse,
)
async def readiness_checkpoints_endpoint(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceReadinessCheckpointResponse:
    """Execution checkpoints across FedRAMP/CMMC/GovCloud readiness tracks."""
    _user, org, _member = await current_user_with_org(current_user, session)
    checkpoints = await overlay_registry_readiness(
        session,
        organization_id=org.id if org else None,
        checkpoints=readiness_checkpoints(),
    )
    return ComplianceReadinessCheckpointResponse(
        checkpoints=checkpoints,
        generated_at=datetime.utcnow(),
    )


@router.get(
    "/readiness-checkpoints/{checkpoint_id}/evidence",
    response_model=list[ComplianceCheckpointEvidenceRead],
)
async def checkpoint_evidence_list(
    checkpoint_id: str,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ComplianceCheckpointEvidenceRead]:
    """List evidence linked to a readiness checkpoint for the current organization."""
    _user, org, member = await current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    snapshots = await list_checkpoint_evidence_snapshots(
        session,
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
    )
    return [
        serialize_checkpoint_evidence(snapshot, checkpoint_id=checkpoint_id)
        for snapshot in snapshots
    ]


@router.post(
    "/readiness-checkpoints/{checkpoint_id}/evidence",
    response_model=ComplianceCheckpointEvidenceRead,
    status_code=201,
)
async def checkpoint_evidence_create(
    checkpoint_id: str,
    payload: ComplianceCheckpointEvidenceCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointEvidenceRead:
    """Link an evidence artifact to a readiness checkpoint (org admin only)."""
    _user, org, member = await current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not is_org_admin(member):
        raise HTTPException(403, "Admin access required")
    if not checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    evidence = (
        await session.execute(
            select(ComplianceEvidence).where(
                ComplianceEvidence.id == payload.evidence_id,
                ComplianceEvidence.organization_id == org.id,
            )
        )
    ).scalar_one_or_none()
    if not evidence:
        raise HTTPException(404, "Evidence not found in organization scope")

    link = ComplianceCheckpointEvidenceLink(
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
        evidence_id=payload.evidence_id,
        status=CheckpointEvidenceStatus(payload.status or CheckpointEvidenceStatus.SUBMITTED.value),
        notes=payload.notes,
        linked_by_user_id=current_user.id,
    )
    session.add(link)
    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance_checkpoint",
            entity_id=org.id,
            action="compliance.readiness_checkpoint.evidence_linked",
            event_metadata={
                "organization_id": org.id,
                "checkpoint_id": checkpoint_id,
                "evidence_id": payload.evidence_id,
                "status": link.status.value,
            },
        )
    )
    await session.commit()
    await session.refresh(link)

    return ComplianceCheckpointEvidenceRead(
        link_id=link.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
        evidence_id=evidence.id,  # type: ignore[arg-type]
        title=evidence.title,
        evidence_type=evidence.evidence_type.value,
        description=evidence.description,
        file_path=evidence.file_path,
        url=evidence.url,
        collected_at=evidence.collected_at,
        expires_at=evidence.expires_at,
        status=link.status.value,  # type: ignore[arg-type]
        notes=link.notes,
        reviewer_user_id=link.reviewer_user_id,
        reviewer_notes=link.reviewer_notes,
        reviewed_at=link.reviewed_at,
        linked_at=link.created_at,
    )


@router.patch(
    "/readiness-checkpoints/{checkpoint_id}/evidence/{link_id}",
    response_model=ComplianceCheckpointEvidenceRead,
)
async def checkpoint_evidence_update(
    checkpoint_id: str,
    link_id: int,
    payload: ComplianceCheckpointEvidenceUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointEvidenceRead:
    """Review/update checkpoint evidence status (org admin only)."""
    _user, org, member = await current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not is_org_admin(member):
        raise HTTPException(403, "Admin access required")
    if not checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    link = (
        await session.execute(
            select(ComplianceCheckpointEvidenceLink).where(
                ComplianceCheckpointEvidenceLink.id == link_id,
                ComplianceCheckpointEvidenceLink.organization_id == org.id,
                ComplianceCheckpointEvidenceLink.checkpoint_id == checkpoint_id,
            )
        )
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Checkpoint evidence link not found")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "status" in updates:
        link.status = CheckpointEvidenceStatus(updates["status"])
    if "reviewer_notes" in updates:
        link.reviewer_notes = updates["reviewer_notes"]
    link.reviewer_user_id = current_user.id
    link.reviewed_at = datetime.utcnow()
    link.updated_at = datetime.utcnow()
    session.add(link)
    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance_checkpoint",
            entity_id=org.id,
            action="compliance.readiness_checkpoint.evidence_updated",
            event_metadata={
                "organization_id": org.id,
                "checkpoint_id": checkpoint_id,
                "link_id": link_id,
                "updates": updates,
            },
        )
    )
    await session.commit()

    evidence = (
        await session.execute(
            select(ComplianceEvidence).where(ComplianceEvidence.id == link.evidence_id)
        )
    ).scalar_one_or_none()
    if not evidence:
        raise HTTPException(404, "Linked evidence not found")

    return ComplianceCheckpointEvidenceRead(
        link_id=link.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
        evidence_id=evidence.id,  # type: ignore[arg-type]
        title=evidence.title,
        evidence_type=evidence.evidence_type.value,
        description=evidence.description,
        file_path=evidence.file_path,
        url=evidence.url,
        collected_at=evidence.collected_at,
        expires_at=evidence.expires_at,
        status=link.status.value,  # type: ignore[arg-type]
        notes=link.notes,
        reviewer_user_id=link.reviewer_user_id,
        reviewer_notes=link.reviewer_notes,
        reviewed_at=link.reviewed_at,
        linked_at=link.created_at,
    )


@router.get(
    "/readiness-checkpoints/{checkpoint_id}/signoff",
    response_model=ComplianceCheckpointSignoffRead,
)
async def checkpoint_signoff_get(
    checkpoint_id: str,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointSignoffRead:
    """Read assessor sign-off status for a checkpoint."""
    _user, org, member = await current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    signoff = await get_checkpoint_signoff(
        session,
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
    )
    if not signoff:
        return ComplianceCheckpointSignoffRead(
            checkpoint_id=checkpoint_id,
            status=CheckpointSignoffStatus.PENDING.value,  # type: ignore[arg-type]
            assessor_name="Pending assessor assignment",
            assessor_org=None,
            notes=None,
            signed_by_user_id=None,
            signed_at=None,
            updated_at=datetime.utcnow(),
        )
    return ComplianceCheckpointSignoffRead(
        checkpoint_id=checkpoint_id,
        status=signoff.status.value,  # type: ignore[arg-type]
        assessor_name=signoff.assessor_name,
        assessor_org=signoff.assessor_org,
        notes=signoff.notes,
        signed_by_user_id=signoff.signed_by_user_id,
        signed_at=signoff.signed_at,
        updated_at=signoff.updated_at,
    )


@router.put(
    "/readiness-checkpoints/{checkpoint_id}/signoff",
    response_model=ComplianceCheckpointSignoffRead,
)
async def checkpoint_signoff_upsert(
    checkpoint_id: str,
    payload: ComplianceCheckpointSignoffWrite,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ComplianceCheckpointSignoffRead:
    """Create/update checkpoint assessor sign-off (org admin only)."""
    _user, org, member = await current_user_with_org(current_user, session)
    if not org or not member:
        raise HTTPException(403, "Organization membership required")
    if not is_org_admin(member):
        raise HTTPException(403, "Admin access required")
    if not checkpoint_exists(checkpoint_id):
        raise HTTPException(404, "Checkpoint not found")

    signoff = await get_checkpoint_signoff(
        session,
        organization_id=org.id,  # type: ignore[arg-type]
        checkpoint_id=checkpoint_id,
    )
    if not signoff:
        signoff = ComplianceCheckpointSignoff(
            organization_id=org.id,  # type: ignore[arg-type]
            checkpoint_id=checkpoint_id,
            status=CheckpointSignoffStatus(payload.status),
            assessor_name=payload.assessor_name,
            assessor_org=payload.assessor_org,
            notes=payload.notes,
            signed_by_user_id=current_user.id,
            signed_at=datetime.utcnow()
            if payload.status != CheckpointSignoffStatus.PENDING.value
            else None,
        )
    else:
        signoff.status = CheckpointSignoffStatus(payload.status)
        signoff.assessor_name = payload.assessor_name
        signoff.assessor_org = payload.assessor_org
        signoff.notes = payload.notes
        signoff.signed_by_user_id = current_user.id
        signoff.signed_at = (
            datetime.utcnow() if payload.status != CheckpointSignoffStatus.PENDING.value else None
        )
        signoff.updated_at = datetime.utcnow()

    session.add(signoff)
    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance_checkpoint",
            entity_id=org.id,
            action="compliance.readiness_checkpoint.signoff_updated",
            event_metadata={
                "organization_id": org.id,
                "checkpoint_id": checkpoint_id,
                "status": payload.status,
                "assessor_name": payload.assessor_name,
            },
        )
    )
    await session.commit()
    await session.refresh(signoff)

    return ComplianceCheckpointSignoffRead(
        checkpoint_id=checkpoint_id,
        status=signoff.status.value,  # type: ignore[arg-type]
        assessor_name=signoff.assessor_name,
        assessor_org=signoff.assessor_org,
        notes=signoff.notes,
        signed_by_user_id=signoff.signed_by_user_id,
        signed_at=signoff.signed_at,
        updated_at=signoff.updated_at,
    )


@router.get("/govcloud-profile", response_model=GovCloudDeploymentProfile)
async def govcloud_profile(
    current_user: UserAuth = Depends(get_current_user),
) -> GovCloudDeploymentProfile:
    """GovCloud deployment execution profile with phase-level readiness."""
    return build_govcloud_profile(datetime.utcnow())


@router.get("/soc2-readiness", response_model=SOC2ReadinessResponse)
async def soc2_readiness(
    current_user: UserAuth = Depends(get_current_user),
) -> SOC2ReadinessResponse:
    """SOC 2 Type II execution tracker with milestone and domain-level posture."""
    return build_soc2_readiness(datetime.utcnow())


@router.get("/three-pao-package")
async def export_three_pao_package(
    signed: bool = Query(False),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Download readiness package for 3PAO onboarding and audit planning."""
    _user, org, member = await current_user_with_org(current_user, session)
    can_manage_policy = bool(member and member.role in (OrgRole.OWNER, OrgRole.ADMIN))
    now = datetime.utcnow()
    try:
        trust_profile = build_trust_center_profile(
            organization=org,
            can_manage_policy=can_manage_policy,
        )
        programs = readiness_programs()
        checkpoints = await overlay_registry_readiness(
            session,
            organization_id=org.id if org else None,
            checkpoints=readiness_checkpoints(),
        )
        third_party_checkpoints = [
            checkpoint for checkpoint in checkpoints if checkpoint.third_party_required
        ]
        soc2_profile = build_soc2_readiness(now)
        govcloud = build_govcloud_profile(now)

        payload: dict[str, Any] = {
            "generated_at": now.isoformat(),
            "generated_by_user_id": current_user.id,
            "organization_id": org.id if org else None,
            "readiness_programs": programs,
            "checkpoint_summary": {
                "total": len(checkpoints),
                "third_party_required": len(third_party_checkpoints),
                "evidence_items_ready": sum(c.evidence_items_ready for c in checkpoints),
                "evidence_items_total": sum(c.evidence_items_total for c in checkpoints),
            },
            "checkpoints": [checkpoint.model_dump(mode="json") for checkpoint in checkpoints],
            "three_pao_focus_checkpoints": [
                checkpoint.model_dump(mode="json") for checkpoint in third_party_checkpoints
            ],
            "govcloud_profile": govcloud.model_dump(mode="json"),
            "soc2_profile": soc2_profile.model_dump(mode="json"),
            "trust_center": trust_profile.model_dump(mode="json"),
            "controls_in_scope": [
                "FedRAMP Moderate baseline deltas",
                "CMMC Level 2 practice evidence map",
                "GovCloud boundary and identity controls",
                "SOC 2 Type II trust criteria execution status",
            ],
        }
    except Exception as exc:
        session.add(
            AuditEvent(
                user_id=current_user.id,
                entity_type="compliance",
                entity_id=org.id if org else None,
                action="compliance.3pao_package.export_failed",
                event_metadata={
                    "organization_id": org.id if org else None,
                    "signed": signed,
                    "error": str(exc),
                },
            )
        )
        await session.commit()
        raise
    filename = f"three_pao_readiness_package_{now.strftime('%Y%m%d')}.json"

    session.add(
        AuditEvent(
            user_id=current_user.id,
            entity_type="compliance",
            entity_id=org.id if org else None,
            action="compliance.3pao_package.exported",
            event_metadata={
                "organization_id": org.id if org else None,
                "third_party_checkpoints": len(third_party_checkpoints),
                "signed": signed,
            },
        )
    )
    await session.commit()

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    headers.update(
        signed_headers(
            json.dumps(payload, sort_keys=True).encode("utf-8"),
            enabled=signed,
        )
    )
    return JSONResponse(content=payload, headers=headers)
