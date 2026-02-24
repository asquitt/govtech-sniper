"""
Contact Extractor Unit Tests
==============================
Tests for pure helper functions in contact_extractor.py.
No Gemini API calls — tests _mock_extract, _normalize_contacts, _str_or_none.
"""

import pytest

from app.services.contact_extractor import (
    _mock_extract,
    _normalize_contacts,
    _str_or_none,
    extract_contacts_from_text,
)


class TestStrOrNone:
    def test_none_returns_none(self):
        assert _str_or_none(None) is None

    def test_empty_string_returns_none(self):
        assert _str_or_none("") is None

    def test_whitespace_returns_none(self):
        assert _str_or_none("   ") is None

    def test_valid_string(self):
        assert _str_or_none("hello") == "hello"

    def test_strips_whitespace(self):
        assert _str_or_none("  hello  ") == "hello"

    def test_integer_converted(self):
        assert _str_or_none(42) == "42"


class TestNormalizeContacts:
    def test_valid_contacts(self):
        raw = [
            {
                "name": "John Smith",
                "title": "Contracting Officer",
                "email": "john@gov.mil",
                "phone": "555-1234",
                "agency": "DoD",
                "role": "CO",
            }
        ]
        result = _normalize_contacts(raw)
        assert len(result) == 1
        assert result[0]["name"] == "John Smith"
        assert result[0]["email"] == "john@gov.mil"

    def test_skips_no_name(self):
        raw = [{"title": "Officer", "email": "a@b.com"}]
        result = _normalize_contacts(raw)
        assert len(result) == 0

    def test_skips_empty_name(self):
        raw = [{"name": "  ", "title": "Officer"}]
        result = _normalize_contacts(raw)
        assert len(result) == 0

    def test_skips_non_dict(self):
        raw = ["not a dict", 42, None]
        result = _normalize_contacts(raw)
        assert len(result) == 0

    def test_missing_fields_become_none(self):
        raw = [{"name": "Jane Doe"}]
        result = _normalize_contacts(raw)
        assert len(result) == 1
        assert result[0]["email"] is None
        assert result[0]["phone"] is None
        assert result[0]["agency"] is None


class TestMockExtract:
    def test_finds_contracting_officer(self):
        text = "The Contracting Officer for this solicitation is responsible."
        result = _mock_extract(text)
        assert len(result) == 1
        assert result[0]["role"] == "Contracting Officer"

    def test_finds_contract_specialist(self):
        text = "Contact the Contract Specialist for questions."
        result = _mock_extract(text)
        assert len(result) == 1

    def test_no_contacts(self):
        text = "This is a generic document about cybersecurity."
        result = _mock_extract(text)
        assert len(result) == 0


class TestExtractContactsFromText:
    @pytest.mark.asyncio
    async def test_empty_text_returns_empty(self):
        result = await extract_contacts_from_text("")
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_returns_empty(self):
        result = await extract_contacts_from_text("   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_mock_without_api_key(self):
        """Without Gemini API key, should use mock extraction."""
        text = "The Contracting Officer is responsible for administration."
        result = await extract_contacts_from_text(text)
        # Should use mock extraction since no API key in tests
        assert isinstance(result, list)
