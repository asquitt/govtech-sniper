"""Custom report routes for building, scheduling, and exporting reports."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.report import ReportType, SavedReport, ScheduleFrequency
from app.models.user import User
from app.schemas.report import (
    ReportDataResponse,
    ReportDeliveryScheduleUpdate,
    ReportShareUpdate,
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


def _report_data_for_config(report: SavedReport) -> ReportDataResponse:
    base_data = MOCK_DATA.get(report.report_type, MOCK_DATA[ReportType.ACTIVITY])
    selected_columns = report.config.get("columns") if isinstance(report.config, dict) else None
    if not selected_columns:
        return base_data

    allowed_columns = [col for col in selected_columns if col in base_data.columns]
    if not allowed_columns:
        return base_data

    rows = [{col: row.get(col) for col in allowed_columns} for row in base_data.rows]
    return ReportDataResponse(columns=allowed_columns, rows=rows, total_rows=len(rows))


def _normalize_email_list(emails: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in emails:
        candidate = value.strip().lower()
        if not candidate or "@" not in candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


async def _get_report_or_404(report_id: int, session: AsyncSession) -> SavedReport:
    report = await session.get(SavedReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _can_view_report(report: SavedReport, user: UserAuth) -> bool:
    if report.user_id == int(user.id):
        return True
    if not report.is_shared:
        return False
    shared_with = _normalize_email_list(report.shared_with_emails or [])
    if not shared_with:
        return True
    return str(user.email).strip().lower() in shared_with


async def _get_accessible_report(
    report_id: int,
    user: UserAuth,
    session: AsyncSession,
) -> SavedReport:
    report = await _get_report_or_404(report_id, session)
    if not _can_view_report(report, user):
        raise HTTPException(status_code=404, detail="Report not found")
    return report


async def _get_owned_report(
    report_id: int,
    user: UserAuth,
    session: AsyncSession,
) -> SavedReport:
    report = await _get_report_or_404(report_id, session)
    if report.user_id != int(user.id):
        raise HTTPException(status_code=403, detail="Only report owners can modify this report")
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
        is_shared=body.is_shared,
        shared_with_emails=_normalize_email_list(body.shared_with_emails),
        delivery_recipients=_normalize_email_list(body.delivery_recipients),
        delivery_enabled=body.delivery_enabled,
        delivery_subject=body.delivery_subject,
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
        .where((SavedReport.user_id == int(current_user.id)) | (SavedReport.is_shared == True))
        .order_by(SavedReport.updated_at.desc())
    )
    reports = list(result.scalars().all())
    return [report for report in reports if _can_view_report(report, current_user)]


@router.get("/{report_id}", response_model=SavedReportRead)
async def get_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    return await _get_accessible_report(report_id, current_user, session)


@router.patch("/{report_id}", response_model=SavedReportRead)
async def update_report(
    report_id: int,
    body: SavedReportUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    report = await _get_owned_report(report_id, current_user, session)
    update_data = body.model_dump(exclude_unset=True)
    if "config" in update_data and update_data["config"] is not None:
        update_data["config"] = body.config.model_dump()
    if "shared_with_emails" in update_data and update_data["shared_with_emails"] is not None:
        update_data["shared_with_emails"] = _normalize_email_list(body.shared_with_emails or [])
    if "delivery_recipients" in update_data and update_data["delivery_recipients"] is not None:
        update_data["delivery_recipients"] = _normalize_email_list(body.delivery_recipients or [])
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
    report = await _get_owned_report(report_id, current_user, session)
    await session.delete(report)
    await session.commit()
    return {"detail": "Report deleted"}


@router.post("/{report_id}/generate", response_model=ReportDataResponse)
async def generate_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportDataResponse:
    report = await _get_accessible_report(report_id, current_user, session)
    report.last_generated_at = datetime.utcnow()
    session.add(report)
    await session.commit()
    return _report_data_for_config(report)


@router.post("/{report_id}/export")
async def export_report(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    report = await _get_accessible_report(report_id, current_user, session)
    data = _report_data_for_config(report)

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
    frequency: ScheduleFrequency | None = None,
    payload: ReportDeliveryScheduleUpdate | None = Body(default=None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    report = await _get_owned_report(report_id, current_user, session)

    resolved_frequency = payload.frequency if payload else frequency
    if not resolved_frequency:
        raise HTTPException(status_code=400, detail="Schedule frequency is required")

    report.schedule = resolved_frequency
    if payload:
        report.delivery_recipients = _normalize_email_list(payload.recipients)
        report.delivery_enabled = payload.enabled
        report.delivery_subject = payload.subject

    report.updated_at = datetime.utcnow()
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.patch("/{report_id}/share", response_model=SavedReportRead)
async def share_report(
    report_id: int,
    payload: ReportShareUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedReport:
    report = await _get_owned_report(report_id, current_user, session)
    report.is_shared = payload.is_shared
    report.shared_with_emails = (
        _normalize_email_list(payload.shared_with_emails) if payload.is_shared else []
    )
    report.updated_at = datetime.utcnow()
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.get("/{report_id}/delivery")
async def get_delivery_schedule(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get_accessible_report(report_id, current_user, session)
    owner = await session.get(User, report.user_id)
    return {
        "report_id": report.id,
        "owner_email": owner.email if owner else None,
        "frequency": report.schedule,
        "enabled": report.delivery_enabled,
        "recipients": report.delivery_recipients,
        "subject": report.delivery_subject,
        "last_delivered_at": report.last_delivered_at,
    }


@router.post("/{report_id}/delivery/send")
async def send_report_delivery(
    report_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await _get_owned_report(report_id, current_user, session)
    if not report.schedule:
        raise HTTPException(status_code=400, detail="Configure a delivery schedule first")
    if not report.delivery_enabled:
        raise HTTPException(status_code=400, detail="Delivery is disabled for this report")
    if not report.delivery_recipients:
        raise HTTPException(status_code=400, detail="Add at least one recipient")

    data = _report_data_for_config(report)
    delivered_at = datetime.utcnow()
    report.last_delivered_at = delivered_at
    report.updated_at = delivered_at
    session.add(report)
    await session.commit()

    return {
        "status": "sent",
        "report_id": report.id,
        "frequency": report.schedule,
        "recipient_count": len(report.delivery_recipients),
        "recipients": report.delivery_recipients,
        "row_count": data.total_rows,
        "subject": report.delivery_subject or f"{report.name} report delivery",
        "delivered_at": delivered_at.isoformat(),
    }
