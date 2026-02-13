"""
Template helper functions.
"""

from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .constants import SYSTEM_TEMPLATES
from .models import ProposalTemplate, TemplateResponse

logger = structlog.get_logger(__name__)


def _to_template_response(template: ProposalTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        name=template.name,
        category=template.category,
        subcategory=template.subcategory,
        description=template.description,
        template_text=template.template_text,
        placeholders=template.placeholders,
        keywords=template.keywords,
        is_system=template.is_system,
        is_public=template.is_public,
        rating_sum=template.rating_sum,
        rating_count=template.rating_count,
        forked_from_id=template.forked_from_id,
        user_id=template.user_id,
        usage_count=template.usage_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


async def _ensure_system_templates(session: AsyncSession) -> None:
    created = 0
    updated = 0

    for template_data in SYSTEM_TEMPLATES:
        result = await session.execute(
            select(ProposalTemplate).where(
                ProposalTemplate.name == template_data["name"],
                ProposalTemplate.is_system == True,
            )
        )
        existing = result.scalars().first()
        desired_public = bool(template_data.get("is_public", False))
        if existing:
            if existing.is_public != desired_public:
                existing.is_public = desired_public
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                updated += 1
            continue

        template = ProposalTemplate(
            name=template_data["name"],
            category=template_data["category"],
            subcategory=template_data.get("subcategory"),
            description=template_data["description"],
            template_text=template_data["template_text"],
            placeholders=template_data["placeholders"],
            keywords=template_data["keywords"],
            is_system=True,
            is_public=desired_public,
        )
        session.add(template)
        created += 1

    if created or updated:
        await session.commit()
        logger.info("System templates synchronized", created=created, updated=updated)
