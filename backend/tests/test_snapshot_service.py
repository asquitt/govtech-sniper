"""
Snapshot Service Unit Tests
============================
Tests for build_snapshot_summary() and diff_snapshot_summaries().
"""

from app.services.snapshot_service import (
    _hash_text,
    _normalize_resource_links,
    build_snapshot_summary,
    diff_snapshot_summaries,
)


class TestNormalizeResourceLinks:
    def test_string_links(self):
        result = _normalize_resource_links(["https://a.com", "https://b.com"])
        assert result == ["https://a.com", "https://b.com"]

    def test_dict_links_with_url(self):
        result = _normalize_resource_links([{"url": "https://a.com", "name": "File A"}])
        assert result == ["https://a.com"]

    def test_dict_links_with_name_fallback(self):
        result = _normalize_resource_links([{"name": "attachment.pdf"}])
        assert result == ["attachment.pdf"]

    def test_deduplicates_and_sorts(self):
        result = _normalize_resource_links(["https://b.com", "https://a.com", "https://b.com"])
        assert result == ["https://a.com", "https://b.com"]

    def test_empty_strings_filtered(self):
        result = _normalize_resource_links(["", "https://a.com", ""])
        assert result == ["https://a.com"]

    def test_empty_list(self):
        assert _normalize_resource_links([]) == []


class TestHashText:
    def test_deterministic(self):
        assert _hash_text("hello") == _hash_text("hello")

    def test_different_inputs(self):
        assert _hash_text("a") != _hash_text("b")


class TestBuildSnapshotSummary:
    def test_basic_payload(self):
        payload = {
            "noticeId": "N123",
            "solicitationNumber": "W912-25-R-0001",
            "title": "IT Services",
            "postedDate": "2025-01-15",
            "responseDeadLine": "2025-02-15",
            "naicsCode": "541512",
            "typeOfSetAsideDescription": "Small Business",
            "type": "solicitation",
            "description": "Cybersecurity services needed.",
            "organizationHierarchy": [
                {"name": "Department of Defense"},
                {"name": "U.S. Army"},
            ],
            "resourceLinks": ["https://sam.gov/doc1.pdf"],
        }
        summary = build_snapshot_summary(payload)
        assert summary.notice_id == "N123"
        assert summary.agency == "Department of Defense"
        assert summary.sub_agency == "U.S. Army"
        assert summary.naics_code == "541512"
        assert summary.resource_links_count == 1
        assert summary.description_length > 0
        assert summary.description_hash is not None

    def test_missing_org_hierarchy(self):
        summary = build_snapshot_summary({"noticeId": "N1", "title": "Test"})
        assert summary.agency is None
        assert summary.sub_agency is None

    def test_empty_description(self):
        summary = build_snapshot_summary({"noticeId": "N1", "description": ""})
        assert summary.description_hash is None
        assert summary.description_length == 0


class TestDiffSnapshotSummaries:
    def test_no_changes(self):
        payload = {"noticeId": "N1", "title": "Same"}
        s1 = build_snapshot_summary(payload)
        s2 = build_snapshot_summary(payload)
        changes = diff_snapshot_summaries(s1, s2)
        assert len(changes) == 0

    def test_title_change_detected(self):
        s1 = build_snapshot_summary({"noticeId": "N1", "title": "Old Title"})
        s2 = build_snapshot_summary({"noticeId": "N1", "title": "New Title"})
        changes = diff_snapshot_summaries(s1, s2)
        title_changes = [c for c in changes if c.field == "title"]
        assert len(title_changes) == 1
        assert title_changes[0].from_value == "Old Title"
        assert title_changes[0].to_value == "New Title"

    def test_deadline_change_detected(self):
        s1 = build_snapshot_summary({"noticeId": "N1", "responseDeadLine": "2025-03-01"})
        s2 = build_snapshot_summary({"noticeId": "N1", "responseDeadLine": "2025-04-01"})
        changes = diff_snapshot_summaries(s1, s2)
        deadline_changes = [c for c in changes if c.field == "response_deadline"]
        assert len(deadline_changes) == 1
