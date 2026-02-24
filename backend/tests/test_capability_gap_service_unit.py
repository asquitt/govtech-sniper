"""Unit tests for capability_gap_service module."""

from app.services.capability_gap_service import (
    CapabilityGap,
    CapabilityGapResult,
    _mock_gap_result,
)


# ---------------------------------------------------------------------------
# CapabilityGap dataclass
# ---------------------------------------------------------------------------
class TestCapabilityGap:
    def test_basic_construction(self):
        gap = CapabilityGap(
            gap_type="technical",
            description="Need cloud skills",
        )
        assert gap.gap_type == "technical"
        assert gap.description == "Need cloud skills"
        assert gap.required_value is None
        assert gap.matching_partner_ids == []

    def test_with_all_fields(self):
        gap = CapabilityGap(
            gap_type="clearance",
            description="TS/SCI required",
            required_value="TS/SCI",
            matching_partner_ids=[1, 2, 3],
        )
        assert gap.required_value == "TS/SCI"
        assert gap.matching_partner_ids == [1, 2, 3]

    def test_defaults_empty_partner_ids(self):
        gap = CapabilityGap(
            gap_type="naics",
            description="Missing NAICS",
        )
        assert gap.matching_partner_ids == []


# ---------------------------------------------------------------------------
# CapabilityGapResult
# ---------------------------------------------------------------------------
class TestCapabilityGapResult:
    def test_construction(self):
        result = CapabilityGapResult(
            rfp_id=42,
            gaps=[{"gap_type": "technical", "description": "Need AWS"}],
            recommended_partners=[{"partner_id": 1, "name": "AWS Partner"}],
            analysis_summary="One gap found.",
        )
        assert result.rfp_id == 42
        assert len(result.gaps) == 1
        assert len(result.recommended_partners) == 1
        assert result.analysis_summary == "One gap found."

    def test_empty_results(self):
        result = CapabilityGapResult(
            rfp_id=1,
            gaps=[],
            recommended_partners=[],
            analysis_summary="No gaps found.",
        )
        assert result.gaps == []
        assert result.recommended_partners == []


# ---------------------------------------------------------------------------
# Mock gap result (deterministic fallback)
# ---------------------------------------------------------------------------
class TestMockGapResult:
    def test_returns_standard_structure(self):
        partners = [
            {"id": 1, "name": "Partner A"},
            {"id": 2, "name": "Partner B"},
            {"id": 3, "name": "Partner C"},
        ]
        result = _mock_gap_result(rfp_id=10, partners=partners)

        assert "gaps" in result
        assert "recommended_partners" in result
        assert "analysis_summary" in result
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["gap_type"] == "technical"

    def test_limits_to_three_partners(self):
        partners = [{"id": i, "name": f"Partner {i}"} for i in range(10)]
        result = _mock_gap_result(rfp_id=5, partners=partners)
        assert len(result["recommended_partners"]) == 3

    def test_empty_partners(self):
        result = _mock_gap_result(rfp_id=1, partners=[])
        assert result["recommended_partners"] == []
        assert result["gaps"][0]["matching_partner_ids"] == []

    def test_single_partner(self):
        partners = [{"id": 99, "name": "Solo Partner"}]
        result = _mock_gap_result(rfp_id=1, partners=partners)
        assert len(result["recommended_partners"]) == 1
        assert result["recommended_partners"][0]["partner_id"] == 99

    def test_gap_includes_matching_partner_ids(self):
        partners = [
            {"id": 1, "name": "P1"},
            {"id": 2, "name": "P2"},
            {"id": 3, "name": "P3"},
        ]
        result = _mock_gap_result(rfp_id=1, partners=partners)
        gap = result["gaps"][0]
        assert gap["matching_partner_ids"] == [1, 2]
