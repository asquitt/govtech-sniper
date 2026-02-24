"""
RFP Route Helper Unit Tests
=============================
Tests for pure helper functions in rfps.py route module.
"""

from app.api.routes.rfps.helpers import _as_text, _impact_level, _impact_profile, _tokenize


class TestAsText:
    def test_none_returns_empty(self):
        assert _as_text(None) == ""

    def test_string_passthrough(self):
        assert _as_text("hello") == "hello"

    def test_integer_converted(self):
        assert _as_text(42) == "42"


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = _tokenize("Cybersecurity IT Services 2025")
        assert "cybersecurity" in tokens
        assert "services" in tokens
        assert "2025" in tokens

    def test_short_words_excluded(self):
        tokens = _tokenize("IT is a good idea")
        assert "is" not in tokens  # too short (< 3 chars)
        assert "good" in tokens

    def test_empty_string(self):
        tokens = _tokenize("")
        assert tokens == set()


class TestImpactLevel:
    def test_high(self):
        assert _impact_level(70) == "high"
        assert _impact_level(100) == "high"

    def test_medium(self):
        assert _impact_level(40) == "medium"
        assert _impact_level(69) == "medium"

    def test_low(self):
        assert _impact_level(0) == "low"
        assert _impact_level(39) == "low"


class TestImpactProfile:
    def test_known_field(self):
        area, severity, actions = _impact_profile("response_deadline")
        assert area == "timeline"
        assert severity == "high"
        assert len(actions) > 0

    def test_unknown_field_defaults(self):
        area, severity, actions = _impact_profile("some_random_field")
        assert area == "scope"
        assert severity == "low"
        assert len(actions) > 0

    def test_naics_code_is_eligibility(self):
        area, severity, actions = _impact_profile("naics_code")
        assert area == "eligibility"
        assert severity == "high"
