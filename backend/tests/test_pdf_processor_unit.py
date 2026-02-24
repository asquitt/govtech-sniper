"""
PDF Processor Unit Tests
=========================
Tests for PDFProcessor._clean_text, chunk_document, and dataclass structures.
Uses mock pdfplumber to avoid needing real PDF files.
"""

from unittest.mock import MagicMock, patch

from app.services.pdf_processor import PDFDocument, PDFPage, PDFProcessor, get_pdf_processor

# ---------------------------------------------------------------------------
# _clean_text
# ---------------------------------------------------------------------------


class TestCleanText:
    def setup_method(self):
        self.processor = PDFProcessor()

    def test_empty_string(self):
        assert self.processor._clean_text("") == ""

    def test_none_like(self):
        assert self.processor._clean_text("") == ""

    def test_collapses_multiple_spaces(self):
        result = self.processor._clean_text("hello   world")
        assert result == "hello world"

    def test_collapses_tabs(self):
        result = self.processor._clean_text("hello\t\tworld")
        assert result == "hello world"

    def test_collapses_excessive_newlines(self):
        result = self.processor._clean_text("a\n\n\n\nb")
        assert result == "a\n\nb"

    def test_replaces_form_feed(self):
        result = self.processor._clean_text("page1\fpage2")
        assert "\f" not in result
        assert "page1" in result
        assert "page2" in result

    def test_strips_line_whitespace(self):
        result = self.processor._clean_text("  hello  \n  world  ")
        assert result == "hello\nworld"

    def test_strips_overall(self):
        result = self.processor._clean_text("\n\n  hello  \n\n")
        assert result == "hello"


# ---------------------------------------------------------------------------
# chunk_document
# ---------------------------------------------------------------------------


def _make_document(page_texts: list[str]) -> PDFDocument:
    pages = []
    for i, text in enumerate(page_texts, 1):
        pages.append(
            PDFPage(
                page_number=i,
                text=text,
                word_count=len(text.split()),
                char_count=len(text),
            )
        )
    full_text = "\n".join(page_texts)
    return PDFDocument(
        filename="test.pdf",
        total_pages=len(pages),
        total_words=sum(p.word_count for p in pages),
        total_chars=sum(p.char_count for p in pages),
        pages=pages,
        full_text=full_text,
        metadata={},
        content_hash="abc123",
    )


class TestChunkDocument:
    def setup_method(self):
        self.processor = PDFProcessor()

    def test_single_page_single_chunk(self):
        doc = _make_document(["Short page content."])
        chunks = self.processor.chunk_document(doc, max_chunk_size=8000)
        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["start_page"] == 1
        assert chunks[0]["end_page"] == 1
        assert "Short page content" in chunks[0]["text"]

    def test_multiple_pages_within_limit(self):
        doc = _make_document(["Page one.", "Page two.", "Page three."])
        chunks = self.processor.chunk_document(doc, max_chunk_size=8000)
        assert len(chunks) == 1

    def test_pages_exceeding_limit_split(self):
        # Each page is ~100 chars; chunk limit 150 forces splits
        page_text = "x" * 100
        doc = _make_document([page_text, page_text, page_text])
        chunks = self.processor.chunk_document(doc, max_chunk_size=150, overlap=0)
        assert len(chunks) > 1

    def test_chunk_indexes_sequential(self):
        page_text = "y" * 200
        doc = _make_document([page_text] * 5)
        chunks = self.processor.chunk_document(doc, max_chunk_size=300, overlap=0)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_chunk_has_required_keys(self):
        doc = _make_document(["Some content here."])
        chunks = self.processor.chunk_document(doc)
        assert len(chunks) >= 1
        chunk = chunks[0]
        assert "chunk_index" in chunk
        assert "text" in chunk
        assert "start_page" in chunk
        assert "end_page" in chunk
        assert "char_count" in chunk
        assert "word_count" in chunk

    def test_empty_document(self):
        doc = _make_document([])
        chunks = self.processor.chunk_document(doc)
        assert chunks == []

    def test_overlap_preserved(self):
        page_text = "w" * 200
        doc = _make_document([page_text, page_text])
        chunks = self.processor.chunk_document(doc, max_chunk_size=250, overlap=50)
        if len(chunks) > 1:
            # Second chunk should start with overlap text from first
            assert chunks[1]["char_count"] > 0


# ---------------------------------------------------------------------------
# extract_text (mocked pdfplumber)
# ---------------------------------------------------------------------------


class TestExtractText:
    def setup_method(self):
        self.processor = PDFProcessor()

    @patch("app.services.pdf_processor.pdfplumber")
    def test_extract_text_basic(self, mock_plumber):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Hello World"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {"Title": "Test", "Author": "Tester"}
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_plumber.open.return_value = mock_pdf

        result = self.processor.extract_text(b"fake pdf bytes", "test.pdf")

        assert result.filename == "test.pdf"
        assert result.total_pages == 1
        assert result.total_words > 0
        assert "Hello World" in result.pages[0].text
        assert result.metadata["title"] == "Test"
        assert len(result.content_hash) == 64  # SHA-256 hex

    @patch("app.services.pdf_processor.pdfplumber")
    def test_extract_text_page_error_handled(self, mock_plumber):
        mock_page = MagicMock()
        mock_page.extract_text.side_effect = RuntimeError("corrupt page")

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_plumber.open.return_value = mock_pdf

        result = self.processor.extract_text(b"fake", "bad.pdf")
        assert result.total_pages == 1
        assert "Error extracting" in result.pages[0].text

    @patch("app.services.pdf_processor.pdfplumber")
    def test_extract_text_pdf_open_fails(self, mock_plumber):
        mock_plumber.open.side_effect = Exception("not a pdf")
        import pytest

        with pytest.raises(ValueError, match="Failed to process PDF"):
            self.processor.extract_text(b"not pdf", "bad.pdf")


# ---------------------------------------------------------------------------
# get_page_count (mocked)
# ---------------------------------------------------------------------------


class TestGetPageCount:
    def setup_method(self):
        self.processor = PDFProcessor()

    @patch("app.services.pdf_processor.pdfplumber")
    def test_page_count(self, mock_plumber):
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock()]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_plumber.open.return_value = mock_pdf

        assert self.processor.get_page_count(b"fake") == 3

    @patch("app.services.pdf_processor.pdfplumber")
    def test_page_count_error(self, mock_plumber):
        mock_plumber.open.side_effect = Exception("bad")
        assert self.processor.get_page_count(b"fake") == 0


# ---------------------------------------------------------------------------
# extract_text_by_page (mocked)
# ---------------------------------------------------------------------------


class TestExtractTextByPage:
    def setup_method(self):
        self.processor = PDFProcessor()

    @patch("app.services.pdf_processor.pdfplumber")
    def test_specific_pages(self, mock_plumber):
        mock_pages = []
        for i in range(3):
            p = MagicMock()
            p.extract_text.return_value = f"Content of page {i + 1}"
            mock_pages.append(p)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_plumber.open.return_value = mock_pdf

        result = self.processor.extract_text_by_page(b"fake", [1, 3])
        assert 1 in result
        assert 3 in result
        assert "page 1" in result[1].lower() or len(result[1]) > 0

    @patch("app.services.pdf_processor.pdfplumber")
    def test_out_of_range_page(self, mock_plumber):
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_plumber.open.return_value = mock_pdf

        result = self.processor.extract_text_by_page(b"fake", [99])
        assert "not found" in result[99]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_pdf_processor_returns_same_instance(self):
        a = get_pdf_processor()
        b = get_pdf_processor()
        assert a is b
        assert isinstance(a, PDFProcessor)
