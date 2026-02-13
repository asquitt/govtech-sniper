"""
RFP Sniper - API Utilities
============================
Shared helpers for route handlers.
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel


async def get_or_404[T: SQLModel](
    session: AsyncSession,
    model: type[T],
    id: int,
    detail: str = "Not found",
) -> T:
    """Fetch a model instance by primary key, raising 404 if not found."""
    obj = await session.get(model, id)
    if not obj:
        raise HTTPException(status_code=404, detail=detail)
    return obj
