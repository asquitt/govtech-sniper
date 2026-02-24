"""
Auth Service Unit Tests
========================
Direct unit tests for auth_service.py functions:
password hashing, JWT creation/decoding, token expiry, password validation.
These are pure-function tests — no DB or async required.
"""

import time
from datetime import datetime, timedelta

from jose import jwt

from app.config import settings
from app.services.auth_service import (
    TokenData,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
    decode_token,
    hash_password,
    is_token_expired,
    validate_password_strength,
    verify_password,
)

# =============================================================================
# Password Hashing
# =============================================================================


class TestPasswordHashing:
    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("SecurePass123!")
        assert hashed.startswith("$2b$")
        assert hashed != "SecurePass123!"

    def test_hash_password_different_salts(self):
        h1 = hash_password("Same")
        h2 = hash_password("Same")
        assert h1 != h2  # bcrypt uses random salts

    def test_verify_password_correct(self):
        hashed = hash_password("TestPassword123!")
        assert verify_password("TestPassword123!", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("TestPassword123!")
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_with_invalid_hash(self):
        # Should return False, not raise
        assert verify_password("anything", "not-a-valid-hash") is False


# =============================================================================
# Access Tokens
# =============================================================================


class TestAccessToken:
    def test_create_access_token_returns_string(self):
        token = create_access_token(user_id=1, email="a@b.com", tier="free")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_claims(self):
        token = create_access_token(user_id=42, email="test@example.com", tier="professional")
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "42"
        assert payload["email"] == "test@example.com"
        assert payload["tier"] == "professional"
        assert payload["type"] == "access"

    def test_create_access_token_custom_expiry(self):
        delta = timedelta(minutes=5)
        now = time.time()
        token = create_access_token(user_id=1, email="a@b.com", tier="free", expires_delta=delta)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        exp_ts = payload["exp"]
        # Should expire roughly 5 minutes from now (UTC epoch)
        assert now + 4 * 60 < exp_ts < now + 6 * 60

    def test_decode_access_token_valid(self):
        token = create_access_token(user_id=7, email="user@test.com", tier="enterprise")
        data = decode_access_token(token)
        assert data is not None
        assert data.user_id == 7
        assert data.email == "user@test.com"
        assert data.tier == "enterprise"

    def test_decode_access_token_rejects_refresh(self):
        """Access token decoder should reject refresh tokens."""
        token = create_refresh_token(user_id=1)
        data = decode_access_token(token)
        assert data is None

    def test_decode_access_token_invalid_string(self):
        assert decode_access_token("garbage.token.value") is None

    def test_decode_access_token_wrong_secret(self):
        token = jwt.encode(
            {
                "sub": "1",
                "email": "a@b.com",
                "tier": "free",
                "type": "access",
                "exp": datetime.utcnow() + timedelta(hours=1),
            },
            "wrong-secret",
            algorithm=settings.jwt_algorithm,
        )
        assert decode_access_token(token) is None


# =============================================================================
# Refresh Tokens
# =============================================================================


class TestRefreshToken:
    def test_create_refresh_token_returns_string(self):
        token = create_refresh_token(user_id=1)
        assert isinstance(token, str)

    def test_create_refresh_token_contains_type(self):
        token = create_refresh_token(user_id=5)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["type"] == "refresh"
        assert payload["sub"] == "5"
        assert "email" not in payload  # refresh tokens don't carry email

    def test_decode_refresh_token_valid(self):
        token = create_refresh_token(user_id=99)
        uid = decode_refresh_token(token)
        assert uid == 99

    def test_decode_refresh_token_rejects_access(self):
        """Refresh token decoder should reject access tokens."""
        token = create_access_token(user_id=1, email="a@b.com", tier="free")
        uid = decode_refresh_token(token)
        assert uid is None

    def test_decode_refresh_token_invalid(self):
        assert decode_refresh_token("bad.token") is None

    def test_refresh_token_custom_expiry(self):
        delta = timedelta(days=1)
        now = time.time()
        token = create_refresh_token(user_id=1, expires_delta=delta)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        exp_ts = payload["exp"]
        # Should expire roughly 1 day from now (UTC epoch)
        assert now + 23 * 3600 < exp_ts < now + 25 * 3600


# =============================================================================
# Token Pair
# =============================================================================


class TestTokenPair:
    def test_create_token_pair_has_both_tokens(self):
        pair = create_token_pair(user_id=1, email="u@e.com", tier="free")
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in == settings.jwt_expiration_hours * 3600

    def test_token_pair_access_is_decodable(self):
        pair = create_token_pair(user_id=3, email="p@q.com", tier="professional")
        data = decode_access_token(pair.access_token)
        assert data is not None
        assert data.user_id == 3

    def test_token_pair_refresh_is_decodable(self):
        pair = create_token_pair(user_id=3, email="p@q.com", tier="professional")
        uid = decode_refresh_token(pair.refresh_token)
        assert uid == 3


# =============================================================================
# Generic decode_token
# =============================================================================


class TestDecodeToken:
    def test_decode_token_access(self):
        token = create_access_token(user_id=10, email="g@h.com", tier="free")
        data = decode_token(token)
        assert data is not None
        assert data.user_id == 10

    def test_decode_token_invalid(self):
        assert decode_token("nope") is None


# =============================================================================
# Token Expiry
# =============================================================================


class TestTokenExpiry:
    def test_is_token_expired_future(self):
        td = TokenData(
            user_id=1, email="a@b.com", tier="free", exp=datetime.utcnow() + timedelta(hours=1)
        )
        assert is_token_expired(td) is False

    def test_is_token_expired_past(self):
        td = TokenData(
            user_id=1, email="a@b.com", tier="free", exp=datetime.utcnow() - timedelta(hours=1)
        )
        assert is_token_expired(td) is True

    def test_expired_token_decode_returns_none(self):
        """jose itself rejects expired tokens during decode."""
        token = create_access_token(
            user_id=1, email="a@b.com", tier="free", expires_delta=timedelta(seconds=-1)
        )
        assert decode_access_token(token) is None


# =============================================================================
# Password Validation
# =============================================================================


class TestPasswordValidation:
    def test_valid_password(self):
        ok, msg = validate_password_strength("GoodPass1!")
        assert ok is True
        assert msg == ""

    def test_too_short(self):
        ok, msg = validate_password_strength("Ab1!")
        assert ok is False
        assert "8 characters" in msg

    def test_no_uppercase(self):
        ok, msg = validate_password_strength("lowercase1!")
        assert ok is False
        assert "uppercase" in msg

    def test_no_lowercase(self):
        ok, msg = validate_password_strength("UPPERCASE1!")
        assert ok is False
        assert "lowercase" in msg

    def test_no_digit(self):
        ok, msg = validate_password_strength("NoDigits!!")
        assert ok is False
        assert "number" in msg

    def test_no_special(self):
        ok, msg = validate_password_strength("NoSpecial1A")
        assert ok is False
        assert "special" in msg
