"""Helpers for HMAC-signing exported trust/compliance payloads."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from app.config import settings


def sign_bytes(payload: bytes) -> str:
    """Sign raw bytes with the configured audit export signing key."""
    return hmac.new(
        settings.audit_export_signing_key.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def sign_json(payload: Any) -> str:
    """Serialize JSON deterministically and sign it."""
    serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
    return sign_bytes(serialized)


def signed_headers(payload: bytes, *, enabled: bool) -> dict[str, str]:
    """Return signature headers when signing is requested."""
    if not enabled:
        return {}
    signature = sign_bytes(payload)
    return {"X-Trust-Export-Signature": signature}
