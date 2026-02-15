"""Readiness checkpoint services backed by the compliance evidence registry."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.compliance_registry import (
    CheckpointEvidenceStatus,
    ComplianceCheckpointEvidenceLink,
    ComplianceCheckpointSignoff,
    ComplianceEvidence,
)
from app.schemas.compliance import ComplianceReadinessCheckpoint


@dataclass(slots=True)
class CheckpointEvidenceSnapshot:
    """Joined checkpoint-evidence row with linked evidence metadata."""

    link: ComplianceCheckpointEvidenceLink
    evidence: ComplianceEvidence


async def list_checkpoint_evidence_snapshots(
    session: AsyncSession,
    *,
    organization_id: int,
    checkpoint_id: str,
) -> list[CheckpointEvidenceSnapshot]:
    """List evidence linked to a readiness checkpoint for an organization."""
    rows = (
        await session.execute(
            select(ComplianceCheckpointEvidenceLink, ComplianceEvidence)
            .join(
                ComplianceEvidence,
                ComplianceEvidence.id == ComplianceCheckpointEvidenceLink.evidence_id,
            )
            .where(
                ComplianceCheckpointEvidenceLink.organization_id == organization_id,
                ComplianceCheckpointEvidenceLink.checkpoint_id == checkpoint_id,
            )
            .order_by(ComplianceCheckpointEvidenceLink.created_at.desc())
        )
    ).all()
    return [CheckpointEvidenceSnapshot(link=row[0], evidence=row[1]) for row in rows]


async def get_checkpoint_signoff(
    session: AsyncSession,
    *,
    organization_id: int,
    checkpoint_id: str,
) -> ComplianceCheckpointSignoff | None:
    """Get latest assessor sign-off for a readiness checkpoint."""
    return (
        await session.execute(
            select(ComplianceCheckpointSignoff).where(
                ComplianceCheckpointSignoff.organization_id == organization_id,
                ComplianceCheckpointSignoff.checkpoint_id == checkpoint_id,
            )
        )
    ).scalar_one_or_none()


async def overlay_registry_readiness(
    session: AsyncSession,
    *,
    organization_id: int | None,
    checkpoints: list[ComplianceReadinessCheckpoint],
) -> list[ComplianceReadinessCheckpoint]:
    """Overlay dynamic evidence/sign-off telemetry onto static readiness checkpoints.

    If no organization scope is present or no registry data exists, the input checkpoints
    are returned unchanged to preserve backward compatibility.
    """
    if not organization_id:
        return checkpoints

    link_rows = (
        (
            await session.execute(
                select(ComplianceCheckpointEvidenceLink).where(
                    ComplianceCheckpointEvidenceLink.organization_id == organization_id
                )
            )
        )
        .scalars()
        .all()
    )
    signoffs = (
        (
            await session.execute(
                select(ComplianceCheckpointSignoff).where(
                    ComplianceCheckpointSignoff.organization_id == organization_id
                )
            )
        )
        .scalars()
        .all()
    )

    if not link_rows and not signoffs:
        return checkpoints

    links_by_checkpoint: dict[str, list[ComplianceCheckpointEvidenceLink]] = defaultdict(list)
    for link in link_rows:
        links_by_checkpoint[link.checkpoint_id].append(link)

    signoff_by_checkpoint = {signoff.checkpoint_id: signoff for signoff in signoffs}

    merged: list[ComplianceReadinessCheckpoint] = []
    for checkpoint in checkpoints:
        links = links_by_checkpoint.get(checkpoint.checkpoint_id, [])
        signoff = signoff_by_checkpoint.get(checkpoint.checkpoint_id)
        total = len(links)
        accepted = sum(1 for link in links if link.status == CheckpointEvidenceStatus.ACCEPTED)

        latest_update: datetime | None = None
        if links:
            latest_update = max(
                (link.reviewed_at or link.updated_at or link.created_at) for link in links
            )

        has_registry_data = bool(links) or signoff is not None
        base = checkpoint.model_dump()
        if has_registry_data:
            base["evidence_items_total"] = total
            base["evidence_items_ready"] = accepted
            base["evidence_source"] = "registry"
        else:
            base["evidence_source"] = "static"
        base["evidence_last_updated_at"] = latest_update
        base["assessor_signoff_status"] = signoff.status.value if signoff else None
        base["assessor_signoff_by"] = signoff.assessor_name if signoff else None
        base["assessor_signed_at"] = signoff.signed_at if signoff else None

        merged.append(ComplianceReadinessCheckpoint(**base))

    return merged
