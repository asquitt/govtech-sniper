"""
RFP Sniper - PDF Processing Service
=====================================
Extract text and metadata from PDF documents.
"""

import hashlib
import io
from dataclasses import dataclass
from typing import Any

import pdfplumber
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PDFPage:
    """Single page extracted from PDF."""

    page_number: int
    text: str
    word_count: int
    char_count: int


@dataclass
class PDFDocument:
    """Extracted PDF document data."""

    filename: str
    total_pages: int
    total_words: int
    total_chars: int
    pages: list[PDFPage]
    full_text: str
    metadata: dict[str, Any]
    content_hash: str


class PDFProcessor:
    """
    Service for extracting text from PDF documents.

    Uses pdfplumber for reliable text extraction with layout preservation.
    """

    def __init__(self):
        """Initialize the PDF processor."""
        pass

    def extract_text(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
    ) -> PDFDocument:
        """
        Extract text from PDF bytes.

        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Original filename for reference

        Returns:
            PDFDocument with extracted text and metadata
        """
        logger.info(f"Processing PDF: {filename}", size_bytes=len(pdf_bytes))

        pages: list[PDFPage] = []
        full_text_parts: list[str] = []
        metadata: dict[str, Any] = {}

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                # Extract metadata
                metadata = {
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "creator": pdf.metadata.get("Creator", ""),
                    "producer": pdf.metadata.get("Producer", ""),
                    "creation_date": str(pdf.metadata.get("CreationDate", "")),
                }

                # Process each page
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract text with layout preservation
                        text = (
                            page.extract_text(
                                layout=True,
                                x_tolerance=3,
                                y_tolerance=3,
                            )
                            or ""
                        )

                        # Clean up text
                        text = self._clean_text(text)

                        word_count = len(text.split())
                        char_count = len(text)

                        # Add page marker for citation tracking
                        page_text = f"\n--- Page {page_num} ---\n{text}\n"
                        full_text_parts.append(page_text)

                        pages.append(
                            PDFPage(
                                page_number=page_num,
                                text=text,
                                word_count=word_count,
                                char_count=char_count,
                            )
                        )

                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {e}")
                        pages.append(
                            PDFPage(
                                page_number=page_num,
                                text=f"[Error extracting page {page_num}]",
                                word_count=0,
                                char_count=0,
                            )
                        )

                full_text = "\n".join(full_text_parts)

                # Calculate content hash
                content_hash = hashlib.sha256(full_text.encode()).hexdigest()

                total_words = sum(p.word_count for p in pages)
                total_chars = sum(p.char_count for p in pages)

                logger.info(
                    "PDF extraction complete",
                    filename=filename,
                    pages=len(pages),
                    words=total_words,
                )

                return PDFDocument(
                    filename=filename,
                    total_pages=len(pages),
                    total_words=total_words,
                    total_chars=total_chars,
                    pages=pages,
                    full_text=full_text,
                    metadata=metadata,
                    content_hash=content_hash,
                )

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}", filename=filename)
            raise ValueError(f"Failed to process PDF: {e}")

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Replace multiple spaces/tabs with single space
        import re

        text = re.sub(r"[ \t]+", " ", text)

        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove form feed characters
        text = text.replace("\f", "\n")

        # Strip leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    def extract_text_by_page(
        self,
        pdf_bytes: bytes,
        page_numbers: list[int],
        filename: str = "document.pdf",
    ) -> dict[int, str]:
        """
        Extract text from specific pages.

        Args:
            pdf_bytes: Raw PDF bytes
            page_numbers: List of page numbers (1-indexed)
            filename: Original filename

        Returns:
            Dict mapping page number to text
        """
        result: dict[int, str] = {}

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num in page_numbers:
                    if 1 <= page_num <= len(pdf.pages):
                        page = pdf.pages[page_num - 1]
                        text = page.extract_text(layout=True) or ""
                        result[page_num] = self._clean_text(text)
                    else:
                        result[page_num] = f"[Page {page_num} not found]"

        except Exception as e:
            logger.error(f"Page extraction failed: {e}")
            for page_num in page_numbers:
                result[page_num] = "[Error extracting page]"

        return result

    def get_page_count(self, pdf_bytes: bytes) -> int:
        """
        Get the number of pages in a PDF.

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            Page count
        """
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0

    def chunk_document(
        self,
        document: PDFDocument,
        max_chunk_size: int = 8000,
        overlap: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Split document into chunks for processing.

        Args:
            document: Extracted PDF document
            max_chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks

        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_start_page = 1

        for page in document.pages:
            page_text = f"[Page {page.page_number}]\n{page.text}\n"
            page_size = len(page_text)

            if current_size + page_size > max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    {
                        "chunk_index": len(chunks),
                        "text": chunk_text,
                        "start_page": chunk_start_page,
                        "end_page": page.page_number - 1,
                        "char_count": len(chunk_text),
                        "word_count": len(chunk_text.split()),
                    }
                )

                # Start new chunk with overlap
                if overlap > 0 and len(chunk_text) > overlap:
                    current_chunk = [chunk_text[-overlap:]]
                    current_size = overlap
                else:
                    current_chunk = []
                    current_size = 0

                chunk_start_page = page.page_number

            current_chunk.append(page_text)
            current_size += page_size

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "text": chunk_text,
                    "start_page": chunk_start_page,
                    "end_page": document.total_pages,
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                }
            )

        logger.info(
            "Document chunked",
            filename=document.filename,
            total_chunks=len(chunks),
        )

        return chunks


# Singleton instance
_processor: PDFProcessor | None = None


def get_pdf_processor() -> PDFProcessor:
    """Get or create PDF processor singleton."""
    global _processor
    if _processor is None:
        _processor = PDFProcessor()
    return _processor
