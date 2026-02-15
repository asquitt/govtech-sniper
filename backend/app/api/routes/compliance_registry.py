"""Compliance control-evidence registry API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.audit import AuditEvent
from app.models.compliance_registry import (
    ComplianceControl,
    ComplianceEvidence,
    ControlEvidenceLink,
    ControlFramework,
    ControlStatus,
    EvidenceType,
)
from app.models.organization import OrganizationMember, OrgRole
from app.models.user import User
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/compliance-registry", tags=["Compliance Registry"])


# --- Schemas ---


class ControlCreate(BaseModel):
    framework: ControlFramework
    control_id: str
    title: str
    description: str | None = None
    status: ControlStatus = ControlStatus.NOT_STARTED
    implementation_notes: str | None = None


class ControlRead(BaseModel):
    id: int
    user_id: int
    framework: ControlFramework
    control_id: str
    title: str
    description: str | None
    status: ControlStatus
    implementation_notes: str | None
    assessor_notes: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ControlUpdate(BaseModel):
    status: ControlStatus | None = None
    implementation_notes: str | None = None
    assessor_notes: str | None = None


class EvidenceCreate(BaseModel):
    title: str
    evidence_type: EvidenceType
    description: str | None = None
    file_path: str | None = None
    url: str | None = None


class EvidenceRead(BaseModel):
    id: int
    user_id: int
    title: str
    evidence_type: EvidenceType
    description: str | None
    file_path: str | None
    url: str | None
    collected_at: datetime
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class LinkCreate(BaseModel):
    control_id: int
    evidence_id: int
    notes: str | None = None


async def _current_user_org_membership(
    user_id: int,
    db: AsyncSession,
) -> tuple[int, OrgRole] | None:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.organization_id:
        return None
    member = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == user.organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if not member:
        return None
    return user.organization_id, member.role


async def _require_org_membership(
    user_id: int,
    db: AsyncSession,
) -> tuple[int, OrgRole]:
    membership = await _current_user_org_membership(user_id, db)
    if not membership:
        raise HTTPException(403, "Organization scope unavailable for this user")
    return membership


# --- Control endpoints ---


@router.get("/controls", response_model=list[ControlRead])
async def list_controls(
    framework: ControlFramework | None = None,
    status: ControlStatus | None = None,
    scope: Literal["mine", "organization"] = Query("mine"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    query = select(ComplianceControl)
    if scope == "organization":
        org_id, _role = await _require_org_membership(user.id, db)
        query = query.where(ComplianceControl.organization_id == org_id)
    else:
        query = query.where(ComplianceControl.user_id == user.id)
    if framework:
        query = query.where(ComplianceControl.framework == framework)
    if status:
        query = query.where(ComplianceControl.status == status)
    query = query.offset(skip).limit(limit).order_by(ComplianceControl.control_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/controls", response_model=ControlRead, status_code=201)
async def create_control(
    body: ControlCreate,
    user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    membership = await _current_user_org_membership(user.id, db)
    control = ComplianceControl(
        user_id=user.id,
        organization_id=membership[0] if membership else None,
        **body.model_dump(),
    )
    db.add(control)
    db.add(
        AuditEvent(
            user_id=user.id,
            entity_type="compliance_control",
            action="compliance.registry.control_created",
            event_metadata={
                "control_id": body.control_id,
                "framework": body.framework.value,
            },
        )
    )
    await db.commit()
    await db.refresh(control)
    return control


@router.patch("/controls/{control_id}", response_model=ControlRead)
async def update_control(
    control_id: int,
    body: ControlUpdate,
    user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    membership = await _current_user_org_membership(user.id, db)
    query = select(ComplianceControl).where(ComplianceControl.id == control_id)
    if membership and membership[1] in (OrgRole.OWNER, OrgRole.ADMIN):
        query = query.where(
            or_(
                ComplianceControl.user_id == user.id,
                ComplianceControl.organization_id == membership[0],
            )
        )
    else:
        query = query.where(ComplianceControl.user_id == user.id)
    result = await db.execute(query)
    control = result.scalar_one_or_none()
    if not control:
        raise HTTPException(404, "Control not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(control, k, v)
    control.updated_at = datetime.utcnow()
    db.add(
        AuditEvent(
            user_id=user.id,
            entity_type="compliance_control",
            entity_id=control_id,
            action="compliance.registry.control_updated",
            event_metadata=body.model_dump(exclude_unset=True),
        )
    )
    await db.commit()
    await db.refresh(control)
    return control


# --- Evidence endpoints ---


@router.get("/evidence", response_model=list[EvidenceRead])
async def list_evidence(
    evidence_type: EvidenceType | None = None,
    scope: Literal["mine", "organization"] = Query("mine"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    query = select(ComplianceEvidence)
    if scope == "organization":
        org_id, _role = await _require_org_membership(user.id, db)
        query = query.where(ComplianceEvidence.organization_id == org_id)
    else:
        query = query.where(ComplianceEvidence.user_id == user.id)
    if evidence_type:
        query = query.where(ComplianceEvidence.evidence_type == evidence_type)
    query = query.offset(skip).limit(limit).order_by(ComplianceEvidence.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/evidence", response_model=EvidenceRead, status_code=201)
async def create_evidence(
    body: EvidenceCreate,
    user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    membership = await _current_user_org_membership(user.id, db)
    evidence = ComplianceEvidence(
        user_id=user.id,
        organization_id=membership[0] if membership else None,
        **body.model_dump(),
    )
    db.add(evidence)
    db.add(
        AuditEvent(
            user_id=user.id,
            entity_type="compliance_evidence",
            action="compliance.registry.evidence_created",
            event_metadata={
                "title": body.title,
                "type": body.evidence_type.value,
            },
        )
    )
    await db.commit()
    await db.refresh(evidence)
    return evidence


# --- Link endpoints ---


@router.post("/links", status_code=201)
async def link_evidence_to_control(
    body: LinkCreate,
    user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    membership = await _current_user_org_membership(user.id, db)

    control_query = select(ComplianceControl).where(ComplianceControl.id == body.control_id)
    if membership:
        control_query = control_query.where(
            or_(
                ComplianceControl.user_id == user.id,
                ComplianceControl.organization_id == membership[0],
            )
        )
    else:
        control_query = control_query.where(ComplianceControl.user_id == user.id)
    control = (await db.execute(control_query)).scalar_one_or_none()
    if not control:
        raise HTTPException(404, "Control not found")

    evidence_query = select(ComplianceEvidence).where(ComplianceEvidence.id == body.evidence_id)
    if membership:
        evidence_query = evidence_query.where(
            or_(
                ComplianceEvidence.user_id == user.id,
                ComplianceEvidence.organization_id == membership[0],
            )
        )
    else:
        evidence_query = evidence_query.where(ComplianceEvidence.user_id == user.id)
    evidence = (await db.execute(evidence_query)).scalar_one_or_none()
    if not evidence:
        raise HTTPException(404, "Evidence not found")

    if control.organization_id != evidence.organization_id and (
        control.user_id != user.id or evidence.user_id != user.id
    ):
        raise HTTPException(400, "Control and evidence must share organization scope")

    link = ControlEvidenceLink(
        control_id=body.control_id,
        evidence_id=body.evidence_id,
        linked_by_user_id=user.id,
        notes=body.notes,
    )
    db.add(link)
    db.add(
        AuditEvent(
            user_id=user.id,
            entity_type="control_evidence_link",
            action="compliance.registry.evidence_linked",
            event_metadata={
                "control_id": body.control_id,
                "evidence_id": body.evidence_id,
            },
        )
    )
    await db.commit()
    return {"status": "linked", "id": link.id}


@router.get("/controls/{control_id}/evidence", response_model=list[EvidenceRead])
async def get_control_evidence(
    control_id: int,
    user: UserAuth = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get all evidence linked to a specific control."""
    membership = await _current_user_org_membership(user.id, db)
    control_query = select(ComplianceControl).where(ComplianceControl.id == control_id)
    if membership:
        control_query = control_query.where(
            or_(
                ComplianceControl.user_id == user.id,
                ComplianceControl.organization_id == membership[0],
            )
        )
    else:
        control_query = control_query.where(ComplianceControl.user_id == user.id)
    control = (await db.execute(control_query)).scalar_one_or_none()
    if not control:
        raise HTTPException(404, "Control not found")

    evidence_scope_filter = (
        ComplianceEvidence.organization_id == control.organization_id
        if control.organization_id is not None
        else ComplianceEvidence.user_id == user.id
    )
    result = await db.execute(
        select(ComplianceEvidence)
        .join(ControlEvidenceLink, ControlEvidenceLink.evidence_id == ComplianceEvidence.id)
        .where(
            ControlEvidenceLink.control_id == control_id,
            evidence_scope_filter,
        )
    )
    return result.scalars().all()
