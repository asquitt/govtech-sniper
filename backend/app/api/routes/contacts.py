"""
RFP Sniper - Opportunity Contact Routes
=======================================
CRUD for opportunity contacts, AI extraction, and agency directory.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.contact import AgencyContactDatabase, OpportunityContact
from app.models.rfp import RFP
from app.services.audit_service import log_audit_event
from app.services.auth_service import UserAuth
from app.services.contact_extractor import extract_contacts_from_text

router = APIRouter(prefix="/contacts", tags=["Contacts"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ContactCreate(BaseModel):
    rfp_id: int | None = None
    name: str
    role: str | None = None
    organization: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    notes: str | None = None
    agency: str | None = None
    title: str | None = None
    department: str | None = None
    location: str | None = None
    source: str | None = "manual"
    extraction_confidence: float | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    organization: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    notes: str | None = None
    agency: str | None = None
    title: str | None = None
    department: str | None = None
    location: str | None = None
    source: str | None = None
    extraction_confidence: float | None = None


class ContactResponse(BaseModel):
    id: int
    rfp_id: int | None
    name: str
    role: str | None
    organization: str | None
    email: str | None
    phone: str | None
    notes: str | None
    agency: str | None
    title: str | None
    department: str | None
    location: str | None
    source: str | None
    extraction_confidence: float | None
    linked_rfp_ids: list | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExtractedContactResponse(BaseModel):
    name: str
    title: str | None
    email: str | None
    phone: str | None
    agency: str | None
    role: str | None


class AgencyCreate(BaseModel):
    agency_name: str
    office: str | None = None
    address: str | None = None
    website: str | None = None
    primary_contact_id: int | None = None


class AgencyResponse(BaseModel):
    id: int
    agency_name: str
    office: str | None
    address: str | None
    website: str | None
    primary_contact_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _merge_contact_links(contact: OpportunityContact, rfp_id: int | None) -> None:
    if not rfp_id:
        return
    linked_ids = [link for link in (contact.linked_rfp_ids or []) if isinstance(link, int)]
    if contact.rfp_id:
        linked_ids.append(contact.rfp_id)
    if rfp_id not in linked_ids:
        linked_ids.append(rfp_id)
    contact.linked_rfp_ids = sorted(set(linked_ids))
    if not contact.rfp_id:
        contact.rfp_id = rfp_id


async def _find_existing_contact_for_linking(
    session: AsyncSession,
    user_id: int,
    name: str,
    email: str | None,
    agency: str | None,
) -> OpportunityContact | None:
    normalized_email = _normalize_text(email)
    normalized_name = _normalize_text(name)
    normalized_agency = _normalize_text(agency)

    query = select(OpportunityContact).where(OpportunityContact.user_id == user_id)
    if normalized_email:
        query = query.where(func.lower(OpportunityContact.email) == normalized_email.lower())
    elif normalized_name:
        query = query.where(func.lower(OpportunityContact.name) == normalized_name.lower())
        if normalized_agency:
            query = query.where(
                func.lower(func.coalesce(OpportunityContact.agency, ""))
                == normalized_agency.lower()
            )
    else:
        return None

    result = await session.execute(query.order_by(OpportunityContact.updated_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def _upsert_agency_contact_directory(
    session: AsyncSession,
    user_id: int,
    agency_name: str | None,
    primary_contact_id: int | None,
) -> None:
    normalized_agency = _normalize_text(agency_name)
    if not normalized_agency or not primary_contact_id:
        return

    result = await session.execute(
        select(AgencyContactDatabase).where(
            AgencyContactDatabase.user_id == user_id,
            func.lower(AgencyContactDatabase.agency_name) == normalized_agency.lower(),
        )
    )
    agency = result.scalar_one_or_none()
    if agency:
        if not agency.primary_contact_id:
            agency.primary_contact_id = primary_contact_id
        agency.updated_at = datetime.utcnow()
        return

    session.add(
        AgencyContactDatabase(
            user_id=user_id,
            agency_name=normalized_agency,
            primary_contact_id=primary_contact_id,
        )
    )


def _merge_contact_metadata(
    contact: OpportunityContact,
    *,
    role: str | None,
    organization: str | None,
    phone: str | None,
    notes: str | None,
    title: str | None,
    department: str | None,
    location: str | None,
    source: str | None,
    extraction_confidence: float | None,
) -> None:
    # Preserve existing values and backfill missing metadata from new source payloads.
    if not contact.role and role:
        contact.role = role
    if not contact.organization and organization:
        contact.organization = organization
    if not contact.phone and phone:
        contact.phone = phone
    if not contact.notes and notes:
        contact.notes = notes
    if not contact.title and title:
        contact.title = title
    if not contact.department and department:
        contact.department = department
    if not contact.location and location:
        contact.location = location
    if source and (contact.source in (None, "manual")):
        contact.source = source
    if extraction_confidence is not None and contact.extraction_confidence is None:
        contact.extraction_confidence = extraction_confidence


# ---------------------------------------------------------------------------
# Existing CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    rfp_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ContactResponse]:
    query = select(OpportunityContact).where(OpportunityContact.user_id == current_user.id)
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
    rfp: RFP | None = None
    if payload.rfp_id:
        rfp_result = await session.execute(
            select(RFP).where(RFP.id == payload.rfp_id, RFP.user_id == current_user.id)
        )
        rfp = rfp_result.scalar_one_or_none()
        if not rfp:
            raise HTTPException(status_code=404, detail="RFP not found")

    resolved_agency = _normalize_text(payload.agency) or (rfp.agency if rfp else None)
    existing = await _find_existing_contact_for_linking(
        session=session,
        user_id=current_user.id,
        name=payload.name,
        email=payload.email,
        agency=resolved_agency,
    )
    if existing:
        _merge_contact_links(existing, payload.rfp_id)
        if resolved_agency and not existing.agency:
            existing.agency = resolved_agency
        _merge_contact_metadata(
            existing,
            role=payload.role,
            organization=payload.organization,
            phone=payload.phone,
            notes=payload.notes,
            title=payload.title,
            department=payload.department,
            location=payload.location,
            source=payload.source,
            extraction_confidence=payload.extraction_confidence,
        )
        existing.updated_at = datetime.utcnow()
        await _upsert_agency_contact_directory(
            session=session,
            user_id=current_user.id,
            agency_name=existing.agency,
            primary_contact_id=existing.id,
        )
        await log_audit_event(
            session,
            user_id=current_user.id,
            entity_type="contact",
            entity_id=existing.id,
            action="contact.linked",
            metadata={"rfp_id": payload.rfp_id, "name": existing.name},
        )
        await session.commit()
        await session.refresh(existing)
        return ContactResponse.model_validate(existing)

    contact_data = payload.model_dump()
    if resolved_agency:
        contact_data["agency"] = resolved_agency
    if payload.rfp_id:
        contact_data["linked_rfp_ids"] = [payload.rfp_id]

    contact = OpportunityContact(
        user_id=current_user.id,
        **contact_data,
    )
    session.add(contact)
    await session.flush()
    await _upsert_agency_contact_directory(
        session=session,
        user_id=current_user.id,
        agency_name=contact.agency,
        primary_contact_id=contact.id,
    )

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


@router.post("/extract/{rfp_id}", response_model=list[ExtractedContactResponse])
async def extract_contacts(
    rfp_id: int,
    auto_link: bool = Query(True, description="Persist extracted contacts and link to opportunity"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExtractedContactResponse]:
    """AI-extract contacts from an RFP's full text."""
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == rfp_id, RFP.user_id == current_user.id)
    )
    rfp = rfp_result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Local/manual RFP records may only populate description before full-text extraction runs.
    text = (rfp.full_text or rfp.description or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="RFP has no text content to extract from")

    extracted = await extract_contacts_from_text(text)
    if auto_link and extracted:
        for item in extracted:
            existing = await _find_existing_contact_for_linking(
                session=session,
                user_id=current_user.id,
                name=item["name"],
                email=item.get("email"),
                agency=item.get("agency") or rfp.agency,
            )
            if existing:
                _merge_contact_links(existing, rfp.id)
                if not existing.agency:
                    existing.agency = item.get("agency") or rfp.agency
                _merge_contact_metadata(
                    existing,
                    role=item.get("role"),
                    organization=None,
                    phone=item.get("phone"),
                    notes=None,
                    title=item.get("title"),
                    department=None,
                    location=None,
                    source="ai_extracted",
                    extraction_confidence=0.9,
                )
                existing.updated_at = datetime.utcnow()
                await log_audit_event(
                    session,
                    user_id=current_user.id,
                    entity_type="contact",
                    entity_id=existing.id,
                    action="contact.linked",
                    metadata={"rfp_id": rfp.id, "name": existing.name, "source": "ai_extract"},
                )
                await _upsert_agency_contact_directory(
                    session=session,
                    user_id=current_user.id,
                    agency_name=existing.agency,
                    primary_contact_id=existing.id,
                )
                continue

            linked_contact = OpportunityContact(
                user_id=current_user.id,
                rfp_id=rfp.id,
                linked_rfp_ids=[rfp.id],
                name=item["name"],
                role=item.get("role"),
                email=item.get("email"),
                phone=item.get("phone"),
                agency=item.get("agency") or rfp.agency,
                title=item.get("title"),
                source="ai_extracted",
                extraction_confidence=0.9,
            )
            session.add(linked_contact)
            await session.flush()
            await log_audit_event(
                session,
                user_id=current_user.id,
                entity_type="contact",
                entity_id=linked_contact.id,
                action="contact.created",
                metadata={"rfp_id": rfp.id, "name": linked_contact.name, "source": "ai_extract"},
            )
            await _upsert_agency_contact_directory(
                session=session,
                user_id=current_user.id,
                agency_name=linked_contact.agency,
                primary_contact_id=linked_contact.id,
            )

        await session.commit()

    return [ExtractedContactResponse(**c) for c in extracted]


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------


@router.get("/search", response_model=list[ContactResponse])
async def search_contacts(
    agency: str | None = Query(None),
    role: str | None = Query(None),
    location: str | None = Query(None),
    name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ContactResponse]:
    """Search contacts by agency, role, location, or name."""
    query = select(OpportunityContact).where(OpportunityContact.user_id == current_user.id)
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


@router.get("/agencies", response_model=list[AgencyResponse])
async def list_agencies(
    limit: int = Query(50, ge=1, le=200),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AgencyResponse]:
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
