"""Semantic search routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.deps import get_current_user
from app.services.auth_service import UserAuth
from app.services.embedding_service import search
from app.schemas.search import SearchRequest, SearchResult, SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/", response_model=SearchResponse)
async def semantic_search(
    payload: SearchRequest,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """Perform semantic search across indexed entities."""
    results = await search(
        session,
        query=payload.query,
        entity_types=payload.entity_types,
        limit=payload.limit,
    )
    return SearchResponse(
        query=payload.query,
        results=[SearchResult(**r) for r in results],
        total=len(results),
    )
