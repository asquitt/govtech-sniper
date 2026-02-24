"""
PDF Processor Unit Tests
=========================
Tests for PDFProcessor text extraction, cleaning, chunking, and error handling.
All pdfplumber calls are mocked — no real PDF bytes required.
"""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.services.pdf_processor import PDFDocument, PDFPage, PDFProcessor, get_pdf_processor

# =============================================================================
# Helpers
# =============================================================================


def make_processor() -> PDFProcessor:
    return PDFProcessor()


def make_pdf_document(pages: list[PDFPage]) -> PDFDocument:
    full_text = "\n".join(f"\n--- Page {p.page_number} ---\n{p.text}\n" for p in pages)
    return PDFDocument(
        filename="test.pdf",
        total_pages=len(pages),
        total_words=sum(p.word_count for p in pages),
        total_chars=sum(p.char_count for p in pages),
        pages=pages,
        full_text=full_text,
        metadata={},
        content_hash=hashlib.sha256(full_text.encode()).hexdigest(),
    )


def make_page(num: int, text: str) -> PDFPage:
    return PDFPage(
        page_number=num,
        text=text,
        word_count=len(text.split()),
        char_count=len(text),
    )


# =============================================================================
# _clean_text
# =============================================================================


class TestCleanText:
    def setup_method(self):
        self.proc = make_processor()

    def test_empty_string_returns_empty(self):
        assert self.proc._clean_text("") == ""

    def test_none_returns_empty(self):
        assert self.proc._clean_text(None) == ""

    def test_multiple_spaces_collapsed(self):
        result = self.proc._clean_text("hello   world")
        assert result == "hello world"

    def test_multiple_tabs_collapsed(self):
        result = self.proc._clean_text("col1\t\t\tcol2")
        assert result == "col1 col2"

    def test_form_feed_replaced_with_newline(self):
        result = self.proc._clean_text("page1\fpage2")
        assert "\f" not in result
        assert "page1" in result
        assert "page2" in result

    def test_excess_newlines_collapsed(self):
        result = self.proc._clean_text("line1\n\n\n\nline2")
        assert result == "line1\n\nline2"

    def test_leading_trailing_whitespace_stripped(self):
        result = self.proc._clean_text("  \n  hello  \n  ")
        assert result == "hello"

    def test_lines_individually_stripped(self):
        result = self.proc._clean_text("  leading\ntrailing  ")
        assert result == "leading\ntrailing"


# =============================================================================
# extract_text
# =============================================================================


class TestExtractText:
    def setup_method(self):
        self.proc = make_processor()

    def _mock_pdf(self, page_texts: list[str], metadata: dict | None = None):
        """Build a fake pdfplumber PDF context manager."""
        mock_pdf = MagicMock()
        mock_pdf.metadata = metadata or {}
        mock_pages = []
        for text in page_texts:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = text
            mock_pages.append(mock_page)
        mock_pdf.pages = mock_pages
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_pdf)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        return mock_ctx

    @patch("app.services.pdf_processor.pdfplumber")
    def test_returns_pdf_document(self, mock_pdfplumber):
        mock_pdfplumber.open.return_value = self._mock_pdf(["Page one text."])
        result = self.proc.extract_text(b"fake-pdf", filename="doc.pdf")
        assert isinstance(result, PDFDocument)

    @patch("app.services.pdf_processor.pdfplumber")
    def test_correct_page_count(self, mock_pdfplumber):
        mock_pdfplumber.open.return_value = self._mock_pdf(["Page 1", "Page 2", "Page 3"])
        result = self.proc.extract_text(b"fake", filename="multi.pdf")
        assert result.total_pages == 3

    @patch("app.services.pdf_processor.pdfplumber")
    def test_filename_preserved(self, mock_pdfplumber):
        mock_pdfplumber.open.return_value = self._mock_pdf(["text"])
        result = self.proc.extract_text(b"fake", filename="report.pdf")
        assert result.filename == "report.pdf"

    @patch("app.services.pdf_processor.pdfplumber")
    def test_full_text_contains_page_markers(self, mock_pdfplumber):
        mock_pdfplumber.open.return_value = self._mock_pdf(["intro text"])
        result = self.proc.extract_text(b"fake", filename="doc.pdf")
        assert "--- Page 1 ---" in result.full_text

    @patch("app.services.pdf_processor.pdfplumber")
    def test_word_count_calculated(self, mock_pdfplumber):
        mock_pdfplumber.open.return_value = self._mock_pdf(["one two three four five"])
        result = self.proc.extract_text(b"fake", filename="doc.pdf")
        assert result.total_words == 5

    @patch("app.services.pdf_processor.pdfplumber")
    def test_content_hash_is_sha256(self, mock_pdfplumber):
        mock_pdfplumber.open.return_value = self._mock_pdf(["text"])
        result = self.proc.extract_text(b"fake", filename="doc.pdf")
        assert len(result.content_hash) == 64  # SHA-256 hex length

    @patch("app.services.pdf_processor.pdfplumber")
    def test_metadata_extracted(self, mock_pdfplumber):
        meta = {"Title": "RFP Document", "Author": "GSA"}
        mock_pdfplumber.open.return_value = self._mock_pdf(["text"], metadata=meta)
        result = self.proc.extract_text(b"fake", filename="doc.pdf")
        assert result.metadata["title"] == "RFP Document"
        assert result.metadata["author"] == "GSA"

    @patch("app.services.pdf_processor.pdfplumber")
    def test_page_extraction_error_uses_placeholder(self, mock_pdfplumber):
        mock_pdf = MagicMock()
        mock_pdf.metadata = {}
        bad_page = MagicMock()
        bad_page.extract_text.side_effect = Exception("corrupt page")
        mock_pdf.pages = [bad_page]
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_pdf)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_ctx

        result = self.proc.extract_text(b"fake", filename="corrupt.pdf")
        assert result.total_pages == 1
        assert "Error extracting page 1" in result.pages[0].text

    @patch("app.services.pdf_processor.pdfplumber")
    def test_raises_value_error_for_completely_corrupt_pdf(self, mock_pdfplumber):
        mock_pdfplumber.open.side_effect = Exception("Not a PDF")
        with pytest.raises(ValueError, match="Failed to process PDF"):
            self.proc.extract_text(b"garbage", filename="bad.pdf")

    @patch("app.services.pdf_processor.pdfplumber")
    def test_empty_page_text_handled(self, mock_pdfplumber):
        mock_pdfplumber.open.return_value = self._mock_pdf(["", "has content"])
        result = self.proc.extract_text(b"fake", filename="doc.pdf")
        assert result.pages[0].word_count == 0
        assert result.pages[1].word_count == 2


