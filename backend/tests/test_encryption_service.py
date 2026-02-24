"""
Encryption Service Unit Tests
==============================
Tests for field-level encryption, decryption, and redaction.
"""

from app.services.encryption_service import (
    decrypt_secrets,
    decrypt_value,
    encrypt_secrets,
    encrypt_value,
    is_encrypted,
    redact_secrets,
    redact_value,
    secret_placeholder,
)


class TestIsEncrypted:
    def test_encrypted_prefix_detected(self):
        assert is_encrypted("enc::sometoken") is True

    def test_plain_text_not_detected(self):
        assert is_encrypted("plain text") is False

    def test_none_not_detected(self):
        assert is_encrypted(None) is False

    def test_empty_string_not_detected(self):
        assert is_encrypted("") is False

    def test_integer_not_detected(self):
        assert is_encrypted(42) is False


class TestEncryptDecrypt:
    def test_round_trip(self):
        original = "my-secret-api-key"
        encrypted = encrypt_value(original)
        assert encrypted.startswith("enc::")
        assert decrypt_value(encrypted) == original

    def test_encrypt_none_returns_empty(self):
        assert encrypt_value(None) == ""

    def test_encrypt_already_encrypted_is_idempotent(self):
        encrypted = encrypt_value("secret")
        double_encrypted = encrypt_value(encrypted)
        assert encrypted == double_encrypted  # no double-wrapping

    def test_decrypt_plain_returns_as_is(self):
        assert decrypt_value("plain text") == "plain text"

    def test_decrypt_invalid_token_returns_original(self):
        bad = "enc::invalid-fernet-token"
        assert decrypt_value(bad) == bad

    def test_encrypt_integer_value(self):
        encrypted = encrypt_value(42)
        assert decrypt_value(encrypted) == "42"


class TestRedact:
    def test_redact_value(self):
        assert redact_value("secret") == "********"

    def test_redact_none(self):
        assert redact_value(None) is None

    def test_redact_empty(self):
        assert redact_value("") == ""

    def test_secret_placeholder(self):
        assert secret_placeholder() == "********"


class TestBulkOperations:
    def test_encrypt_secrets_encrypts_specified_fields(self):
        config = {"api_key": "sk-123", "name": "test", "token": "tok-456"}
        result = encrypt_secrets(config, ["api_key", "token"])
        assert result["api_key"].startswith("enc::")
        assert result["token"].startswith("enc::")
        assert result["name"] == "test"  # untouched

    def test_encrypt_secrets_skips_none_and_empty(self):
        config = {"api_key": None, "token": ""}
        result = encrypt_secrets(config, ["api_key", "token"])
        assert result["api_key"] is None
        assert result["token"] == ""

    def test_decrypt_secrets_round_trip(self):
        config = {"api_key": "sk-123", "name": "test"}
        encrypted = encrypt_secrets(config, ["api_key"])
        decrypted = decrypt_secrets(encrypted, ["api_key"])
        assert decrypted["api_key"] == "sk-123"
        assert decrypted["name"] == "test"

    def test_redact_secrets(self):
        config = {"api_key": "sk-123", "name": "test"}
        redacted = redact_secrets(config, ["api_key"])
        assert redacted["api_key"] == "********"
        assert redacted["name"] == "test"

    def test_does_not_mutate_original(self):
        config = {"api_key": "sk-123"}
        encrypt_secrets(config, ["api_key"])
        assert config["api_key"] == "sk-123"  # original unchanged
