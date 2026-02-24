"""
Export Signing Unit Tests
==========================
Tests for HMAC signing of exported trust/compliance payloads.
"""

import hashlib
import hmac
import json

from app.config import settings
from app.services.export_signing import sign_bytes, sign_json, signed_headers


class TestSignBytes:
    def test_returns_hex_digest(self):
        sig = sign_bytes(b"hello")
        assert isinstance(sig, str)
        assert len(sig) == 64  # sha256 hex digest

    def test_deterministic(self):
        assert sign_bytes(b"payload") == sign_bytes(b"payload")

    def test_different_payloads_different_sigs(self):
        assert sign_bytes(b"a") != sign_bytes(b"b")

    def test_matches_manual_hmac(self):
        payload = b"test data"
        expected = hmac.new(
            settings.audit_export_signing_key.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        assert sign_bytes(payload) == expected


class TestSignJson:
    def test_deterministic_for_same_dict(self):
        data = {"b": 2, "a": 1}
        assert sign_json(data) == sign_json(data)

    def test_key_order_independent(self):
        """sort_keys=True makes key order irrelevant."""
        assert sign_json({"b": 2, "a": 1}) == sign_json({"a": 1, "b": 2})

    def test_matches_sign_bytes_on_canonical_json(self):
        data = {"x": 1}
        canonical = json.dumps(data, sort_keys=True).encode("utf-8")
        assert sign_json(data) == sign_bytes(canonical)


class TestSignedHeaders:
    def test_returns_header_when_enabled(self):
        headers = signed_headers(b"payload", enabled=True)
        assert "X-Trust-Export-Signature" in headers
        assert headers["X-Trust-Export-Signature"] == sign_bytes(b"payload")

    def test_returns_empty_when_disabled(self):
        headers = signed_headers(b"payload", enabled=False)
        assert headers == {}
