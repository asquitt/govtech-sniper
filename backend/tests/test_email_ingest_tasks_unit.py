"""Unit tests for email_ingest_tasks helper functions."""

from datetime import datetime

from app.tasks.email_ingest_tasks import (
    _classify_rfp_likelihood,
    _clean_subject,
    _extract_agency,
    _extract_sender_email,
    _extract_solicitation_number,
    _fallback_solicitation_number,
    _normalize_message_id,
    _parse_received_at,
)


# ---------------------------------------------------------------------------
# _extract_solicitation_number
# ---------------------------------------------------------------------------
class TestExtractSolicitationNumber:
    def test_extracts_from_subject(self):
        result = _extract_solicitation_number("RFP W912HV-24-R-0001 for IT Services", "")
        assert result == "W912HV-24-R-0001"

    def test_extracts_from_body(self):
        result = _extract_solicitation_number(
            "IT Opportunity",
            "Solicitation: W912HV-24-R-0001 for IT services.",
        )
        assert result == "W912HV-24-R-0001"

    def test_extracts_notice_id_pattern(self):
        result = _extract_solicitation_number("Notice ID: ABC123-2024", "")
        assert result is not None
        assert "ABC123" in result

    def test_returns_none_for_no_match(self):
        result = _extract_solicitation_number("Hello world", "Just a regular email.")
        assert result is None

    def test_handles_empty_strings(self):
        result = _extract_solicitation_number("", "")
        assert result is None

    def test_truncates_long_numbers(self):
        long_id = "A" * 200
        result = _extract_solicitation_number(f"solicitation number: {long_id}", "")
        if result:
            assert len(result) <= 100


# ---------------------------------------------------------------------------
# _fallback_solicitation_number
# ---------------------------------------------------------------------------
class TestFallbackSolicitationNumber:
    def test_generates_email_prefix(self):
        result = _fallback_solicitation_number("msg-123@example.com")
        assert result.startswith("EMAIL-")
        assert len(result) == 18  # "EMAIL-" + 12 hex chars

    def test_deterministic(self):
        r1 = _fallback_solicitation_number("test@mail.com")
        r2 = _fallback_solicitation_number("test@mail.com")
        assert r1 == r2

    def test_different_ids_produce_different_results(self):
        r1 = _fallback_solicitation_number("msg-a@mail.com")
        r2 = _fallback_solicitation_number("msg-b@mail.com")
        assert r1 != r2


# ---------------------------------------------------------------------------
# _normalize_message_id
# ---------------------------------------------------------------------------
class TestNormalizeMessageId:
    def test_uses_message_id_field(self):
        result = _normalize_message_id({"message_id": "<abc123@mail.com>"})
        assert result == "<abc123@mail.com>"

    def test_fallback_to_composite(self):
        result = _normalize_message_id(
            {
                "subject": "Test Subject",
                "sender": "bob@example.com",
                "date": "2025-01-01",
            }
        )
        assert "Test Subject" in result
        assert "bob@example.com" in result

    def test_truncates_long_message_id(self):
        long_id = "x" * 600
        result = _normalize_message_id({"message_id": long_id})
        assert len(result) <= 500

    def test_handles_missing_fields(self):
        result = _normalize_message_id({})
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _parse_received_at
# ---------------------------------------------------------------------------
class TestParseReceivedAt:
    def test_parses_rfc2822_date(self):
        result = _parse_received_at("Mon, 01 Jan 2025 12:00:00 +0000")
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_returns_now_for_none(self):
        result = _parse_received_at(None)
        assert isinstance(result, datetime)
        # Should be close to now
        diff = abs((datetime.utcnow() - result).total_seconds())
        assert diff < 5

    def test_returns_now_for_unparseable(self):
        result = _parse_received_at("not a date")
        assert isinstance(result, datetime)

    def test_strips_timezone(self):
        result = _parse_received_at("Mon, 01 Jan 2025 15:00:00 -0500")
        assert result.tzinfo is None


# ---------------------------------------------------------------------------
# _extract_agency
# ---------------------------------------------------------------------------
class TestExtractAgency:
    def test_extracts_gov_domain(self):
        result = _extract_agency("John Smith <john@dod.gov>")
        assert result == "DOD"

    def test_non_gov_returns_unknown(self):
        result = _extract_agency("Jane <jane@company.com>")
        assert result == "Unknown"

    def test_handles_complex_gov_domain(self):
        result = _extract_agency("user@nasa.gov")
        assert result == "NASA"

    def test_handles_empty_sender(self):
        result = _extract_agency("")
        assert result == "Unknown"


