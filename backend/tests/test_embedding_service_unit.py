"""
Embedding Service Unit Tests
==============================
Tests for compose helpers, _cosine_similarity, _fallback_embedding,
_chunk_text, and _coerce_vector — pure logic, no DB or API calls.
"""

import math

import pytest

from app.services.embedding_service import (
    EMBEDDING_DIM,
    _chunk_text,
    _coerce_vector,
    _cosine_similarity,
    _fallback_embedding,
    compose_contact_text,
    compose_knowledge_document_text,
    compose_proposal_section_text,
    compose_rfp_text,
)

# ---------------------------------------------------------------------------
# compose_rfp_text
# ---------------------------------------------------------------------------


class TestComposeRfpText:
    def test_all_fields(self):
        text = compose_rfp_text(
            title="Cyber RFP",
            solicitation_number="W912HV-24-S-0001",
            agency="DoD",
            sub_agency="Army",
            naics_code="541512",
            set_aside="8(a)",
            description="Provide IT services.",
            full_text="Full solicitation text here.",
            summary="Brief summary.",
        )
        assert "Cyber RFP" in text
        assert "W912HV" in text
        assert "DoD" in text
        assert "541512" in text
        assert "Brief summary" in text

    def test_none_fields_excluded(self):
        text = compose_rfp_text(
            title="Test",
            solicitation_number=None,
            agency=None,
            sub_agency=None,
            naics_code=None,
            set_aside=None,
            description=None,
            full_text=None,
            summary=None,
        )
        assert text == "Test"

    def test_empty_strings_excluded(self):
        text = compose_rfp_text(
            title="Test",
            solicitation_number="",
            agency="  ",
            sub_agency="",
            naics_code=None,
            set_aside=None,
            description=None,
            full_text=None,
            summary=None,
        )
        assert text == "Test"


# ---------------------------------------------------------------------------
# compose_proposal_section_text
# ---------------------------------------------------------------------------


class TestComposeProposalSectionText:
    def test_basic(self):
        text = compose_proposal_section_text(
            title="Technical Approach",
            section_number="3.1",
            requirement_text="Describe methodology",
            final_content="Our approach uses agile.",
            generated_content_clean_text=None,
        )
        assert "Technical Approach" in text
        assert "3.1" in text
        assert "agile" in text

    def test_prefers_final_over_generated(self):
        text = compose_proposal_section_text(
            title="Section",
            section_number=None,
            requirement_text=None,
            final_content="Final version",
            generated_content_clean_text="Generated version",
        )
        assert "Final version" in text
        assert "Generated version" not in text

    def test_falls_back_to_generated(self):
        text = compose_proposal_section_text(
            title="Section",
            section_number=None,
            requirement_text=None,
            final_content=None,
            generated_content_clean_text="Generated version",
        )
        assert "Generated version" in text


# ---------------------------------------------------------------------------
# compose_knowledge_document_text
# ---------------------------------------------------------------------------


class TestComposeKnowledgeDocumentText:
    def test_basic(self):
        text = compose_knowledge_document_text(
            title="Past Performance",
            document_type="capability_statement",
            description="Our company capabilities.",
            full_text="Detailed text of the document.",
        )
        assert "Past Performance" in text
        assert "capability_statement" in text


# ---------------------------------------------------------------------------
# compose_contact_text
# ---------------------------------------------------------------------------


class TestComposeContactText:
    def test_basic(self):
        text = compose_contact_text(
            name="John Doe",
            role="CO",
            organization="GSA",
            agency="General Services",
            title="Contracting Officer",
            department="FAS",
            location="DC",
            notes="Key contact for IT BPAs.",
        )
        assert "John Doe" in text
        assert "GSA" in text
        assert "BPAs" in text

    def test_all_none_except_name(self):
        text = compose_contact_text(
            name="Jane",
            role=None,
            organization=None,
            agency=None,
            title=None,
            department=None,
            location=None,
            notes=None,
        )
        assert text == "Jane"


# ---------------------------------------------------------------------------
# _coerce_vector
# ---------------------------------------------------------------------------


class TestCoerceVector:
    def test_none(self):
        assert _coerce_vector(None) is None

    def test_list(self):
        result = _coerce_vector([1, 2, 3])
        assert result == [1.0, 2.0, 3.0]

    def test_tuple(self):
        result = _coerce_vector((1.5, 2.5))
        assert result == [1.5, 2.5]

    def test_string_bracketed(self):
        result = _coerce_vector("[1.0,2.0,3.0]")
        assert result == [1.0, 2.0, 3.0]

    def test_string_no_brackets(self):
        result = _coerce_vector("1.0,2.0")
        assert result == [1.0, 2.0]

    def test_empty_string(self):
        assert _coerce_vector("") is None

    def test_empty_brackets(self):
        assert _coerce_vector("[]") is None

    def test_invalid_string(self):
        assert _coerce_vector("[a,b,c]") is None

    def test_numpy_like_with_tolist(self):
        class FakeArray:
            def tolist(self):
                return [1.0, 2.0, 3.0]

        result = _coerce_vector(FakeArray())
        assert result == [1.0, 2.0, 3.0]

    def test_tolist_returns_tuple(self):
        class FakeArray:
            def tolist(self):
                return (4.0, 5.0)

        result = _coerce_vector(FakeArray())
        assert result == [4.0, 5.0]

    def test_object_without_tolist(self):
        assert _coerce_vector(object()) is None


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_empty_vectors(self):
        assert _cosine_similarity([], []) == 0.0

    def test_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# _fallback_embedding
# ---------------------------------------------------------------------------


class TestFallbackEmbedding:
    def test_correct_dimension(self):
        emb = _fallback_embedding("some text here")
        assert len(emb) == EMBEDDING_DIM

    def test_normalized(self):
        emb = _fallback_embedding("some text here")
        magnitude = math.sqrt(sum(x * x for x in emb))
        assert magnitude == pytest.approx(1.0, abs=0.01)

    def test_empty_text(self):
        emb = _fallback_embedding("")
        assert len(emb) == EMBEDDING_DIM
        assert all(x == 0.0 for x in emb)

    def test_same_text_same_embedding(self):
        a = _fallback_embedding("hello world")
        b = _fallback_embedding("hello world")
        assert a == b

    def test_different_text_different_embedding(self):
        a = _fallback_embedding("cybersecurity")
        b = _fallback_embedding("construction")
        assert a != b


# ---------------------------------------------------------------------------
# _chunk_text
# ---------------------------------------------------------------------------


class TestChunkText:
    def test_short_text(self):
        chunks = _chunk_text("short", chunk_size=500)
        assert chunks == ["short"]

    def test_empty_text(self):
        assert _chunk_text("") == []
        assert _chunk_text(None) == []

    def test_exact_chunk_size(self):
        text = "a" * 500
        chunks = _chunk_text(text, chunk_size=500)
        assert len(chunks) == 1

    def test_splits_long_text(self):
        text = "x" * 1000
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) >= 2

    def test_overlap(self):
        text = "a" * 1000
        chunks = _chunk_text(text, chunk_size=500, overlap=100)
        # With overlap, chunks should share characters
        assert len(chunks) >= 2
        # Total covered chars should be less than sum of chunk sizes
        total_chars = sum(len(c) for c in chunks)
        assert total_chars > len(text)  # overlap means some chars counted twice

    def test_no_overlap(self):
        text = "b" * 1000
        chunks = _chunk_text(text, chunk_size=500, overlap=0)
        total_chars = sum(len(c) for c in chunks)
        assert total_chars == len(text)
