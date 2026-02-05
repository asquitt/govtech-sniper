"""
RFP Sniper - Draft Generation Routes
=====================================
Endpoints for proposal section generation with RAG.
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from sqlmodel import select, func

from app.database import get_session
from app.api.deps import get_current_user_optional, resolve_user_id
from app.services.auth_service import UserAuth
from app.models.proposal import (
    Proposal,
    ProposalSection,
    SectionStatus,
    SubmissionPackage,
    SubmissionPackageStatus,
    SectionEvidence,
)
from app.models.knowledge_base import KnowledgeBaseDocument, DocumentChunk
from app.models.rfp import RFP, ComplianceMatrix
from app.schemas.proposal import (
    DraftRequest,
    DraftResponse,
    ProposalCreate,
    ProposalRead,
    ProposalSectionCreate,
    ProposalSectionRead,
    ProposalSectionUpdate,
    SubmissionPackageCreate,
    SubmissionPackageRead,
    SubmissionPackageUpdate,
    SectionEvidenceCreate,
    SectionEvidenceRead,
)
from app.tasks.generation_tasks import (
    generate_proposal_section,
    generate_all_sections,
    refresh_context_cache,
)
from app.config import settings
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/draft", tags=["Draft Generation"])


@router.get("/proposals", response_model=List[ProposalRead])
async def list_proposals(
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    rfp_id: Optional[int] = Query(None, description="Filter by RFP ID"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> List[ProposalRead]:
    """
    List proposals for a user.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)
    query = select(Proposal).where(Proposal.user_id == resolved_user_id)
    if rfp_id is not None:
        query = query.where(Proposal.rfp_id == rfp_id)

    result = await session.execute(query.order_by(Proposal.created_at.desc()))
    proposals = result.scalars().all()
    return [ProposalRead.from_orm_with_completion(p) for p in proposals]


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
async def get_proposal(
    proposal_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProposalRead:
    """
    Get a proposal by id.
    """
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return ProposalRead.from_orm_with_completion(proposal)


@router.post("/proposals", response_model=ProposalRead)
async def create_proposal(
    proposal: ProposalCreate,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalRead:
    """
    Create a new proposal for an RFP.
    
    This initializes the proposal structure. Use the sections
    endpoints to add content.
    """
    # Verify RFP exists
    result = await session.execute(
        select(RFP).where(RFP.id == proposal.rfp_id)
    )
    rfp = result.scalar_one_or_none()
    
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {proposal.rfp_id} not found")
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Create proposal
    new_proposal = Proposal(
        user_id=resolved_user_id,
        rfp_id=proposal.rfp_id,
        title=proposal.title,
    )
    session.add(new_proposal)
    await session.commit()
    await session.refresh(new_proposal)
    
    return ProposalRead.from_orm_with_completion(new_proposal)


@router.post("/proposals/{proposal_id}/sections", response_model=ProposalSectionRead)
async def create_section(
    proposal_id: int,
    section: ProposalSectionCreate,
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """
    Add a section to a proposal.
    
    Sections can be created manually or auto-generated from
    the compliance matrix.
    """
    # Verify proposal exists
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")
    
    # Create section
    new_section = ProposalSection(
        proposal_id=proposal_id,
        title=section.title,
        section_number=section.section_number,
        requirement_id=section.requirement_id,
        requirement_text=section.requirement_text,
        display_order=section.display_order,
    )
    session.add(new_section)
    
    # Update proposal section count
    proposal.total_sections += 1
    
    await session.commit()
    await session.refresh(new_section)
    
    return ProposalSectionRead.model_validate(new_section)


@router.get("/proposals/{proposal_id}/sections", response_model=List[ProposalSectionRead])
async def list_sections(
    proposal_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    status: Optional[SectionStatus] = Query(None, description="Filter by section status"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> List[ProposalSectionRead]:
    """
    List proposal sections.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    query = select(ProposalSection).where(ProposalSection.proposal_id == proposal_id)
    if status:
        query = query.where(ProposalSection.status == status)

    result = await session.execute(query.order_by(ProposalSection.display_order))
    sections = result.scalars().all()
    return [ProposalSectionRead.model_validate(section) for section in sections]


@router.get("/sections/{section_id}", response_model=ProposalSectionRead)
async def get_section(
    section_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """
    Get a proposal section by id.
    """
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

    return ProposalSectionRead.model_validate(section)


@router.patch("/sections/{section_id}", response_model=ProposalSectionRead)
async def update_section(
    section_id: int,
    update: ProposalSectionUpdate,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> ProposalSectionRead:
    """
    Update a proposal section (final content, status, metadata).
    """
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

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)

    if "final_content" in update_data and update_data.get("final_content"):
        section.word_count = len(update_data["final_content"].split())
        if "status" not in update_data:
            section.status = SectionStatus.EDITING

    section.updated_at = datetime.utcnow()

    # Update compliance matrix addressed status if mapped to requirement
    if section.requirement_id:
        matrix_result = await session.execute(
            select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == proposal.rfp_id)
        )
        matrix = matrix_result.scalar_one_or_none()
        if matrix:
            for req in matrix.requirements:
                if req.get("id") == section.requirement_id:
                    if update_data.get("status") == SectionStatus.APPROVED:
                        req["is_addressed"] = True
                    elif "final_content" in update_data and update_data.get("final_content"):
                        req["is_addressed"] = True
                    elif update_data.get("status") == SectionStatus.PENDING:
                        req["is_addressed"] = False
                    break
            # Recalculate counts
            matrix.total_requirements = len(matrix.requirements)
            matrix.mandatory_count = len(
                [r for r in matrix.requirements if r.get("importance") == "mandatory"]
            )
            matrix.addressed_count = len(
                [r for r in matrix.requirements if r.get("is_addressed")]
            )
            matrix.updated_at = datetime.utcnow()

    # Update proposal completion counts
    completed_result = await session.execute(
        select(ProposalSection).where(
            ProposalSection.proposal_id == proposal.id,
            ProposalSection.status.in_([
                SectionStatus.GENERATED,
                SectionStatus.APPROVED,
            ]),
        )
    )
    proposal.completed_sections = len(completed_result.scalars().all())
    proposal.updated_at = datetime.utcnow()

    # Version tracking
    if "final_content" in update_data or "status" in update_data:
        from app.models.proposal import ProposalVersion, ProposalVersionType, SectionVersion

        max_version_result = await session.execute(
            select(func.max(SectionVersion.version_number)).where(
                SectionVersion.section_id == section.id
            )
        )
        max_version = max_version_result.scalar() or 0
        section_version = SectionVersion(
            section_id=section.id,
            user_id=resolved_user_id,
            version_number=max_version + 1,
            content=section.final_content or "",
            word_count=section.word_count or 0,
            change_type="edited" if "final_content" in update_data else "status_change",
            change_summary="Section updated",
        )
        session.add(section_version)

        proposal_max_result = await session.execute(
            select(func.max(ProposalVersion.version_number)).where(
                ProposalVersion.proposal_id == proposal.id
            )
        )
        proposal_max = proposal_max_result.scalar() or 0
        proposal_version = ProposalVersion(
            proposal_id=proposal.id,
            user_id=resolved_user_id,
            version_number=proposal_max + 1,
            version_type=ProposalVersionType.SECTION_EDITED,
            description=f"Updated section {section.section_number}",
            snapshot={
                "title": proposal.title,
                "status": proposal.status.value,
                "total_sections": proposal.total_sections,
                "completed_sections": proposal.completed_sections,
                "compliance_score": proposal.compliance_score,
            },
            section_id=section.id,
            section_snapshot={
                "section_id": section.id,
                "title": section.title,
                "status": section.status.value,
            },
        )
        session.add(proposal_version)

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="proposal_section",
        entity_id=section.id,
        action="proposal.section.updated",
        metadata={"proposal_id": proposal.id, "section_id": section.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.section.updated",
        payload={"proposal_id": proposal.id, "section_id": section.id},
    )

    await session.commit()
    await session.refresh(section)

    return ProposalSectionRead.model_validate(section)


@router.get("/sections/{section_id}/evidence", response_model=List[SectionEvidenceRead])
async def list_section_evidence(
    section_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> List[SectionEvidenceRead]:
    """
    List evidence links for a section.
    """
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

    evidence_result = await session.execute(
        select(SectionEvidence).where(SectionEvidence.section_id == section_id)
    )
    evidence_links = evidence_result.scalars().all()

    response: List[SectionEvidenceRead] = []
    for link in evidence_links:
        doc_result = await session.execute(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.id == link.document_id
            )
        )
        doc = doc_result.scalar_one_or_none()
        response.append(
            SectionEvidenceRead(
                id=link.id,
                section_id=link.section_id,
                document_id=link.document_id,
                chunk_id=link.chunk_id,
                citation=link.citation,
                notes=link.notes,
                created_at=link.created_at,
                document_title=doc.title if doc else None,
                document_filename=doc.original_filename if doc else None,
            )
        )

    return response


@router.post("/sections/{section_id}/evidence", response_model=SectionEvidenceRead)
async def add_section_evidence(
    section_id: int,
    payload: SectionEvidenceCreate,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SectionEvidenceRead:
    """
    Add evidence link to a section.
    """
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

    document_result = await session.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.id == payload.document_id
        )
    )
    document = document_result.scalar_one_or_none()
    if not document or document.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Document not found")

    if payload.chunk_id:
        chunk_result = await session.execute(
            select(DocumentChunk).where(
                DocumentChunk.id == payload.chunk_id,
                DocumentChunk.document_id == payload.document_id,
            )
        )
        if not chunk_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document chunk not found")

    link = SectionEvidence(
        section_id=section_id,
        document_id=payload.document_id,
        chunk_id=payload.chunk_id,
        citation=payload.citation,
        notes=payload.notes,
    )
    session.add(link)
    await session.flush()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="section_evidence",
        entity_id=link.id,
        action="proposal.section.evidence.added",
        metadata={
            "proposal_id": proposal.id,
            "section_id": section_id,
            "document_id": payload.document_id,
        },
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.section.evidence.added",
        payload={
            "proposal_id": proposal.id,
            "section_id": section_id,
            "document_id": payload.document_id,
        },
    )

    await session.commit()
    await session.refresh(link)

    return SectionEvidenceRead(
        id=link.id,
        section_id=link.section_id,
        document_id=link.document_id,
        chunk_id=link.chunk_id,
        citation=link.citation,
        notes=link.notes,
        created_at=link.created_at,
        document_title=document.title,
        document_filename=document.original_filename,
    )


@router.delete("/sections/{section_id}/evidence/{evidence_id}")
async def delete_section_evidence(
    section_id: int,
    evidence_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Remove evidence link from a section.
    """
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

    evidence_result = await session.execute(
        select(SectionEvidence).where(
            SectionEvidence.id == evidence_id,
            SectionEvidence.section_id == section_id,
        )
    )
    evidence = evidence_result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    await session.delete(evidence)

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="section_evidence",
        entity_id=evidence_id,
        action="proposal.section.evidence.deleted",
        metadata={"section_id": section_id, "proposal_id": proposal.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.section.evidence.deleted",
        payload={"section_id": section_id, "proposal_id": proposal.id},
    )

    await session.commit()

    return {"message": "Evidence deleted", "evidence_id": evidence_id}


@router.get("/proposals/{proposal_id}/submission-packages", response_model=List[SubmissionPackageRead])
async def list_submission_packages(
    proposal_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> List[SubmissionPackageRead]:
    """
    List submission packages for a proposal.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    result = await session.execute(
        select(SubmissionPackage)
        .where(SubmissionPackage.proposal_id == proposal_id)
        .order_by(SubmissionPackage.created_at.desc())
    )
    packages = result.scalars().all()
    return [SubmissionPackageRead.model_validate(pkg) for pkg in packages]


@router.post("/proposals/{proposal_id}/submission-packages", response_model=SubmissionPackageRead)
async def create_submission_package(
    proposal_id: int,
    payload: SubmissionPackageCreate,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SubmissionPackageRead:
    """
    Create a submission package for a proposal.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    package = SubmissionPackage(
        proposal_id=proposal_id,
        owner_id=payload.owner_id,
        title=payload.title,
        due_date=payload.due_date,
        checklist=payload.checklist or [],
        notes=payload.notes,
    )
    session.add(package)
    await session.flush()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="submission_package",
        entity_id=package.id,
        action="proposal.submission_package.created",
        metadata={"proposal_id": proposal_id, "title": payload.title},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.submission_package.created",
        payload={"proposal_id": proposal_id, "title": payload.title},
    )

    await session.commit()
    await session.refresh(package)

    return SubmissionPackageRead.model_validate(package)


@router.patch("/submission-packages/{package_id}", response_model=SubmissionPackageRead)
async def update_submission_package(
    package_id: int,
    payload: SubmissionPackageUpdate,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SubmissionPackageRead:
    """
    Update a submission package.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    package_result = await session.execute(
        select(SubmissionPackage).where(SubmissionPackage.id == package_id)
    )
    package = package_result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Submission package not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == package.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Submission package not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(package, field, value)

    package.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="submission_package",
        entity_id=package.id,
        action="proposal.submission_package.updated",
        metadata={"proposal_id": proposal.id, "package_id": package.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.submission_package.updated",
        payload={"proposal_id": proposal.id, "package_id": package.id},
    )

    await session.commit()
    await session.refresh(package)

    return SubmissionPackageRead.model_validate(package)


@router.post("/submission-packages/{package_id}/submit", response_model=SubmissionPackageRead)
async def submit_submission_package(
    package_id: int,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> SubmissionPackageRead:
    """
    Mark a submission package as submitted.
    """
    resolved_user_id = resolve_user_id(user_id, current_user)

    package_result = await session.execute(
        select(SubmissionPackage).where(SubmissionPackage.id == package_id)
    )
    package = package_result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Submission package not found")

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.id == package.proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal or proposal.user_id != resolved_user_id:
        raise HTTPException(status_code=404, detail="Submission package not found")

    package.status = SubmissionPackageStatus.SUBMITTED
    package.submitted_at = datetime.utcnow()
    package.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=resolved_user_id,
        entity_type="submission_package",
        entity_id=package.id,
        action="proposal.submission_package.submitted",
        metadata={"proposal_id": proposal.id, "package_id": package.id},
    )
    await dispatch_webhook_event(
        session,
        user_id=resolved_user_id,
        event_type="proposal.submission_package.submitted",
        payload={"proposal_id": proposal.id, "package_id": package.id},
    )

    await session.commit()
    await session.refresh(package)

    return SubmissionPackageRead.model_validate(package)


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
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
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
    
    # Create sections for each requirement
    sections_created = 0
    for i, req in enumerate(matrix.requirements):
        section = ProposalSection(
            proposal_id=proposal_id,
            title=f"Response to {req.get('section', 'Requirement')}",
            section_number=f"R{i+1:03d}",
            requirement_id=req.get("id"),
            requirement_text=req.get("requirement_text"),
            display_order=i,
        )
        session.add(section)
        sections_created += 1
    
    proposal.total_sections = sections_created
    await session.commit()
    
    return {
        "proposal_id": proposal_id,
        "sections_created": sections_created,
        "message": f"Created {sections_created} sections from compliance matrix",
    }


@router.post("/{requirement_id}", response_model=DraftResponse)
async def generate_section_draft(
    requirement_id: str = Path(..., description="Requirement ID from compliance matrix"),
    request: DraftRequest = None,
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
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
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured",
        )
    
    # Parse request
    if request is None:
        request = DraftRequest(requirement_id=requirement_id)
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Find the section for this requirement that belongs to the requesting user
    result = await session.execute(
        select(ProposalSection)
        .join(Proposal, ProposalSection.proposal_id == Proposal.id)
        .where(
            ProposalSection.requirement_id == requirement_id,
            Proposal.user_id == resolved_user_id,
        )
        .order_by(desc(ProposalSection.created_at))
        .limit(1)
    )
    section = result.scalar_one_or_none()
    
    if not section:
        raise HTTPException(
            status_code=404,
            detail=f"No section found for requirement {requirement_id}. Create proposal sections first.",
        )
    
    resolved_user_id = resolve_user_id(user_id, current_user)

    # Queue generation task
    task = generate_proposal_section.delay(
        section_id=section.id,
        user_id=resolved_user_id,
        max_words=request.max_words,
        tone=request.tone,
        additional_context=request.additional_context,
    )
    
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
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    max_words: int = Query(500, ge=100, le=2000),
    tone: str = Query("professional", pattern="^(professional|technical|executive)$"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Generate all pending sections for a proposal.
    
    Queues generation tasks for each section that hasn't been written yet.
    """
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")
    
    # Verify proposal exists
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
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
    user_id: Optional[int] = Query(None, description="User ID (optional if authenticated)"),
    ttl_hours: int = Query(24, ge=1, le=168, description="Cache TTL in hours"),
    current_user: Optional[UserAuth] = Depends(get_current_user_optional),
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
