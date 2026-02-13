"""
Template CRUD and usage endpoints.
"""

import re

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session

from .models import ProposalTemplate, TemplateCreate, TemplateResponse
from .utils import _ensure_system_templates, _to_template_response

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    subcategory: str | None = Query(None, description="Filter by subcategory"),
    search: str | None = Query(None, description="Search in name and keywords"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TemplateResponse]:
    """
    List all available templates.
    Includes system templates and user's custom templates.
    """
    await _ensure_system_templates(session)

    query = select(ProposalTemplate).where(
        (ProposalTemplate.is_system == True) | (ProposalTemplate.user_id == current_user.id)
    )

    if category:
        query = query.where(ProposalTemplate.category == category)
    if subcategory:
        query = query.where(ProposalTemplate.subcategory == subcategory)

    result = await session.execute(query.order_by(ProposalTemplate.category, ProposalTemplate.name))
    templates = list(result.scalars().all())

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        templates = [
            t
            for t in templates
            if search_lower in t.name.lower()
            or any(search_lower in kw.lower() for kw in t.keywords)
        ]

    return [_to_template_response(t) for t in templates]


@router.get("/categories")
async def list_categories(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """
    List all template categories.
    """
    await _ensure_system_templates(session)
    result = await session.execute(select(ProposalTemplate.category).distinct())
    categories = [row[0] for row in result.all()]
    return sorted(categories)


@router.get("/categories/list", include_in_schema=False)
async def list_categories_legacy(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """
    Backward-compatible alias for older frontend clients.
    """
    await _ensure_system_templates(session)
    result = await session.execute(select(ProposalTemplate.category).distinct())
    categories = [row[0] for row in result.all()]
    return sorted(categories)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TemplateResponse:
    """
    Get a specific template by ID.
    """
    await _ensure_system_templates(session)

    result = await session.execute(
        select(ProposalTemplate).where(ProposalTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access
    if not template.is_system and template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _to_template_response(template)


@router.post("/", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TemplateResponse:
    """
    Create a custom template.
    """
    template = ProposalTemplate(
        name=request.name,
        category=request.category,
        subcategory=request.subcategory,
        description=request.description,
        template_text=request.template_text,
        placeholders=request.placeholders,
        keywords=request.keywords,
        is_system=False,
        user_id=current_user.id,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)

    logger.info("Template created", template_id=template.id, user_id=current_user.id)

    return _to_template_response(template)


@router.post("/{template_id}/use")
async def use_template(
    template_id: int,
    placeholders: dict,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Use a template with provided placeholder values.
    Returns the filled-in template text.
    """
    await _ensure_system_templates(session)

    result = await session.execute(
        select(ProposalTemplate).where(ProposalTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not template.is_system and template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Fill in placeholders
    filled_text = template.template_text
    for key, value in placeholders.items():
        filled_text = filled_text.replace(f"{{{key}}}", str(value))

    # Update usage count
    template.usage_count += 1
    await session.commit()

    # Check for unfilled placeholders
    unfilled = re.findall(r"\{(\w+)\}", filled_text)

    return {
        "filled_text": filled_text,
        "unfilled_placeholders": unfilled,
    }


@router.post("/seed-system-templates")
async def seed_system_templates(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Seed the database with system templates.
    This endpoint should be called during initial setup.
    """
    before_result = await session.execute(
        select(sa_func.count()).where(ProposalTemplate.is_system == True)
    )
    before_count = before_result.scalar() or 0

    await _ensure_system_templates(session)

    after_result = await session.execute(
        select(sa_func.count()).where(ProposalTemplate.is_system == True)
    )
    after_count = after_result.scalar() or 0
    created = max(0, after_count - before_count)

    logger.info("Seeded system templates", created=created, total=after_count)

    return {
        "message": f"Created {created} system templates",
        "total_system_templates": after_count,
    }
