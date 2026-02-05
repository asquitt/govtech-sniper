"""
RFP Sniper - Saved Search Routes
================================
Saved opportunity searches and match evaluation.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.saved_search import SavedSearch
from app.models.rfp import RFP, RFPStatus
from app.schemas.rfp import RFPListItem
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/saved-searches", tags=["Saved Searches"])


class SavedSearchCreate(BaseModel):
    name: str = Field(max_length=255)
    filters: dict = Field(default_factory=dict)
    is_active: bool = True


class SavedSearchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    filters: Optional[dict] = None
    is_active: Optional[bool] = None


class SavedSearchResponse(BaseModel):
    id: int
    name: str
    filters: dict
    is_active: bool
    last_run_at: Optional[datetime]
    last_match_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SavedSearchRunResponse(BaseModel):
    search_id: int
    match_count: int
    matches: List[RFPListItem]
    ran_at: datetime


def _normalize_list(value: Optional[object]) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _apply_filters(query, filters: dict):
    keywords = _normalize_list(filters.get("keywords"))
    agencies = _normalize_list(filters.get("agencies"))
    naics_codes = _normalize_list(filters.get("naics_codes"))
    set_asides = _normalize_list(filters.get("set_asides"))
    statuses = _normalize_list(filters.get("statuses"))
    source_types = _normalize_list(filters.get("source_types"))
    jurisdictions = _normalize_list(filters.get("jurisdictions"))
    contract_vehicles = _normalize_list(filters.get("contract_vehicles"))

    min_value = filters.get("min_value")
    max_value = filters.get("max_value")

    if keywords:
        like_terms = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            like_terms.append(RFP.title.ilike(pattern))
            like_terms.append(RFP.description.ilike(pattern))
            like_terms.append(RFP.summary.ilike(pattern))
            like_terms.append(RFP.solicitation_number.ilike(pattern))
        query = query.where(or_(*like_terms))

    if agencies:
        agency_filters = [RFP.agency.ilike(f"%{agency}%") for agency in agencies]
        query = query.where(or_(*agency_filters))

    if naics_codes:
        query = query.where(RFP.naics_code.in_(naics_codes))

    if set_asides:
        query = query.where(RFP.set_aside.in_(set_asides))

    if statuses:
        valid_statuses = [RFPStatus(status) for status in statuses if status in RFPStatus._value2member_map_]
        if valid_statuses:
            query = query.where(RFP.status.in_(valid_statuses))

    if source_types:
        query = query.where(RFP.source_type.in_(source_types))

    if jurisdictions:
        query = query.where(RFP.jurisdiction.in_(jurisdictions))

    if contract_vehicles:
        query = query.where(RFP.contract_vehicle.in_(contract_vehicles))

    if isinstance(min_value, (int, float)):
        query = query.where(RFP.estimated_value != None)  # noqa: E711
        query = query.where(RFP.estimated_value >= int(min_value))

    if isinstance(max_value, (int, float)):
        query = query.where(RFP.estimated_value != None)  # noqa: E711
        query = query.where(RFP.estimated_value <= int(max_value))

    return query


@router.get("", response_model=List[SavedSearchResponse])
async def list_saved_searches(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[SavedSearchResponse]:
    result = await session.execute(
        select(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
    )
    searches = result.scalars().all()
    return [SavedSearchResponse.model_validate(search) for search in searches]


@router.post("", response_model=SavedSearchResponse)
async def create_saved_search(
    payload: SavedSearchCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedSearchResponse:
    search = SavedSearch(
        user_id=current_user.id,
        name=payload.name,
        filters=payload.filters or {},
        is_active=payload.is_active,
    )
    session.add(search)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="saved_search",
        entity_id=search.id,
        action="saved_search.created",
        metadata={"name": search.name},
    )
    await session.commit()
    await session.refresh(search)

    return SavedSearchResponse.model_validate(search)


@router.patch("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: int,
    payload: SavedSearchUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedSearchResponse:
    result = await session.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(search, field, value)
    search.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="saved_search",
        entity_id=search.id,
        action="saved_search.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(search)

    return SavedSearchResponse.model_validate(search)


@router.delete("/{search_id}")
async def delete_saved_search(
    search_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="saved_search",
        entity_id=search.id,
        action="saved_search.deleted",
        metadata={"name": search.name},
    )
    await session.delete(search)
    await session.commit()

    return {"message": "Saved search deleted"}


@router.post("/{search_id}/run", response_model=SavedSearchRunResponse)
async def run_saved_search(
    search_id: int,
    limit: int = Query(100, ge=1, le=500),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedSearchRunResponse:
    result = await session.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    query = select(RFP).where(RFP.user_id == current_user.id)
    query = _apply_filters(query, search.filters)
    query = query.order_by(RFP.created_at.desc()).limit(limit)
    matches_result = await session.execute(query)
    matches = matches_result.scalars().all()

    search.last_run_at = datetime.utcnow()
    search.last_match_count = len(matches)
    search.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="saved_search",
        entity_id=search.id,
        action="saved_search.run",
        metadata={"match_count": len(matches)},
    )
    await session.commit()
    await session.refresh(search)

    return SavedSearchRunResponse(
        search_id=search.id,
        match_count=len(matches),
        matches=[RFPListItem.model_validate(rfp) for rfp in matches],
        ran_at=search.last_run_at,
    )
