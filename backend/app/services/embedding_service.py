"""Embedding generation and semantic search service.

Uses Gemini text-embedding-004 for production-quality semantic vectors.
Stores and queries via pgvector for efficient approximate nearest neighbor search.
Falls back to hash-based embeddings when GEMINI_API_KEY is not configured.
"""

import math
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.embedding import DocumentEmbedding

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 768
EMBEDDING_MODEL = "text-embedding-004"


def _join_non_empty(parts: list[str | None]) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())


def compose_rfp_text(
    *,
    title: str,
    solicitation_number: str | None,
    agency: str | None,
    sub_agency: str | None,
    naics_code: str | None,
    set_aside: str | None,
    description: str | None,
    full_text: str | None,
    summary: str | None,
) -> str:
    """Compose indexable RFP text from key metadata + content fields."""
    return _join_non_empty(
        [
            title,
            solicitation_number,
            agency,
            sub_agency,
            naics_code,
            set_aside,
            summary,
            description,
            full_text,
        ]
    )


def compose_proposal_section_text(
    *,
    title: str,
    section_number: str | None,
    requirement_text: str | None,
    final_content: str | None,
    generated_content_clean_text: str | None,
) -> str:
    """Compose indexable text for a proposal section."""
    return _join_non_empty(
        [
            title,
            section_number,
            requirement_text,
            final_content or generated_content_clean_text,
        ]
    )


def compose_knowledge_document_text(
    *,
    title: str,
    document_type: str | None,
    description: str | None,
    full_text: str | None,
) -> str:
    """Compose indexable knowledge-base document text."""
    return _join_non_empty([title, document_type, description, full_text])


def compose_contact_text(
    *,
    name: str,
    role: str | None,
    organization: str | None,
    agency: str | None,
    title: str | None,
    department: str | None,
    location: str | None,
    notes: str | None,
) -> str:
    """Compose indexable contact text."""
    return _join_non_empty([name, role, organization, agency, title, department, location, notes])


