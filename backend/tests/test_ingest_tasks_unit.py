"""Unit tests for ingest_tasks helper functions."""

from datetime import datetime

from app.tasks.ingest_tasks import _parse_date


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------
class TestParseDate:
    def test_iso_format(self):
        result = _parse_date("2025-01-15")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_us_format(self):
        result = _parse_date("01/15/2025")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_iso_with_time(self):
        result = _parse_date("2025-01-15T14:30:00")
        assert isinstance(result, datetime)
        assert result.hour == 14
        assert result.minute == 30

    def test_iso_with_z(self):
        result = _parse_date("2025-01-15T14:30:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_invalid_format_returns_none(self):
        assert _parse_date("not-a-date") is None

    def test_partial_date_returns_none(self):
        assert _parse_date("2025") is None

    def test_various_valid_dates(self):
        dates = [
            ("2025-12-31", 12, 31),
            ("06/15/2024", 6, 15),
            ("2025-03-01T00:00:00Z", 3, 1),
        ]
        for date_str, expected_month, expected_day in dates:
            result = _parse_date(date_str)
            assert result is not None, f"Failed to parse: {date_str}"
            assert result.month == expected_month
            assert result.day == expected_day
