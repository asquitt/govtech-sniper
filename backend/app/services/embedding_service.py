"""Embedding generation and semantic search service."""

import json
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.embedding import DocumentEmbedding


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


def _simple_embedding(text: str) -> list[float]:
    """Generate a simple TF-based embedding for MVP.

    Uses word frequency hashing for basic similarity.
    Replace with Gemini text-embedding-004 in production.
    """
    words = text.lower().split()
    if not words:
        return [0.0] * 128

    # Simple hash-based embedding (128 dimensions)
    embedding = [0.0] * 128
    for word in words:
        h = hash(word) % 128
        embedding[h] += 1.0

    # L2 normalize
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]

    return embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


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
    for i, chunk in enumerate(chunks):
        embedding = _simple_embedding(chunk)
        doc_emb = DocumentEmbedding(
            entity_type=entity_type,
            entity_id=entity_id,
            chunk_text=chunk,
            chunk_index=i,
            embedding_json=json.dumps(embedding),
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
    """Semantic search across indexed entities."""
    query_embedding = _simple_embedding(query)

    stmt = select(DocumentEmbedding)
    if entity_types:
        stmt = stmt.where(DocumentEmbedding.entity_type.in_(entity_types))

    result = await session.execute(stmt)
    all_embeddings = result.scalars().all()

    scored: list[dict] = []
    for emb in all_embeddings:
        if not emb.embedding_json:
            continue
        doc_embedding = json.loads(emb.embedding_json)
        score = _cosine_similarity(query_embedding, doc_embedding)
        scored.append(
            {
                "entity_type": emb.entity_type,
                "entity_id": emb.entity_id,
                "chunk_text": emb.chunk_text,
                "score": round(score, 4),
                "chunk_index": emb.chunk_index,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