def _coerce_vector(value: Any) -> list[float] | None:
    """Normalize stored vectors from pgvector/SQLAlchemy into Python float lists."""
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, tuple):
        return [float(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("[") and text.endswith("]"):
            text = text[1:-1]
        if not text:
            return None
        try:
            return [float(item) for item in text.split(",")]
        except ValueError:
            return None

    to_list = getattr(value, "tolist", None)
    if callable(to_list):
        raw = to_list()
        if isinstance(raw, list):
            return [float(item) for item in raw]
        if isinstance(raw, tuple):
            return [float(item) for item in raw]
    return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity for fallback search on non-pgvector backends."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _supports_native_pgvector(session: AsyncSession) -> bool:
    bind = session.get_bind()
    if bind is None:
        return False
    return bind.dialect.name.startswith("postgresql")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


async def _gemini_embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via Gemini text-embedding-004 API.

    Batches up to 100 texts per request (API limit).
    """
    import google.generativeai as genai

    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set, using fallback embeddings")
        return [_fallback_embedding(t) for t in texts]

    genai.configure(api_key=settings.gemini_api_key)

    embeddings: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            result = genai.embed_content(
                model=f"models/{EMBEDDING_MODEL}",
                content=batch,
                task_type="RETRIEVAL_DOCUMENT",
            )
            batch_embeddings = result["embedding"]
            if isinstance(batch_embeddings[0], float):
                # Single text returns flat list
                embeddings.append(batch_embeddings)
            else:
                embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error("Gemini embedding failed, using fallback", error=str(e))
            embeddings.extend([_fallback_embedding(t) for t in batch])

    return embeddings


async def _gemini_embed_query(text: str) -> list[float]:
    """Generate query embedding (uses RETRIEVAL_QUERY task type)."""
    import google.generativeai as genai

    if not settings.gemini_api_key:
        return _fallback_embedding(text)

    genai.configure(api_key=settings.gemini_api_key)

    try:
        result = genai.embed_content(
            model=f"models/{EMBEDDING_MODEL}",
            content=text,
            task_type="RETRIEVAL_QUERY",
        )
        return result["embedding"]
    except Exception as e:
        logger.error("Gemini query embedding failed", error=str(e))
        return _fallback_embedding(text)


def _fallback_embedding(text: str) -> list[float]:
    """Hash-based fallback embedding when Gemini is unavailable."""
    words = text.lower().split()
    if not words:
        return [0.0] * EMBEDDING_DIM

    embedding = [0.0] * EMBEDDING_DIM
    for word in words:
        h = hash(word) % EMBEDDING_DIM
        embedding[h] += 1.0

    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]
    return embedding


async def index_entity(
    session: AsyncSession,
    user_id: int,
    entity_type: str,
    entity_id: int,
    text: str,
) -> int:
    """Chunk, embed, and store text for an entity. Returns chunk count."""
    # Remove existing embeddings
    existing = await session.execute(
        select(DocumentEmbedding).where(
            DocumentEmbedding.user_id == user_id,
            DocumentEmbedding.entity_type == entity_type,
            DocumentEmbedding.entity_id == entity_id,
        )
    )
    for emb in existing.scalars().all():
        await session.delete(emb)

    chunks = _chunk_text(text)
    if not chunks:
        return 0

    # Batch embed all chunks
    embeddings = await _gemini_embed(chunks)

    for i, (chunk, emb_vector) in enumerate(zip(chunks, embeddings, strict=False)):
        doc_emb = DocumentEmbedding(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            chunk_text=chunk,
            chunk_index=i,
            embedding=emb_vector,
        )
        session.add(doc_emb)

    await session.flush()
    return len(chunks)


async def delete_entity_embeddings(
    session: AsyncSession,
    *,
    user_id: int,
    entity_type: str,
    entity_id: int,
) -> int:
    """Delete embeddings for a single entity. Returns number of rows removed."""
    result = await session.execute(
        select(DocumentEmbedding).where(
            DocumentEmbedding.user_id == user_id,
            DocumentEmbedding.entity_type == entity_type,
            DocumentEmbedding.entity_id == entity_id,
        )
    )
    rows = result.scalars().all()
    for row in rows:
        await session.delete(row)
    await session.flush()
    return len(rows)


async def search(
    session: AsyncSession,
    user_id: int,
    query: str,
    entity_types: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    """Semantic search across indexed entities with pgvector + portable fallback."""
    query_embedding = await _gemini_embed_query(query)

    base_stmt = select(DocumentEmbedding).where(
        DocumentEmbedding.user_id == user_id,
        DocumentEmbedding.embedding.is_not(None),
    )
    if entity_types:
        base_stmt = base_stmt.where(DocumentEmbedding.entity_type.in_(entity_types))

    # PostgreSQL + pgvector path (ANN + cosine distance in SQL).
    if _supports_native_pgvector(session):
        stmt = (
            select(
                DocumentEmbedding.entity_type,
                DocumentEmbedding.entity_id,
                DocumentEmbedding.chunk_text,
                DocumentEmbedding.chunk_index,
                DocumentEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(
                DocumentEmbedding.user_id == user_id,
                DocumentEmbedding.embedding.is_not(None),
            )
            .order_by("distance")
            .limit(limit)
        )

        if entity_types:
            stmt = stmt.where(DocumentEmbedding.entity_type.in_(entity_types))

        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "chunk_text": row.chunk_text,
                "score": round(1.0 - row.distance, 4),  # Convert distance to similarity
                "chunk_index": row.chunk_index,
            }
            for row in rows
        ]

    # Fallback path for SQLite/non-pgvector environments.
    result = await session.execute(base_stmt)
    rows = result.scalars().all()
    scored: list[dict] = []
    for row in rows:
        vec = _coerce_vector(row.embedding)
        if not vec:
            continue
        similarity = _cosine_similarity(vec, query_embedding)
        scored.append(
            {
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "score": round(similarity, 4),
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]
