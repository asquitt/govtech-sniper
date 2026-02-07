"""
RFP Sniper - Opportunity Contact Routes
=======================================
CRUD for opportunity contacts, AI extraction, and agency directory.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.models.contact import OpportunityContact, AgencyContactDatabase
from app.models.rfp import RFP
from app.services.audit_service import log_audit_event
from app.services.contact_extractor import extract_contacts_from_text

router = APIRouter(prefix="/contacts", tags=["Contacts"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ContactCreate(BaseModel):
    rfp_id: Optional[int] = None
    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    agency: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    agency: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None


class ContactResponse(BaseModel):
    id: int
    rfp_id: Optional[int]
    name: str
    role: Optional[str]
    organization: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    notes: Optional[str]
    agency: Optional[str]
    title: Optional[str]
    department: Optional[str]
    location: Optional[str]
    source: Optional[str]
    extraction_confidence: Optional[float]
    linked_rfp_ids: Optional[list]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExtractedContactResponse(BaseModel):
    name: str
    title: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    agency: Optional[str]
    role: Optional[str]


class AgencyCreate(BaseModel):
    agency_name: str
    office: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    primary_contact_id: Optional[int] = None


class AgencyResponse(BaseModel):
    id: int
    agency_name: str
    office: Optional[str]
    address: Optional[str]
    website: Optional[str]
    primary_contact_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Existing CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ContactResponse])
async def list_contacts(
    rfp_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[ContactResponse]:
    query = select(OpportunityContact).where(
        OpportunityContact.user_id == current_user.id
    )
    if rfp_id:
        query = query.where(OpportunityContact.rfp_id == rfp_id)
    query = query.order_by(OpportunityContact.created_at.desc()).limit(limit)
    result = await session.execute(query)
    contacts = result.scalars().all()
    return [ContactResponse.model_validate(contact) for contact in contacts]


@router.post("", response_model=ContactResponse)
async def create_contact(
    payload: ContactCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContactResponse:
    if payload.rfp_id:
        rfp_result = await session.execute(
            select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
        )
        if not rfp_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="RFP not found")

    contact = OpportunityContact(
        user_id=current_user.id,
        **payload.model_dump(),
    )
    session.add(contact)
    await session.flush()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contact",
        entity_id=contact.id,
        action="contact.created",
        metadata={"rfp_id": contact.rfp_id, "name": contact.name},
    )
    await session.commit()
    await session.refresh(contact)

    return ContactResponse.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContactResponse:
    result = await session.execute(
        select(OpportunityContact).where(
            OpportunityContact.id == contact_id,
            OpportunityContact.user_id == current_user.id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    contact.updated_at = datetime.utcnow()

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contact",
        entity_id=contact.id,
        action="contact.updated",
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()
    await session.refresh(contact)

    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(OpportunityContact).where(
            OpportunityContact.id == contact_id,
            OpportunityContact.user_id == current_user.id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await log_audit_event(
        session,
        user_id=current_user.id,
        entity_type="contact",
        entity_id=contact.id,
        action="contact.deleted",
        metadata={"name": contact.name},
    )
    await session.delete(contact)
    await session.commit()

    return {"message": "Contact deleted"}


# ---------------------------------------------------------------------------
# AI extraction endpoint
# ---------------------------------------------------------------------------

@router.post("/extract/{rfp_id}", response_model=List[ExtractedContactResponse])
async def extract_contacts(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[ExtractedContactResponse]:
    """AI-extract contacts from an RFP's full text."""
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    text = rfp.full_text or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="RFP has no text content to extract from")

    extracted = await extract_contacts_from_text(text)
    return [ExtractedContactResponse(**c) for c in extracted]


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

@router.get("/search", response_model=List[ContactResponse])
async def search_contacts(
    agency: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[ContactResponse]:
    """Search contacts by agency, role, location, or name."""
    query = select(OpportunityContact).where(
        OpportunityContact.user_id == current_user.id
    )
    if agency:
        query = query.where(OpportunityContact.agency.ilike(f"%{agency}%"))
    if role:
        query = query.where(OpportunityContact.role.ilike(f"%{role}%"))
    if location:
        query = query.where(OpportunityContact.location.ilike(f"%{location}%"))
    if name:
        query = query.where(OpportunityContact.name.ilike(f"%{name}%"))
    query = query.order_by(OpportunityContact.created_at.desc()).limit(limit)

    result = await session.execute(query)
    contacts = result.scalars().all()
    return [ContactResponse.model_validate(c) for c in contacts]


# ---------------------------------------------------------------------------
# Agency directory endpoints
# ---------------------------------------------------------------------------

@router.get("/agencies", response_model=List[AgencyResponse])
async def list_agencies(
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[AgencyResponse]:
    """List agency profiles."""
    query = (
        select(AgencyContactDatabase)
        .where(AgencyContactDatabase.user_id == current_user.id)
        .order_by(AgencyContactDatabase.agency_name)
        .limit(limit)
    )
    result = await session.execute(query)
    agencies = result.scalars().all()
    return [AgencyResponse.model_validate(a) for a in agencies]


@router.post("/agencies", response_model=AgencyResponse)
async def upsert_agency(
    payload: AgencyCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgencyResponse:
    """Create or update an agency profile."""
    # Check for existing agency by name
    result = await session.execute(
        select(AgencyContactDatabase).where(
            AgencyContactDatabase.user_id == current_user.id,
            AgencyContactDatabase.agency_name == payload.agency_name,
        )
    )
    agency = result.scalar_one_or_none()

    if agency:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(agency, field, value)
        agency.updated_at = datetime.utcnow()
    else:
        agency = AgencyContactDatabase(
            user_id=current_user.id,
            **payload.model_dump(),
        )
        session.add(agency)

    await session.commit()
    await session.refresh(agency)
    return AgencyResponse.model_validate(agency)
