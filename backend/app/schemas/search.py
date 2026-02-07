"""Search schemas."""


from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(min_length=1, max_length=500)
    entity_types: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    """Single search result."""

    entity_type: str
    entity_id: int
    chunk_text: str
    score: float
    chunk_index: int


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    results: list[SearchResult]
    total: int
