"""
RFP Sniper - Template Marketplace Routes
==========================================
Browse, fork, rate, and publish templates in the marketplace.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import UserAuth, get_current_user
from app.api.routes.templates import ProposalTemplate, _ensure_system_templates
from app.database import get_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["Template Marketplace"])


# =============================================================================
# Schemas
# =============================================================================


class MarketplaceTemplateResponse(BaseModel):
    """Marketplace template response (includes rating/public fields)."""

    id: int
    name: str
    category: str
    subcategory: str | None
    description: str
    placeholders: dict
    keywords: list[str]
    usage_count: int
    is_public: bool
    rating_sum: int
    rating_count: int
    forked_from_id: int | None
    user_id: int | None
    created_at: datetime


class MarketplaceBrowseResponse(BaseModel):
    """Paginated marketplace browse response."""

    items: list[MarketplaceTemplateResponse]
    total: int


class RateRequest(BaseModel):
    """Rate a template."""

    rating: int  # 1-5


# =============================================================================
# Helpers
# =============================================================================


def _to_marketplace_response(t: ProposalTemplate) -> MarketplaceTemplateResponse:
    return MarketplaceTemplateResponse(
        id=t.id,
        name=t.name,
        category=t.category,
        subcategory=t.subcategory,
        description=t.description,
        placeholders=t.placeholders,
        keywords=t.keywords,
        usage_count=t.usage_count,
        is_public=t.is_public,
        rating_sum=t.rating_sum,
        rating_count=t.rating_count,
        forked_from_id=t.forked_from_id,
        user_id=t.user_id,
        created_at=t.created_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/marketplace", response_model=MarketplaceBrowseResponse)
async def browse_marketplace(
    q: str | None = Query(None, description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MarketplaceBrowseResponse:
    """Browse public templates in the marketplace."""
    await _ensure_system_templates(session)

    query = select(ProposalTemplate).where(ProposalTemplate.is_public == True)

    if category:
        query = query.where(ProposalTemplate.category == category)
    if q:
        q_like = f"%{q.strip()}%"
        query = query.where(
            (ProposalTemplate.name.ilike(q_like)) | (ProposalTemplate.description.ilike(q_like))
        )

    # Get total before pagination
    count_query = select(sa_func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply search filter, pagination, and ordering
    query = query.order_by(ProposalTemplate.usage_count.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    templates = list(result.scalars().all())

    return MarketplaceBrowseResponse(
        items=[_to_marketplace_response(t) for t in templates],
        total=total,
    )


@router.get("/marketplace/popular", response_model=list[MarketplaceTemplateResponse])
async def popular_templates(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MarketplaceTemplateResponse]:
    """Get top public templates by usage and rating."""
    await _ensure_system_templates(session)

    result = await session.execute(
        select(ProposalTemplate)
        .where(ProposalTemplate.is_public == True)
        .order_by((ProposalTemplate.usage_count + ProposalTemplate.rating_sum).desc())
        .limit(20)
    )
    templates = list(result.scalars().all())
    return [_to_marketplace_response(t) for t in templates]


@router.post("/{template_id}/publish", response_model=MarketplaceTemplateResponse)
async def publish_template(
    template_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MarketplaceTemplateResponse:
    """Publish a template to the marketplace (set is_public=True)."""
    result = await session.execute(
        select(ProposalTemplate).where(ProposalTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can publish a template")

    template.is_public = True
    template.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(template)

    logger.info("Template published", template_id=template.id, user_id=current_user.id)
    return _to_marketplace_response(template)


@router.post("/{template_id}/fork", response_model=MarketplaceTemplateResponse)
async def fork_template(
    template_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MarketplaceTemplateResponse:
    """Fork a public template into the user's library."""
    result = await session.execute(
        select(ProposalTemplate).where(ProposalTemplate.id == template_id)
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Template not found")
    if not original.is_public and original.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Template is not public")

    forked = ProposalTemplate(
        name=f"{original.name} (Fork)",
        category=original.category,
        subcategory=original.subcategory,
        description=original.description,
        template_text=original.template_text,
        placeholders=original.placeholders,
        keywords=original.keywords,
        is_system=False,
        user_id=current_user.id,
        forked_from_id=original.id,
    )

    session.add(forked)
    await session.commit()
    await session.refresh(forked)

    logger.info(
        "Template forked", original_id=template_id, fork_id=forked.id, user_id=current_user.id
    )
    return _to_marketplace_response(forked)


@router.post("/{template_id}/rate")
async def rate_template(
    template_id: int,
    request: RateRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Rate a public template (1-5)."""
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    result = await session.execute(
        select(ProposalTemplate).where(ProposalTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not template.is_public:
        raise HTTPException(status_code=400, detail="Can only rate public templates")

    template.rating_sum += request.rating
    template.rating_count += 1
    template.updated_at = datetime.utcnow()
    await session.commit()

    avg = template.rating_sum / template.rating_count if template.rating_count > 0 else 0
    return {"average_rating": round(avg, 2), "total_ratings": template.rating_count}
