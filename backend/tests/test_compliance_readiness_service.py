"""
Compliance Readiness Service Unit Tests
=========================================
Tests for pure data structures (CheckpointEvidenceSnapshot).
The async DB functions are not tested here since they require a live session.
"""

from unittest.mock import MagicMock

from app.services.compliance_readiness_service import CheckpointEvidenceSnapshot

# =============================================================================
# CheckpointEvidenceSnapshot
# =============================================================================


class TestCheckpointEvidenceSnapshot:
    def test_init_with_mocks(self):
        link = MagicMock()
        evidence = MagicMock()
        snapshot = CheckpointEvidenceSnapshot(link=link, evidence=evidence)
        assert snapshot.link is link
        assert snapshot.evidence is evidence

    def test_slots_prevents_extra_attrs(self):
        import pytest

        link = MagicMock()
        evidence = MagicMock()
        snapshot = CheckpointEvidenceSnapshot(link=link, evidence=evidence)
        with pytest.raises(AttributeError):
            snapshot.extra_field = "test"  # type: ignore[attr-defined]

    def test_two_snapshots_are_independent(self):
        link1 = MagicMock()
        link2 = MagicMock()
        ev1 = MagicMock()
        ev2 = MagicMock()
        s1 = CheckpointEvidenceSnapshot(link=link1, evidence=ev1)
        s2 = CheckpointEvidenceSnapshot(link=link2, evidence=ev2)
        assert s1.link is not s2.link
        assert s1.evidence is not s2.evidence
