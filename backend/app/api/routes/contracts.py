"""
RFP Sniper - Contract Routes
============================
Endpoints for post-award contract tracking.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.contract import (
    ContractAward,
    ContractDeliverable,
    ContractTask,
    CPARSReview,
    CPARSEvidence,
    ContractStatusReport,
)
from app.models.knowledge_base import KnowledgeBaseDocument
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractRead,
    ContractListResponse,
    DeliverableCreate,
    DeliverableUpdate,
    DeliverableRead,
    TaskCreate,
    TaskUpdate,
    TaskRead,
    CPARSCreate,
    CPARSRead,
    CPARSEvidenceCreate,
    CPARSEvidenceRead,
    StatusReportCreate,
    StatusReportUpdate,
    StatusReportRead,
)
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractListResponse:
    result = await session.execute(
        select(ContractAward).where(ContractAward.user_id == current_user.id)
    )
    contracts = result.scalars().all()
    data = [ContractRead.model_validate(c) for c in contracts]
    return ContractListResponse(contracts=data, total=len(data))


@router.post("", response_model=ContractRead)
async def create_contract(
    payload: ContractCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractRead:
    contract = ContractAward(
        user_id=current_user.id,
        rfp_id=payload.rfp_id,
        contract_number=payload.contract_number,
        title=payload.title,
        agency=payload.agency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        value=payload.value,
        status=payload.status,
        summary=payload.summary,
    )
    session.add(contract)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        action="contract.created",
        metadata={"contract_number": contract.contract_number},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="contract.created",
        payload={"contract_id": contract.id, "title": contract.title},
    )
    await session.commit()
    await session.refresh(contract)

    return ContractRead.model_validate(contract)


@router.get("/{contract_id}", response_model=ContractRead)
async def get_contract(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractRead:
    result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return ContractRead.model_validate(contract)


@router.patch("/{contract_id}", response_model=ContractRead)
async def update_contract(
    contract_id: int,
    payload: ContractUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContractRead:
    result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    contract.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        action="contract.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(contract)

    return ContractRead.model_validate(contract)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        action="contract.deleted",
        metadata={"contract_number": contract.contract_number},
    )
    await session.delete(contract)
    await session.commit()

    return {"message": "Contract deleted"}


# -----------------------------------------------------------------------------
# Deliverables
# -----------------------------------------------------------------------------

@router.get("/{contract_id}/deliverables", response_model=List[DeliverableRead])
async def list_deliverables(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[DeliverableRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractDeliverable).where(ContractDeliverable.contract_id == contract_id)
    )
    deliverables = result.scalars().all()
    return [DeliverableRead.model_validate(d) for d in deliverables]


@router.post("/{contract_id}/deliverables", response_model=DeliverableRead)
async def create_deliverable(
    contract_id: int,
    payload: DeliverableCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeliverableRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    deliverable = ContractDeliverable(
        contract_id=contract_id,
        title=payload.title,
        due_date=payload.due_date,
        status=payload.status,
        notes=payload.notes,
    )
    session.add(deliverable)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_deliverable",
        entity_id=deliverable.id,
        action="contract.deliverable_created",
        metadata={"contract_id": contract_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="contract.deliverable_created",
        payload={"contract_id": contract_id, "deliverable_id": deliverable.id},
    )
    await session.commit()
    await session.refresh(deliverable)

    return DeliverableRead.model_validate(deliverable)


@router.patch("/deliverables/{deliverable_id}", response_model=DeliverableRead)
async def update_deliverable(
    deliverable_id: int,
    payload: DeliverableUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeliverableRead:
    result = await session.execute(
        select(ContractDeliverable).where(ContractDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    # Ensure ownership
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == deliverable.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deliverable, field, value)
    deliverable.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_deliverable",
        entity_id=deliverable.id,
        action="contract.deliverable_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(deliverable)

    return DeliverableRead.model_validate(deliverable)


@router.delete("/deliverables/{deliverable_id}")
async def delete_deliverable(
    deliverable_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(ContractDeliverable).where(ContractDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == deliverable.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_deliverable",
        entity_id=deliverable.id,
        action="contract.deliverable_deleted",
        metadata={"contract_id": deliverable.contract_id},
    )
    await session.delete(deliverable)
    await session.commit()

    return {"message": "Deliverable deleted"}


# -----------------------------------------------------------------------------
# Tasks
# -----------------------------------------------------------------------------

@router.get("/{contract_id}/tasks", response_model=List[TaskRead])
async def list_tasks(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[TaskRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractTask).where(ContractTask.contract_id == contract_id)
    )
    tasks = result.scalars().all()
    return [TaskRead.model_validate(t) for t in tasks]


@router.post("/{contract_id}/tasks", response_model=TaskRead)
async def create_task(
    contract_id: int,
    payload: TaskCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TaskRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    task = ContractTask(
        contract_id=contract_id,
        title=payload.title,
        due_date=payload.due_date,
        notes=payload.notes,
    )
    session.add(task)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_task",
        entity_id=task.id,
        action="contract.task_created",
        metadata={"contract_id": contract_id},
    )
    await session.commit()
    await session.refresh(task)

    return TaskRead.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TaskRead:
    result = await session.execute(
        select(ContractTask).where(ContractTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == task.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    task.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_task",
        entity_id=task.id,
        action="contract.task_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(task)

    return TaskRead.model_validate(task)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(ContractTask).where(ContractTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == task.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_task",
        entity_id=task.id,
        action="contract.task_deleted",
        metadata={"contract_id": task.contract_id},
    )
    await session.delete(task)
    await session.commit()

    return {"message": "Task deleted"}


# -----------------------------------------------------------------------------
# CPARS
# -----------------------------------------------------------------------------

@router.get("/{contract_id}/cpars", response_model=List[CPARSRead])
async def list_cpars(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[CPARSRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(CPARSReview).where(CPARSReview.contract_id == contract_id)
    )
    reviews = result.scalars().all()
    return [CPARSRead.model_validate(r) for r in reviews]


@router.post("/{contract_id}/cpars", response_model=CPARSRead)
async def create_cpars(
    contract_id: int,
    payload: CPARSCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CPARSRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    review = CPARSReview(
        contract_id=contract_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        overall_rating=payload.overall_rating,
        notes=payload.notes,
    )
    session.add(review)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_cpars",
        entity_id=review.id,
        action="contract.cpars_created",
        metadata={"contract_id": contract_id},
    )
    await session.commit()
    await session.refresh(review)

    return CPARSRead.model_validate(review)


@router.get(
    "/{contract_id}/cpars/{cpars_id}/evidence",
    response_model=List[CPARSEvidenceRead],
)
async def list_cpars_evidence(
    contract_id: int,
    cpars_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[CPARSEvidenceRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    review_result = await session.execute(
        select(CPARSReview).where(
            CPARSReview.id == cpars_id,
            CPARSReview.contract_id == contract_id,
        )
    )
    if not review_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="CPARS review not found")

    result = await session.execute(
        select(CPARSEvidence, KnowledgeBaseDocument)
        .join(KnowledgeBaseDocument, KnowledgeBaseDocument.id == CPARSEvidence.document_id)
        .where(CPARSEvidence.cpars_id == cpars_id)
    )
    rows = result.all()
    response: List[CPARSEvidenceRead] = []
    for evidence, document in rows:
        response.append(
            CPARSEvidenceRead(
                id=evidence.id,
                cpars_id=evidence.cpars_id,
                document_id=evidence.document_id,
                citation=evidence.citation,
                notes=evidence.notes,
                created_at=evidence.created_at,
                document_title=document.title if document else None,
                document_type=document.document_type if document else None,
            )
        )
    return response


@router.post(
    "/{contract_id}/cpars/{cpars_id}/evidence",
    response_model=CPARSEvidenceRead,
)
async def add_cpars_evidence(
    contract_id: int,
    cpars_id: int,
    payload: CPARSEvidenceCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CPARSEvidenceRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    review_result = await session.execute(
        select(CPARSReview).where(
            CPARSReview.id == cpars_id,
            CPARSReview.contract_id == contract_id,
        )
    )
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="CPARS review not found")

    doc_result = await session.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.id == payload.document_id,
            KnowledgeBaseDocument.user_id == current_user.id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    evidence = CPARSEvidence(
        cpars_id=review.id,
        document_id=payload.document_id,
        citation=payload.citation,
        notes=payload.notes,
    )
    session.add(evidence)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_cpars_evidence",
        entity_id=evidence.id,
        action="contract.cpars_evidence.added",
        metadata={"contract_id": contract_id, "cpars_id": cpars_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="contract.cpars_evidence.added",
        payload={"contract_id": contract_id, "cpars_id": cpars_id, "evidence_id": evidence.id},
    )

    await session.commit()
    await session.refresh(evidence)

    return CPARSEvidenceRead(
        id=evidence.id,
        cpars_id=evidence.cpars_id,
        document_id=evidence.document_id,
        citation=evidence.citation,
        notes=evidence.notes,
        created_at=evidence.created_at,
        document_title=document.title,
        document_type=document.document_type,
    )


@router.delete("/{contract_id}/cpars/{cpars_id}/evidence/{evidence_id}")
async def delete_cpars_evidence(
    contract_id: int,
    cpars_id: int,
    evidence_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    review_result = await session.execute(
        select(CPARSReview).where(
            CPARSReview.id == cpars_id,
            CPARSReview.contract_id == contract_id,
        )
    )
    if not review_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="CPARS review not found")

    evidence_result = await session.execute(
        select(CPARSEvidence).where(
            CPARSEvidence.id == evidence_id,
            CPARSEvidence.cpars_id == cpars_id,
        )
    )
    evidence = evidence_result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_cpars_evidence",
        entity_id=evidence.id,
        action="contract.cpars_evidence.deleted",
        metadata={"contract_id": contract_id, "cpars_id": cpars_id},
    )
    await session.delete(evidence)
    await session.commit()

    return {"message": "Evidence deleted", "evidence_id": evidence_id}


# -----------------------------------------------------------------------------
# Status Reports
# -----------------------------------------------------------------------------

@router.get("/{contract_id}/status-reports", response_model=List[StatusReportRead])
async def list_status_reports(
    contract_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[StatusReportRead]:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await session.execute(
        select(ContractStatusReport).where(
            ContractStatusReport.contract_id == contract_id
        )
    )
    reports = result.scalars().all()
    return [StatusReportRead.model_validate(r) for r in reports]


@router.get("/{contract_id}/status-reports/{report_id}/export")
async def export_status_report(
    contract_id: int,
    report_id: int,
    format: str = Query("markdown", pattern="^(markdown|json)$"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    report_result = await session.execute(
        select(ContractStatusReport).where(
            ContractStatusReport.id == report_id,
            ContractStatusReport.contract_id == contract_id,
        )
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Status report not found")

    report_payload = StatusReportRead.model_validate(report).model_dump()

    if format == "json":
        return JSONResponse(content=report_payload)

    markdown = (
        f"# Status Report\n\n"
        f"**Period:** {report.period_start or 'TBD'} - {report.period_end or 'TBD'}\n\n"
        f"## Summary\n{report.summary or 'No summary provided.'}\n\n"
        f"## Accomplishments\n{report.accomplishments or 'No accomplishments provided.'}\n\n"
        f"## Risks\n{report.risks or 'No risks provided.'}\n\n"
        f"## Next Steps\n{report.next_steps or 'No next steps provided.'}\n"
    )
    response = PlainTextResponse(markdown)
    response.headers["Content-Disposition"] = "attachment; filename=status_report.md"
    return response


@router.post("/{contract_id}/status-reports", response_model=StatusReportRead)
async def create_status_report(
    contract_id: int,
    payload: StatusReportCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StatusReportRead:
    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    report = ContractStatusReport(
        contract_id=contract_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        summary=payload.summary,
        accomplishments=payload.accomplishments,
        risks=payload.risks,
        next_steps=payload.next_steps,
    )
    session.add(report)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_status_report",
        entity_id=report.id,
        action="contract.status_report_created",
        metadata={"contract_id": contract_id},
    )
    await dispatch_webhook_event(
        session,
        user_id=current_user.id,
        event_type="contract.status_report_created",
        payload={"contract_id": contract_id, "report_id": report.id},
    )

    await session.commit()
    await session.refresh(report)

    return StatusReportRead.model_validate(report)


@router.patch("/status-reports/{report_id}", response_model=StatusReportRead)
async def update_status_report(
    report_id: int,
    payload: StatusReportUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StatusReportRead:
    report_result = await session.execute(
        select(ContractStatusReport).where(ContractStatusReport.id == report_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Status report not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == report.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)
    report.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_status_report",
        entity_id=report.id,
        action="contract.status_report_updated",
        metadata={"updated_fields": list(update_data.keys())},
    )

    await session.commit()
    await session.refresh(report)

    return StatusReportRead.model_validate(report)


@router.delete("/status-reports/{report_id}")
async def delete_status_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report_result = await session.execute(
        select(ContractStatusReport).where(ContractStatusReport.id == report_id)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Status report not found")

    contract_result = await session.execute(
        select(ContractAward).where(
            ContractAward.id == report.contract_id,
            ContractAward.user_id == current_user.id,
        )
    )
    if not contract_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contract_status_report",
        entity_id=report.id,
        action="contract.status_report_deleted",
        metadata={"contract_id": report.contract_id},
    )
    await session.delete(report)
    await session.commit()

    return {"message": "Status report deleted"}