# ---------------------------------------------------------------------------
# _extract_sender_email
# ---------------------------------------------------------------------------
class TestExtractSenderEmail:
    def test_extracts_email(self):
        result = _extract_sender_email("John Smith <john@example.com>")
        assert result == "john@example.com"

    def test_plain_email(self):
        result = _extract_sender_email("john@example.com")
        assert result == "john@example.com"

    def test_empty_returns_none(self):
        result = _extract_sender_email("")
        assert result is None


# ---------------------------------------------------------------------------
# _clean_subject
# ---------------------------------------------------------------------------
class TestCleanSubject:
    def test_strips_re_prefix(self):
        assert _clean_subject("Re: IT Services RFP") == "IT Services RFP"

    def test_strips_fw_prefix(self):
        assert _clean_subject("FW: Opportunity") == "Opportunity"

    def test_strips_fwd_prefix(self):
        assert _clean_subject("Fwd: RFP Alert") == "RFP Alert"

    def test_no_prefix(self):
        assert _clean_subject("Direct Subject") == "Direct Subject"

    def test_empty_after_clean(self):
        assert _clean_subject("Re:") == "Forwarded Opportunity"

    def test_case_insensitive(self):
        assert _clean_subject("RE: Test") == "Test"


# ---------------------------------------------------------------------------
# _classify_rfp_likelihood
# ---------------------------------------------------------------------------
class TestClassifyRfpLikelihood:
    def test_high_confidence_with_solicitation_and_keywords(self):
        confidence, reasons = _classify_rfp_likelihood(
            subject="RFP W912HV-24-R-0001 for IT Services",
            body="This solicitation seeks proposals for cybersecurity services. NAICS 541512.",
            sender="co@dod.gov",
            attachment_names=["solicitation.pdf"],
        )
        assert confidence > 0.5
        assert len(reasons) > 0

    def test_low_confidence_for_generic_email(self):
        confidence, reasons = _classify_rfp_likelihood(
            subject="Happy New Year!",
            body="Wishing you all the best in 2025.",
            sender="friend@gmail.com",
            attachment_names=[],
        )
        assert confidence < 0.2

    def test_keyword_hits_contribute_score(self):
        confidence, _ = _classify_rfp_likelihood(
            subject="request for proposal",
            body="solicitation for procurement services",
            sender="test@test.com",
            attachment_names=[],
        )
        assert confidence > 0.0

    def test_pdf_attachment_boosts_score(self):
        c_no_pdf, _ = _classify_rfp_likelihood(
            subject="RFP Notice",
            body="",
            sender="test@test.com",
            attachment_names=[],
        )
        c_with_pdf, _ = _classify_rfp_likelihood(
            subject="RFP Notice",
            body="",
            sender="test@test.com",
            attachment_names=["doc.pdf"],
        )
        assert c_with_pdf > c_no_pdf

    def test_gov_sender_boosts_score(self):
        c_no_gov, _ = _classify_rfp_likelihood(
            subject="RFP",
            body="",
            sender="test@company.com",
            attachment_names=[],
        )
        c_gov, _ = _classify_rfp_likelihood(
            subject="RFP",
            body="",
            sender="co@agency.gov",
            attachment_names=[],
        )
        assert c_gov > c_no_gov

    def test_confidence_capped_at_one(self):
        confidence, _ = _classify_rfp_likelihood(
            subject="RFP W912HV-24-R-0001 solicitation notice rfq procurement NAICS",
            body="request for proposal request for quotation statement of work "
            "scope of work period of performance proposal due response deadline "
            "contracting officer sam.gov",
            sender="co@dod.gov",
            attachment_names=["rfp.pdf", "sow.pdf", "cover.docx"],
        )
        assert confidence <= 1.0

    def test_no_signals_message(self):
        _, reasons = _classify_rfp_likelihood(
            subject="Hey",
            body="How are you?",
            sender="test@test.com",
            attachment_names=[],
        )
        assert any("No strong" in r for r in reasons)
