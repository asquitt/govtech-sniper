"""
RFP Sniper - Authentication Service
====================================
JWT-based authentication with secure password hashing.
"""

from datetime import datetime, timedelta

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.config import settings

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# Token Models
# =============================================================================


class TokenData(BaseModel):
    """Data encoded in JWT token."""

    user_id: int
    email: str
    tier: str
    exp: datetime


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserAuth(BaseModel):
    """User authentication data."""

    id: int
    email: EmailStr
    full_name: str | None
    company_name: str | None
    tier: str
    is_active: bool


# =============================================================================
# Password Utilities
# =============================================================================


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to check
        hashed_password: Stored hash to verify against

    Returns:
        True if password matches
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# =============================================================================
# JWT Token Utilities
# =============================================================================


def create_access_token(
    user_id: int,
    email: str,
    tier: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's database ID
        email: User's email address
        tier: User's subscription tier
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode = {
        "sub": str(user_id),
        "email": email,
        "tier": tier,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def create_refresh_token(
    user_id: int,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token (longer-lived).

    Args:
        user_id: User's database ID
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Refresh tokens last 7 days by default
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def create_token_pair(user_id: int, email: str, tier: str) -> TokenPair:
    """
    Create both access and refresh tokens.

    Args:
        user_id: User's database ID
        email: User's email address
        tier: User's subscription tier

    Returns:
        TokenPair with both tokens
    """
    access_token = create_access_token(user_id, email, tier)
    refresh_token = create_refresh_token(user_id)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_hours * 3600,
    )


def decode_token(token: str) -> TokenData | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = int(payload.get("sub"))
        email = payload.get("email", "")
        tier = payload.get("tier", "free")
        exp = datetime.fromtimestamp(payload.get("exp", 0))

        return TokenData(
            user_id=user_id,
            email=email,
            tier=tier,
            exp=exp,
        )

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None


def decode_access_token(token: str) -> TokenData | None:
    """
    Decode and validate an access token.

    Returns TokenData if the token is valid and of type 'access'.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        if payload.get("type") != "access":
            logger.warning("Token is not an access token")
            return None

        user_id = int(payload.get("sub"))
        email = payload.get("email", "")
        tier = payload.get("tier", "free")
        exp = datetime.fromtimestamp(payload.get("exp", 0))

        return TokenData(
            user_id=user_id,
            email=email,
            tier=tier,
            exp=exp,
        )
    except JWTError as e:
        logger.warning(f"Access token decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Access token decode error: {e}")
        return None


def decode_refresh_token(token: str) -> int | None:
    """
    Decode a refresh token and return user_id.

    Args:
        token: JWT refresh token string

    Returns:
        User ID if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            return None

        return int(payload.get("sub"))

    except JWTError as e:
        logger.warning(f"Refresh token decode error: {e}")
        return None


def is_token_expired(token_data: TokenData) -> bool:
    """
    Check if a token has expired.

    Args:
        token_data: Decoded token data

    Returns:
        True if expired
    """
    return datetime.utcnow() > token_data.exp


# =============================================================================
# Password Validation
# =============================================================================


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"

    return True, ""
