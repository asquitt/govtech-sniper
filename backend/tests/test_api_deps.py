"""
Tests for app/api/deps.py
=========================
Unit tests for auth dependencies, rate limiting, feature gates,
step-up auth, org role lookup, and API usage tracking.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.api.deps import (
    FEATURE_GATES,
    TIER_LEVELS,
    RedisRateLimiter,
    check_rate_limit,
    get_current_user,
    get_current_user_optional,
    get_current_user_with_profile,
    get_org_security_policy_from_settings,
    get_step_up_code,
    get_user_org_security_policy,
    get_user_policy_role,
    merge_org_security_policy_settings,
    require_feature,
    require_tier,
    resolve_user_id,
    track_api_usage,
    verify_step_up_code,
)
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User, UserProfile, UserTier
from app.services.auth_service import TokenData, UserAuth

# ---------------------------------------------------------------------------
# Async DB fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


@pytest_asyncio.fixture
async def user(session: AsyncSession) -> User:
    u = User(
        email="test@example.com",
        full_name="Test User",
        company_name="Test Corp",
        hashed_password="hashed",
        tier=UserTier.PROFESSIONAL,
        is_active=True,
        api_calls_today=0,
        api_calls_limit=100,
        last_api_reset=datetime.utcnow(),
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest_asyncio.fixture
async def inactive_user(session: AsyncSession) -> User:
    u = User(
        email="inactive@example.com",
        full_name="Inactive",
        company_name=None,
        hashed_password="hashed",
        tier=UserTier.FREE,
        is_active=False,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest_asyncio.fixture
async def user_with_mfa(session: AsyncSession) -> User:
    secret = pyotp.random_base32()
    u = User(
        email="mfa@example.com",
        full_name="MFA User",
        company_name=None,
        hashed_password="hashed",
        tier=UserTier.STARTER,
        is_active=True,
        mfa_enabled=True,
        mfa_secret=secret,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest_asyncio.fixture
async def organization(session: AsyncSession) -> Organization:
    org = Organization(
        name="Test Org",
        slug="test-org",
        settings={
            "require_step_up_for_sensitive_exports": False,
            "apply_cui_watermark_to_sensitive_exports": False,
        },
    )
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


@pytest_asyncio.fixture
async def org_member(
    session: AsyncSession, user: User, organization: Organization
) -> OrganizationMember:
    user.organization_id = organization.id
    session.add(user)
    member = OrganizationMember(
        organization_id=organization.id,
        user_id=user.id,
        role=OrgRole.ADMIN,
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


# ---------------------------------------------------------------------------
# resolve_user_id (pure function)
# ---------------------------------------------------------------------------


class TestResolveUserId:
    def test_both_match(self):
        auth = UserAuth(
            id=1, email="a@b.com", full_name=None, company_name=None, tier="free", is_active=True
        )
        assert resolve_user_id(1, auth) == 1

    def test_user_id_only(self):
        assert resolve_user_id(42, None) == 42

    def test_auth_only(self):
        auth = UserAuth(
            id=7, email="a@b.com", full_name=None, company_name=None, tier="free", is_active=True
        )
        assert resolve_user_id(None, auth) == 7

    def test_neither_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            resolve_user_id(None, None)
        assert exc.value.status_code == 401

    def test_mismatch_raises_403(self):
        auth = UserAuth(
            id=1, email="a@b.com", full_name=None, company_name=None, tier="free", is_active=True
        )
        with pytest.raises(HTTPException) as exc:
            resolve_user_id(999, auth)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# get_org_security_policy_from_settings (pure function)
# ---------------------------------------------------------------------------


class TestGetOrgSecurityPolicy:
    def test_defaults_when_empty(self):
        policy = get_org_security_policy_from_settings({})
        assert policy["require_step_up_for_sensitive_exports"] is True
        assert policy["apply_cui_redaction_to_sensitive_exports"] is False

    def test_overrides(self):
        policy = get_org_security_policy_from_settings(
            {
                "require_step_up_for_sensitive_exports": False,
                "apply_cui_redaction_to_sensitive_exports": True,
            }
        )
        assert policy["require_step_up_for_sensitive_exports"] is False
        assert policy["apply_cui_redaction_to_sensitive_exports"] is True

    def test_non_dict_returns_defaults(self):
        policy = get_org_security_policy_from_settings("invalid")
        assert policy["require_step_up_for_sensitive_exports"] is True

    def test_none_returns_defaults(self):
        policy = get_org_security_policy_from_settings(None)
        assert policy["require_step_up_for_sensitive_exports"] is True


# ---------------------------------------------------------------------------
# merge_org_security_policy_settings (pure function)
# ---------------------------------------------------------------------------


class TestMergeOrgSecurityPolicy:
    def test_merge_updates(self):
        result = merge_org_security_policy_settings(
            {"require_step_up_for_sensitive_exports": True},
            {"require_step_up_for_sensitive_exports": False},
        )
        assert result["require_step_up_for_sensitive_exports"] is False

    def test_preserves_existing(self):
        result = merge_org_security_policy_settings(
            {"custom_key": "value"},
            {"require_step_up_for_sensitive_exports": False},
        )
        assert result["custom_key"] == "value"
        assert result["require_step_up_for_sensitive_exports"] is False

    def test_skips_none_updates(self):
        result = merge_org_security_policy_settings(
            {},
            {"require_step_up_for_sensitive_exports": None},
        )
        # None is skipped, default True preserved
        assert result["require_step_up_for_sensitive_exports"] is True

    def test_non_dict_current_settings(self):
        result = merge_org_security_policy_settings("bad", {})
        assert "require_step_up_for_sensitive_exports" in result


# ---------------------------------------------------------------------------
# get_step_up_code (pure function)
# ---------------------------------------------------------------------------


class TestGetStepUpCode:
    def test_explicit_code_preferred(self):
        request = MagicMock()
        assert get_step_up_code(request, "123456") == "123456"

    def test_strips_whitespace(self):
        assert get_step_up_code(None, "  123456  ") == "123456"

    def test_header_fallback(self):
        request = MagicMock()
        request.headers.get = lambda h: "789012" if h == "X-Step-Up-Code" else None
        assert get_step_up_code(request) == "789012"

    def test_mfa_header_fallback(self):
        request = MagicMock()
        request.headers.get = lambda h: "654321" if h == "X-MFA-Code" else None
        assert get_step_up_code(request) == "654321"

    def test_no_code_returns_none(self):
        request = MagicMock()
        request.headers.get = lambda h: None
        assert get_step_up_code(request) is None

    def test_no_request_no_explicit(self):
        assert get_step_up_code(None, None) is None

    def test_empty_string_explicit(self):
        assert get_step_up_code(None, "   ") is None


# ---------------------------------------------------------------------------
# require_feature (dependency factory)
# ---------------------------------------------------------------------------


class TestRequireFeature:
    def test_unknown_feature_raises(self):
        with pytest.raises(ValueError, match="Unknown feature"):
            require_feature("nonexistent_feature")

    @pytest.mark.asyncio
    async def test_sufficient_tier_passes(self):
        checker = require_feature("deep_read")  # requires STARTER
        auth = UserAuth(
            id=1, email="a@b.com", full_name=None, company_name=None, tier="starter", is_active=True
        )
        result = await checker(auth)
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_insufficient_tier_raises_403(self):
        checker = require_feature("export_docx")  # requires PROFESSIONAL
        auth = UserAuth(
            id=1, email="a@b.com", full_name=None, company_name=None, tier="free", is_active=True
        )
        with pytest.raises(HTTPException) as exc:
            await checker(auth)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_enterprise_accesses_all(self):
        checker = require_feature("salesforce_sync")  # requires ENTERPRISE
        auth = UserAuth(
            id=1,
            email="a@b.com",
            full_name=None,
            company_name=None,
            tier="enterprise",
            is_active=True,
        )
        result = await checker(auth)
        assert result.id == 1


# ---------------------------------------------------------------------------
# require_tier (dependency factory)
# ---------------------------------------------------------------------------


class TestRequireTier:
    @pytest.mark.asyncio
    async def test_meets_minimum(self):
        checker = require_tier("starter")
        auth = UserAuth(
            id=1,
            email="a@b.com",
            full_name=None,
            company_name=None,
            tier="professional",
            is_active=True,
        )
        result = await checker(auth)
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_exact_tier(self):
        checker = require_tier("professional")
        auth = UserAuth(
            id=1,
            email="a@b.com",
            full_name=None,
            company_name=None,
            tier="professional",
            is_active=True,
        )
        result = await checker(auth)
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_below_minimum_raises_403(self):
        checker = require_tier("enterprise")
        auth = UserAuth(
            id=1, email="a@b.com", full_name=None, company_name=None, tier="starter", is_active=True
        )
        with pytest.raises(HTTPException) as exc:
            await checker(auth)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# TIER_LEVELS and FEATURE_GATES consistency
# ---------------------------------------------------------------------------


class TestTierConfig:
    def test_tier_ordering(self):
        assert TIER_LEVELS["free"] < TIER_LEVELS["starter"]
        assert TIER_LEVELS["starter"] < TIER_LEVELS["professional"]
        assert TIER_LEVELS["professional"] < TIER_LEVELS["enterprise"]

    def test_all_feature_gates_reference_valid_tiers(self):
        for feature, tier in FEATURE_GATES.items():
            assert tier.value in TIER_LEVELS, (
                f"Feature {feature} references unknown tier {tier.value}"
            )


# ---------------------------------------------------------------------------
# get_current_user (async, needs DB)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_no_credentials_raises_401(self, session):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(None, session)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, session):
        creds = MagicMock()
        creds.credentials = "invalid.jwt.token"
        with patch("app.api.deps.decode_token", return_value=None):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds, session)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_auth(self, session, user):
        creds = MagicMock()
        creds.credentials = "valid-token"
        token_data = TokenData(
            user_id=user.id,
            email=user.email,
            tier=user.tier.value,
            exp=datetime.utcnow() + timedelta(hours=1),
        )
        with patch("app.api.deps.decode_token", return_value=token_data):
            result = await get_current_user(creds, session)
        assert result.id == user.id
        assert result.email == user.email
        assert result.tier == "professional"

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self, session, inactive_user):
        creds = MagicMock()
        creds.credentials = "valid-token"
        token_data = TokenData(
            user_id=inactive_user.id,
            email=inactive_user.email,
            tier="free",
            exp=datetime.utcnow() + timedelta(hours=1),
        )
        with patch("app.api.deps.decode_token", return_value=token_data):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds, session)
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_401(self, session):
        creds = MagicMock()
        creds.credentials = "valid-token"
        token_data = TokenData(
            user_id=99999,
            email="gone@example.com",
            tier="free",
            exp=datetime.utcnow() + timedelta(hours=1),
        )
        with patch("app.api.deps.decode_token", return_value=token_data):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds, session)
            assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user_optional (async, needs DB)
# ---------------------------------------------------------------------------


class TestGetCurrentUserOptional:
    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self, session):
        result = await get_current_user_optional(None, session)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self, session):
        creds = MagicMock()
        creds.credentials = "bad-token"
        with patch("app.api.deps.decode_token", return_value=None):
            result = await get_current_user_optional(creds, session)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, session, user):
        creds = MagicMock()
        creds.credentials = "valid"
        token_data = TokenData(
            user_id=user.id,
            email=user.email,
            tier=user.tier.value,
            exp=datetime.utcnow() + timedelta(hours=1),
        )
        with patch("app.api.deps.decode_token", return_value=token_data):
            result = await get_current_user_optional(creds, session)
        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_inactive_user_returns_none(self, session, inactive_user):
        creds = MagicMock()
        creds.credentials = "valid"
        token_data = TokenData(
            user_id=inactive_user.id,
            email=inactive_user.email,
            tier="free",
            exp=datetime.utcnow() + timedelta(hours=1),
        )
        with patch("app.api.deps.decode_token", return_value=token_data):
            result = await get_current_user_optional(creds, session)
        assert result is None


# ---------------------------------------------------------------------------
# get_current_user_with_profile (async, needs DB)
# ---------------------------------------------------------------------------


class TestGetCurrentUserWithProfile:
    @pytest.mark.asyncio
    async def test_user_without_profile(self, session, user):
        auth = UserAuth(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            tier=user.tier.value,
            is_active=True,
        )
        result_auth, profile = await get_current_user_with_profile(auth, session)
        assert result_auth.id == user.id
        assert profile is None

    @pytest.mark.asyncio
    async def test_user_with_profile(self, session, user):
        profile = UserProfile(user_id=user.id)
        session.add(profile)
        await session.commit()

        auth = UserAuth(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            tier=user.tier.value,
            is_active=True,
        )
        result_auth, result_profile = await get_current_user_with_profile(auth, session)
        assert result_auth.id == user.id
        assert result_profile is not None
        assert result_profile.user_id == user.id


# ---------------------------------------------------------------------------
# verify_step_up_code (async, needs DB)
# ---------------------------------------------------------------------------


class TestVerifyStepUpCode:
    @pytest.mark.asyncio
    async def test_no_code_returns_false(self, session, user_with_mfa):
        result = await verify_step_up_code(user_with_mfa.id, session, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_valid_totp_returns_true(self, session, user_with_mfa):
        totp = pyotp.TOTP(user_with_mfa.mfa_secret)
        code = totp.now()
        result = await verify_step_up_code(user_with_mfa.id, session, code)
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_totp_returns_false(self, session, user_with_mfa):
        result = await verify_step_up_code(user_with_mfa.id, session, "000000")
        assert result is False

    @pytest.mark.asyncio
    async def test_user_without_mfa_returns_false(self, session, user):
        result = await verify_step_up_code(user.id, session, "123456")
        assert result is False

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_false(self, session):
        result = await verify_step_up_code(99999, session, "123456")
        assert result is False


# ---------------------------------------------------------------------------
# get_user_policy_role (async, needs DB)
# ---------------------------------------------------------------------------


class TestGetUserPolicyRole:
    @pytest.mark.asyncio
    async def test_no_membership_returns_editor(self, session, user):
        role = await get_user_policy_role(user.id, session)
        assert role == "editor"

    @pytest.mark.asyncio
    async def test_admin_maps_to_admin(self, session, user, org_member):
        role = await get_user_policy_role(user.id, session)
        assert role == "admin"

    @pytest.mark.asyncio
    async def test_owner_maps_to_owner(self, session, user, organization):
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=OrgRole.OWNER,
        )
        session.add(member)
        await session.commit()
        role = await get_user_policy_role(user.id, session)
        assert role == "owner"

    @pytest.mark.asyncio
    async def test_viewer_maps_to_viewer(self, session, user, organization):
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=OrgRole.VIEWER,
        )
        session.add(member)
        await session.commit()
        role = await get_user_policy_role(user.id, session)
        assert role == "viewer"

    @pytest.mark.asyncio
    async def test_member_maps_to_editor(self, session, user, organization):
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=OrgRole.MEMBER,
        )
        session.add(member)
        await session.commit()
        role = await get_user_policy_role(user.id, session)
        assert role == "editor"


# ---------------------------------------------------------------------------
# get_user_org_security_policy (async, needs DB)
# ---------------------------------------------------------------------------


class TestGetUserOrgSecurityPolicy:
    @pytest.mark.asyncio
    async def test_user_without_org_returns_defaults(self, session, user):
        policy = await get_user_org_security_policy(user.id, session)
        assert policy["require_step_up_for_sensitive_exports"] is True

    @pytest.mark.asyncio
    async def test_user_with_org_returns_org_settings(
        self, session, user, organization, org_member
    ):
        policy = await get_user_org_security_policy(user.id, session)
        assert policy["require_step_up_for_sensitive_exports"] is False
        assert policy["apply_cui_watermark_to_sensitive_exports"] is False

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_defaults(self, session):
        policy = await get_user_org_security_policy(99999, session)
        assert policy["require_step_up_for_sensitive_exports"] is True


# ---------------------------------------------------------------------------
# RedisRateLimiter
# ---------------------------------------------------------------------------


class TestRedisRateLimiter:
    @pytest.mark.asyncio
    async def test_allowed_when_under_limit(self):
        limiter = RedisRateLimiter("redis://fake:6379")
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        limiter._redis = mock_redis

        allowed, remaining = await limiter.is_allowed("test:key", 10, 3600)
        assert allowed is True
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_denied_when_over_limit(self):
        limiter = RedisRateLimiter("redis://fake:6379")
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=11)
        limiter._redis = mock_redis

        allowed, remaining = await limiter.is_allowed("test:key", 10, 3600)
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_expire_called_on_first_request(self):
        limiter = RedisRateLimiter("redis://fake:6379")
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        limiter._redis = mock_redis

        await limiter.is_allowed("test:key", 10, 3600)
        mock_redis.expire.assert_called_once_with("rate:test:key", 3600)

    @pytest.mark.asyncio
    async def test_expire_not_called_on_subsequent(self):
        limiter = RedisRateLimiter("redis://fake:6379")
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=5)
        mock_redis.expire = AsyncMock()
        limiter._redis = mock_redis

        await limiter.is_allowed("test:key", 10, 3600)
        mock_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_error(self):
        limiter = RedisRateLimiter("redis://fake:6379")
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))
        limiter._redis = mock_redis

        allowed, remaining = await limiter.is_allowed("test:key", 10, 3600)
        assert allowed is True
        assert remaining == 10


# ---------------------------------------------------------------------------
# check_rate_limit (async, uses rate_limiter global)
# ---------------------------------------------------------------------------


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_authenticated_user_uses_tier_limit(self):
        auth = UserAuth(
            id=1,
            email="a@b.com",
            full_name=None,
            company_name=None,
            tier="professional",
            is_active=True,
        )
        request = MagicMock()

        with patch("app.api.deps.rate_limiter") as mock_rl:
            mock_rl.is_allowed = AsyncMock(return_value=(True, 1999))
            await check_rate_limit(request, auth)
            mock_rl.is_allowed.assert_called_once_with(
                key="user:1", max_requests=2000, window_seconds=3600
            )

    @pytest.mark.asyncio
    async def test_unauthenticated_uses_ip(self):
        request = MagicMock()
        request.client.host = "10.0.0.1"
        request.url.path = "/api/v1/test"

        with (
            patch("app.api.deps.rate_limiter") as mock_rl,
            patch("app.api.deps.settings") as mock_settings,
        ):
            mock_settings.debug = False
            mock_rl.is_allowed = AsyncMock(return_value=(True, 49))
            await check_rate_limit(request, None)
            mock_rl.is_allowed.assert_called_once_with(
                key="ip:10.0.0.1:/api/v1/test", max_requests=50, window_seconds=3600
            )

    @pytest.mark.asyncio
    async def test_debug_mode_higher_anon_limit(self):
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.url.path = "/api/v1/auth/login"

        with (
            patch("app.api.deps.rate_limiter") as mock_rl,
            patch("app.api.deps.settings") as mock_settings,
        ):
            mock_settings.debug = True
            mock_rl.is_allowed = AsyncMock(return_value=(True, 199))
            await check_rate_limit(request, None)
            call_args = mock_rl.is_allowed.call_args
            assert call_args.kwargs["max_requests"] == 200

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_raises_429(self):
        auth = UserAuth(
            id=1, email="a@b.com", full_name=None, company_name=None, tier="free", is_active=True
        )
        request = MagicMock()

        with patch("app.api.deps.rate_limiter") as mock_rl:
            mock_rl.is_allowed = AsyncMock(return_value=(False, 0))
            with pytest.raises(HTTPException) as exc:
                await check_rate_limit(request, auth)
            assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_free_tier_limit(self):
        auth = UserAuth(
            id=1, email="a@b.com", full_name=None, company_name=None, tier="free", is_active=True
        )
        request = MagicMock()

        with patch("app.api.deps.rate_limiter") as mock_rl:
            mock_rl.is_allowed = AsyncMock(return_value=(True, 99))
            await check_rate_limit(request, auth)
            call_args = mock_rl.is_allowed.call_args
            assert call_args.kwargs["max_requests"] == 100


# ---------------------------------------------------------------------------
# track_api_usage (async, needs DB)
# ---------------------------------------------------------------------------


class TestTrackApiUsage:
    @pytest.mark.asyncio
    async def test_increments_counter(self, session, user):
        auth = UserAuth(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            tier=user.tier.value,
            is_active=True,
        )
        result = await track_api_usage(auth, session)
        assert result.id == user.id

        await session.refresh(user)
        assert user.api_calls_today == 1

    @pytest.mark.asyncio
    async def test_resets_daily_counter(self, session, user):
        user.api_calls_today = 50
        user.last_api_reset = datetime.utcnow() - timedelta(days=2)
        session.add(user)
        await session.commit()

        auth = UserAuth(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            tier=user.tier.value,
            is_active=True,
        )
        await track_api_usage(auth, session)

        await session.refresh(user)
        assert user.api_calls_today == 1  # Reset to 0 then incremented

    @pytest.mark.asyncio
    async def test_exceeds_limit_raises_429(self, session, user):
        user.api_calls_today = user.api_calls_limit
        session.add(user)
        await session.commit()

        auth = UserAuth(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            tier=user.tier.value,
            is_active=True,
        )
        with pytest.raises(HTTPException) as exc:
            await track_api_usage(auth, session)
        assert exc.value.status_code == 429