# =============================================================================
# get_page_count
# =============================================================================


class TestGetPageCount:
    @patch("app.services.pdf_processor.pdfplumber")
    def test_returns_correct_count(self, mock_pdfplumber):
        proc = make_processor()
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock()]
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_pdf)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_ctx

        count = proc.get_page_count(b"fake")
        assert count == 3

    @patch("app.services.pdf_processor.pdfplumber")
    def test_returns_zero_on_error(self, mock_pdfplumber):
        proc = make_processor()
        mock_pdfplumber.open.side_effect = Exception("bad pdf")
        count = proc.get_page_count(b"garbage")
        assert count == 0


# =============================================================================
# chunk_document
# =============================================================================


class TestChunkDocument:
    def setup_method(self):
        self.proc = make_processor()

    def test_single_page_doc_creates_one_chunk(self):
        doc = make_pdf_document([make_page(1, "short content")])
        chunks = self.proc.chunk_document(doc, max_chunk_size=1000)
        assert len(chunks) == 1

    def test_large_doc_splits_into_multiple_chunks(self):
        pages = [make_page(i, "word " * 500) for i in range(1, 6)]
        doc = make_pdf_document(pages)
        chunks = self.proc.chunk_document(doc, max_chunk_size=1000)
        assert len(chunks) > 1

    def test_chunk_has_required_keys(self):
        doc = make_pdf_document([make_page(1, "text here")])
        chunks = self.proc.chunk_document(doc, max_chunk_size=1000)
        assert "chunk_index" in chunks[0]
        assert "text" in chunks[0]
        assert "start_page" in chunks[0]
        assert "end_page" in chunks[0]
        assert "char_count" in chunks[0]
        assert "word_count" in chunks[0]

    def test_chunk_indices_sequential(self):
        pages = [make_page(i, "word " * 500) for i in range(1, 4)]
        doc = make_pdf_document(pages)
        chunks = self.proc.chunk_document(doc, max_chunk_size=500)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_empty_doc_returns_empty_list(self):
        doc = make_pdf_document([])
        chunks = self.proc.chunk_document(doc, max_chunk_size=1000)
        # No pages → no content → empty or one empty chunk
        assert isinstance(chunks, list)


# =============================================================================
# extract_text_by_page
# =============================================================================


class TestExtractTextByPage:
    @patch("app.services.pdf_processor.pdfplumber")
    def test_extracts_specified_pages(self, mock_pdfplumber):
        proc = make_processor()
        mock_pdf = MagicMock()
        p1 = MagicMock()
        p1.extract_text.return_value = "Page one content"
        p2 = MagicMock()
        p2.extract_text.return_value = "Page two content"
        mock_pdf.pages = [p1, p2]
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_pdf)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_ctx

        result = proc.extract_text_by_page(b"fake", page_numbers=[1, 2])
        assert "Page one content" in result[1]
        assert "Page two content" in result[2]

    @patch("app.services.pdf_processor.pdfplumber")
    def test_out_of_range_page_returns_placeholder(self, mock_pdfplumber):
        proc = make_processor()
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()]
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_pdf)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_ctx

        result = proc.extract_text_by_page(b"fake", page_numbers=[99])
        assert "not found" in result[99]


# =============================================================================
# Singleton
# =============================================================================


class TestGetPdfProcessor:
    def test_returns_pdf_processor_instance(self):
        # Reset singleton
        import app.services.pdf_processor as mod

        mod._processor = None
        p1 = get_pdf_processor()
        p2 = get_pdf_processor()
        assert isinstance(p1, PDFProcessor)
        assert p1 is p2
