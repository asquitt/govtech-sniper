"""
RFP Sniper - Encryption Service
===============================
Field-level encryption helpers for secrets and sensitive data.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_ENCRYPTION_PREFIX = "enc::"
_REDACTED_VALUE = "********"


def _derive_key(raw_key: str) -> bytes:
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    key_source = settings.field_encryption_key or settings.secret_key
    return Fernet(_derive_key(key_source))


def is_encrypted(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(_ENCRYPTION_PREFIX)


def encrypt_value(value: Any) -> str:
    if value is None:
        return ""
    if is_encrypted(value):
        return value
    fernet = _get_fernet()
    token = fernet.encrypt(str(value).encode("utf-8")).decode("utf-8")
    return f"{_ENCRYPTION_PREFIX}{token}"


def decrypt_value(value: Any) -> Any:
    if not is_encrypted(value):
        return value
    token = str(value).replace(_ENCRYPTION_PREFIX, "", 1)
    fernet = _get_fernet()
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value


def redact_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    return _REDACTED_VALUE


def encrypt_secrets(config: dict[str, Any], secret_fields: list[str]) -> dict[str, Any]:
    updated = dict(config)
    for key in secret_fields:
        if key in updated and updated[key] not in (None, ""):
            updated[key] = encrypt_value(updated[key])
    return updated


def decrypt_secrets(config: dict[str, Any], secret_fields: list[str]) -> dict[str, Any]:
    updated = dict(config)
    for key in secret_fields:
        if key in updated and updated[key] not in (None, ""):
            updated[key] = decrypt_value(updated[key])
    return updated


def redact_secrets(config: dict[str, Any], secret_fields: list[str]) -> dict[str, Any]:
    updated = dict(config)
    for key in secret_fields:
        if key in updated and updated[key] not in (None, ""):
            updated[key] = redact_value(updated[key])
    return updated


def secret_placeholder() -> str:
    return _REDACTED_VALUE
