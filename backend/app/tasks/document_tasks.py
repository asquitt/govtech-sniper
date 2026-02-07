"""
RFP Sniper - Document Processing Tasks
======================================
Celery tasks for extracting text and chunking knowledge base documents.
"""

import asyncio
import hashlib
import io
import os
from datetime import datetime
from typing import Any

import structlog

from app.database import get_celery_session_context
from app.models.knowledge_base import (
    DocumentChunk,
    KnowledgeBaseDocument,
    ProcessingStatus,
)
from app.services.pdf_processor import get_pdf_processor
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _extract_docx_text(file_bytes: bytes) -> str:
    try:
        from docx import Document as DocxDocument
    except ImportError as exc:
        raise RuntimeError("python-docx not installed") from exc

    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(paragraphs).strip()


@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.process_document",
    max_retries=2,
    default_retry_delay=60,
)
def process_document(self, document_id: int) -> dict:
    """
    Process a knowledge base document:
    - Extract text
    - Store metadata
    - Create chunks for citation tracking
    """
    task_id = self.request.id
    logger.info("Processing document", task_id=task_id, document_id=document_id)

    async def _process() -> dict:
        async with get_celery_session_context() as session:
            from sqlalchemy import delete
            from sqlmodel import select

            result = await session.execute(
                select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                return {"status": "error", "error": "Document not found"}

            # Mark as processing
            document.processing_status = ProcessingStatus.PROCESSING
            document.processing_error = None
            await session.commit()

            try:
                if not os.path.exists(document.file_path):
                    raise FileNotFoundError(f"File not found: {document.file_path}")

                with open(document.file_path, "rb") as f:
                    file_bytes = f.read()

                mime_type = (document.mime_type or "").lower()
                extension = os.path.splitext(document.original_filename)[1].lower()

                full_text = ""
                page_count = None
                extracted_metadata: dict[str, Any] = {}
                chunks: list[dict[str, Any]] = []

                if mime_type == "application/pdf" or extension == ".pdf":
                    pdf_processor = get_pdf_processor()
                    pdf_doc = pdf_processor.extract_text(
                        file_bytes,
                        filename=document.original_filename,
                    )
                    full_text = pdf_doc.full_text
                    page_count = pdf_doc.total_pages
                    extracted_metadata = pdf_doc.metadata or {}
                    chunks = pdf_processor.chunk_document(pdf_doc)

                elif mime_type == "text/plain" or extension in {".txt"}:
                    full_text = file_bytes.decode("utf-8", errors="ignore").strip()
                    page_count = 1
                    extracted_metadata = {"source": "text"}
                    chunks = [
                        {
                            "chunk_index": 0,
                            "text": full_text,
                            "start_page": 1,
                            "end_page": 1,
                            "char_count": len(full_text),
                            "word_count": len(full_text.split()),
                        }
                    ]

                elif (
                    mime_type
                    in {
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    }
                    or extension == ".docx"
                ):
                    full_text = _extract_docx_text(file_bytes)
                    page_count = 1
                    extracted_metadata = {"source": "docx"}
                    chunks = [
                        {
                            "chunk_index": 0,
                            "text": full_text,
                            "start_page": 1,
                            "end_page": 1,
                            "char_count": len(full_text),
                            "word_count": len(full_text.split()),
                        }
                    ]

                elif extension == ".doc":
                    raise ValueError("Legacy .doc files are not supported. Upload .docx or PDF.")
                else:
                    raise ValueError(f"Unsupported file type: {document.mime_type or extension}")

                if not full_text:
                    raise ValueError("No text extracted from document")

                # Clear existing chunks (if reprocessing)
                await session.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
                )

                # Persist chunks
                cursor = 0
                for chunk in chunks:
                    text = chunk.get("text", "")
                    start_char = cursor
                    end_char = cursor + len(text)
                    cursor = end_char

                    session.add(
                        DocumentChunk(
                            document_id=document.id,
                            content=text,
                            page_number=int(chunk.get("start_page", 1) or 1),
                            start_char=start_char,
                            end_char=end_char,
                            chunk_index=int(chunk.get("chunk_index", 0) or 0),
                            word_count=int(chunk.get("word_count", len(text.split())) or 0),
                            content_hash=_hash_content(text),
                        )
                    )

                # Update document
                document.full_text = full_text
                document.page_count = page_count
                document.extracted_metadata = extracted_metadata
                document.processing_status = ProcessingStatus.READY
                document.processed_at = datetime.utcnow()

                await session.commit()

                logger.info(
                    "Document processed",
                    document_id=document.id,
                    page_count=page_count,
                    chunks=len(chunks),
                )

                return {
                    "status": "completed",
                    "document_id": document.id,
                    "page_count": page_count,
                    "chunks": len(chunks),
                }

            except Exception as e:
                logger.error("Document processing failed", document_id=document.id, error=str(e))
                document.processing_status = ProcessingStatus.ERROR
                document.processing_error = str(e)[:1000]
                await session.commit()
                return {
                    "status": "error",
                    "document_id": document.id,
                    "error": str(e),
                }

    return run_async(_process())
