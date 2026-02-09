"""Custom report routes for building, scheduling, and exporting reports."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.report import ReportType, SavedReport, ScheduleFrequency
from app.schemas.report import (
    ReportDataResponse,
    SavedReportCreate,
    SavedReportRead,
    SavedReportUpdate,
)
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/reports", tags=["reports"])


# -- Mock data generators per report type --

MOCK_DATA: dict[str, ReportDataResponse] = {
    ReportType.PIPELINE: ReportDataResponse(
        columns=["opportunity", "agency", "stage", "value", "due_date"],
        rows=[
            {
                "opportunity": "IT Modernization",
                "agency": "DoD",
                "stage": "Capture",
                "value": 2500000,
                "due_date": "2026-04-15",
            },
            {
                "opportunity": "Cloud Migration",
                "agency": "GSA",
                "stage": "Draft",
                "value": 1200000,
                "due_date": "2026-05-01",
            },
        ],
        total_rows=2,
    ),
    ReportType.PROPOSALS: ReportDataResponse(
        columns=["proposal", "rfp", "status", "score", "submitted_at"],
        rows=[
            {
                "proposal": "Technical Volume",
                "rfp": "W911-24-001",
                "status": "Submitted",
                "score": 92,
                "submitted_at": "2026-01-20",
            },
            {
                "proposal": "Management Volume",
                "rfp": "FA8750-24-003",
                "status": "Draft",
                "score": 78,
                "submitted_at": None,
            },
        ],
        total_rows=2,
    ),
    ReportType.REVENUE: ReportDataResponse(
        columns=["contract", "agency", "monthly_revenue", "period"],
        rows=[
            {
                "contract": "STARS III",
                "agency": "GSA",
                "monthly_revenue": 450000,
                "period": "2026-01",
            },
            {"contract": "OASIS+", "agency": "DoD", "monthly_revenue": 320000, "period": "2026-01"},
        ],
        total_rows=2,
    ),
    ReportType.ACTIVITY: ReportDataResponse(
        columns=["user", "action", "target", "timestamp"],
        rows=[
            {
                "user": "admin@company.com",
                "action": "Created proposal",
                "target": "Technical Volume",
                "timestamp": "2026-02-05T14:30:00",
            },
            {
                "user": "admin@company.com",
                "action": "Analyzed RFP",
                "target": "W911-24-001",
                "timestamp": "2026-02-04T09:15:00",
            },
        ],
        total_rows=2,
    ),
}


async def _get_user_report(
    report_id: int,
    user: UserAuth,
    session: AsyncSession,
) -> SavedReport:
    """Fetch a report owned by the current user or raise 404."""
    report = await session.get(SavedReport, report_id)
    if not report or report.user_id != int(user.user_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("", response_model=SavedReportRead)
async def create_report(
    body: SavedReportCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    report = SavedReport(
        user_id=int(current_user.id),
        name=body.name,
        report_type=body.report_type,
        config=body.config.model_dump(),
        schedule=body.schedule,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.get("", response_model=list[SavedReportRead])
async def list_reports(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SavedReport]:
    result = await session.execute(
        select(SavedReport)
        .where(SavedReport.user_id == int(current_user.id))
        .order_by(SavedReport.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{report_id}", response_model=SavedReportRead)
async def get_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    return await _get_user_report(report_id, current_user, session)


@router.patch("/{report_id}", response_model=SavedReportRead)
async def update_report(
    report_id: int,
    body: SavedReportUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    report = await _get_user_report(report_id, current_user, session)
    update_data = body.model_dump(exclude_unset=True)
    if "config" in update_data and update_data["config"] is not None:
        update_data["config"] = body.config.model_dump()
    for key, value in update_data.items():
        setattr(report, key, value)
    report.updated_at = datetime.utcnow()
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get_user_report(report_id, current_user, session)
    await session.delete(report)
    await session.commit()
    return {"detail": "Report deleted"}


@router.post("/{report_id}/generate", response_model=ReportDataResponse)
async def generate_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportDataResponse:
    report = await _get_user_report(report_id, current_user, session)
    report.last_generated_at = datetime.utcnow()
    session.add(report)
    await session.commit()
    return MOCK_DATA.get(report.report_type, MOCK_DATA[ReportType.ACTIVITY])


@router.post("/{report_id}/export")
async def export_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    report = await _get_user_report(report_id, current_user, session)
    data = MOCK_DATA.get(report.report_type, MOCK_DATA[ReportType.ACTIVITY])

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=data.columns)
    writer.writeheader()
    for row in data.rows:
        writer.writerow({col: row.get(col, "") for col in data.columns})

    buf.seek(0)
    filename = f"{report.name.replace(' ', '_').lower()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{report_id}/schedule", response_model=SavedReportRead)
async def set_schedule(
    report_id: int,
    frequency: ScheduleFrequency,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    report = await _get_user_report(report_id, current_user, session)
    report.schedule = frequency
    report.updated_at = datetime.utcnow()
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report
