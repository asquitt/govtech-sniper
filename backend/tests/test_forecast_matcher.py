"""
Forecast Matcher Unit Tests
=============================
Tests for _compute_match() pure scoring function.
"""

from unittest.mock import MagicMock

from app.services.forecast_matcher import _compute_match


def _mock_forecast(**kwargs):
    f = MagicMock()
    f.agency = kwargs.get("agency")
    f.naics_code = kwargs.get("naics_code")
    f.title = kwargs.get("title")
    f.estimated_value = kwargs.get("estimated_value")
    return f


def _mock_rfp(**kwargs):
    r = MagicMock()
    r.agency = kwargs.get("agency")
    r.naics_code = kwargs.get("naics_code")
    r.title = kwargs.get("title")
    r.estimated_value = kwargs.get("estimated_value")
    return r


class TestComputeMatch:
    def test_perfect_match(self):
        forecast = _mock_forecast(
            agency="Department of Defense",
            naics_code="541512",
            title="Cybersecurity Monitoring Services",
            estimated_value=1000000,
        )
        rfp = _mock_rfp(
            agency="Department of Defense",
            naics_code="541512",
            title="Cybersecurity Monitoring Services",
            estimated_value=1000000,
        )
        score, reasons = _compute_match(forecast, rfp)
        assert score >= 75  # Agency(30) + NAICS(25) + Title(20) + Value(25)
        assert "Agency match" in reasons
        assert "NAICS exact match" in reasons

    def test_agency_match_only(self):
        forecast = _mock_forecast(agency="DoD", naics_code=None, title=None, estimated_value=None)
        rfp = _mock_rfp(agency="DoD", naics_code=None, title=None, estimated_value=None)
        score, reasons = _compute_match(forecast, rfp)
        assert score == 30
        assert "Agency match" in reasons

    def test_naics_prefix_match(self):
        forecast = _mock_forecast(
            agency=None, naics_code="541512", title=None, estimated_value=None
        )
        rfp = _mock_rfp(agency=None, naics_code="541519", title=None, estimated_value=None)
        score, reasons = _compute_match(forecast, rfp)
        assert score == 15
        assert "NAICS prefix match" in reasons

    def test_naics_exact_match(self):
        forecast = _mock_forecast(
            agency=None, naics_code="541512", title=None, estimated_value=None
        )
        rfp = _mock_rfp(agency=None, naics_code="541512", title=None, estimated_value=None)
        score, reasons = _compute_match(forecast, rfp)
        assert score == 25
        assert "NAICS exact match" in reasons

    def test_no_match(self):
        forecast = _mock_forecast(
            agency="NASA", naics_code="111111", title="Farming", estimated_value=100
        )
        rfp = _mock_rfp(
            agency="DoD", naics_code="999999", title="Cybersecurity", estimated_value=10000000
        )
        score, reasons = _compute_match(forecast, rfp)
        assert score == 0
        assert len(reasons) == 0

    def test_value_range_match(self):
        forecast = _mock_forecast(agency=None, naics_code=None, title=None, estimated_value=800000)
        rfp = _mock_rfp(agency=None, naics_code=None, title=None, estimated_value=1000000)
        score, reasons = _compute_match(forecast, rfp)
        assert score > 0
        assert "Value range match" in reasons

    def test_value_out_of_range(self):
        forecast = _mock_forecast(agency=None, naics_code=None, title=None, estimated_value=100000)
        rfp = _mock_rfp(agency=None, naics_code=None, title=None, estimated_value=10000000)
        score, reasons = _compute_match(forecast, rfp)
        # ratio = 0.01, way outside 0.5-2.0 range
        assert "Value range match" not in reasons

    def test_title_overlap(self):
        forecast = _mock_forecast(
            agency=None, naics_code=None, title="Network Security Operations", estimated_value=None
        )
        rfp = _mock_rfp(
            agency=None, naics_code=None, title="Network Security Management", estimated_value=None
        )
        score, reasons = _compute_match(forecast, rfp)
        assert any("Title overlap" in r for r in reasons)

    def test_none_fields_no_crash(self):
        forecast = _mock_forecast(agency=None, naics_code=None, title=None, estimated_value=None)
        rfp = _mock_rfp(agency=None, naics_code=None, title=None, estimated_value=None)
        score, reasons = _compute_match(forecast, rfp)
        assert score == 0
