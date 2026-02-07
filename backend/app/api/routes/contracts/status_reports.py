"""
Contract status report CRUD operations.
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
from app.models.contract import ContractAward, ContractStatusReport
from app.schemas.contract import StatusReportCreate, StatusReportUpdate, StatusReportRead
from app.services.audit_service import log_audit_event
from app.services.webhook_service import dispatch_webhook_event

router = APIRouter()


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
