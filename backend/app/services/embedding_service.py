"""Embedding generation and semantic search service.

Uses Gemini text-embedding-004 for production-quality semantic vectors.
Stores and queries via pgvector for efficient approximate nearest neighbor search.
Falls back to hash-based embeddings when GEMINI_API_KEY is not configured.
"""

import math

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.embedding import DocumentEmbedding

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 768
EMBEDDING_MODEL = "text-embedding-004"


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
    entity_type: str,
    entity_id: int,
    text: str,
) -> int:
    """Chunk, embed, and store text for an entity. Returns chunk count."""
    # Remove existing embeddings
    existing = await session.execute(
        select(DocumentEmbedding).where(
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
            entity_type=entity_type,
            entity_id=entity_id,
            chunk_text=chunk,
            chunk_index=i,
            embedding=emb_vector,
        )
        session.add(doc_emb)

    await session.flush()
    return len(chunks)


async def search(
    session: AsyncSession,
    query: str,
    entity_types: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    """Semantic search across indexed entities using pgvector cosine distance."""
    query_embedding = await _gemini_embed_query(query)

    # Use pgvector cosine distance operator for efficient ANN search
    stmt = select(
        DocumentEmbedding.entity_type,
        DocumentEmbedding.entity_id,
        DocumentEmbedding.chunk_text,
        DocumentEmbedding.chunk_index,
        DocumentEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
    ).where(DocumentEmbedding.embedding != None)

    if entity_types:
        stmt = stmt.where(DocumentEmbedding.entity_type.in_(entity_types))

    stmt = stmt.order_by("distance").limit(limit)

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
