"""
RFP Sniper - Audit Routes
=========================
Advanced audit log views and summaries.
"""

from datetime import datetime, timedelta
from typing import List, Optional
import csv
import io
import json
import hmac
import hashlib

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select
from pydantic import BaseModel

from app.database import get_session
from app.api.deps import get_current_user, UserAuth
from app.models.audit import AuditEvent
from app.config import settings
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditEventResponse(BaseModel):
    id: int
    user_id: Optional[int]
    entity_type: str
    entity_id: Optional[int]
    action: str
    event_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditSummaryResponse(BaseModel):
    period_days: int
    total_events: int
    by_action: List[dict]
    by_entity_type: List[dict]


@router.get("", response_model=List[AuditEventResponse])
async def list_audit_events(
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[AuditEventResponse]:
    query = select(AuditEvent).where(AuditEvent.user_id == current_user.id)

    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if action:
        query = query.where(AuditEvent.action == action)
    if start_date:
        query = query.where(AuditEvent.created_at >= start_date)
    if end_date:
        query = query.where(AuditEvent.created_at <= end_date)

    query = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    events = result.scalars().all()
    return [AuditEventResponse.model_validate(event) for event in events]


@router.get("/summary", response_model=AuditSummaryResponse)
async def get_audit_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AuditSummaryResponse:
    start_date = datetime.utcnow() - timedelta(days=days)

    total_result = await session.execute(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.user_id == current_user.id,
            AuditEvent.created_at >= start_date,
        )
    )
    total_events = total_result.scalar() or 0

    by_action_result = await session.execute(
        select(AuditEvent.action, func.count(AuditEvent.id).label("count"))
        .where(
            AuditEvent.user_id == current_user.id,
            AuditEvent.created_at >= start_date,
        )
        .group_by(AuditEvent.action)
        .order_by(func.count(AuditEvent.id).desc())
    )
    by_action = [
        {"action": row.action, "count": row.count}
        for row in by_action_result.all()
    ]

    by_entity_result = await session.execute(
        select(AuditEvent.entity_type, func.count(AuditEvent.id).label("count"))
        .where(
            AuditEvent.user_id == current_user.id,
            AuditEvent.created_at >= start_date,
        )
        .group_by(AuditEvent.entity_type)
        .order_by(func.count(AuditEvent.id).desc())
    )
    by_entity = [
        {"entity_type": row.entity_type, "count": row.count}
        for row in by_entity_result.all()
    ]

    return AuditSummaryResponse(
        period_days=days,
        total_events=total_events,
        by_action=by_action,
        by_entity_type=by_entity,
    )


@router.get("/export")
async def export_audit_events(
    format: str = Query("json", pattern="^(json|csv)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(AuditEvent).where(AuditEvent.user_id == current_user.id)

    if start_date:
        query = query.where(AuditEvent.created_at >= start_date)
    if end_date:
        query = query.where(AuditEvent.created_at <= end_date)

    query = query.order_by(AuditEvent.created_at.desc())
    result = await session.execute(query)
    events = result.scalars().all()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="audit_export",
        entity_id=None,
        action="audit.exported",
        metadata={"format": format, "count": len(events)},
    )
    await session.commit()

    export_records = [
        {
            "id": event.id,
            "user_id": event.user_id,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "action": event.action,
            "metadata": event.event_metadata,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "id",
                "user_id",
                "entity_type",
                "entity_id",
                "action",
                "metadata",
                "created_at",
            ],
        )
        writer.writeheader()
        for record in export_records:
            row = dict(record)
            row["metadata"] = json.dumps(record["metadata"])
            writer.writerow(row)

        content = output.getvalue()
        signature = hmac.new(
            settings.audit_export_signing_key.encode("utf-8"),
            content.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        response = StreamingResponse(
            iter([content]),
            media_type="text/csv",
        )
        response.headers["X-Audit-Signature"] = signature
        response.headers["Content-Disposition"] = "attachment; filename=audit_export.csv"
        return response

    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "count": len(export_records),
        "records": export_records,
    }
    serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = hmac.new(
        settings.audit_export_signing_key.encode("utf-8"),
        serialized,
        hashlib.sha256,
    ).hexdigest()

    return JSONResponse(
        content={"signature": signature, "payload": payload},
        headers={"X-Audit-Signature": signature},
    )
