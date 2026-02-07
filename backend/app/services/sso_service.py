"""
RFP Sniper - SSO Service
========================
Token exchange, JWT decode, and JIT user provisioning for SSO.
"""

import base64
import json
from datetime import datetime

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.integration import IntegrationProvider
from app.models.organization import (
    OrganizationMember,
    OrgRole,
    SSOIdentity,
    SSOProvider,
)
from app.models.user import User

logger = structlog.get_logger(__name__)

# Map IntegrationProvider to SSOProvider
_PROVIDER_MAP: dict[IntegrationProvider, SSOProvider] = {
    IntegrationProvider.OKTA: SSOProvider.OKTA,
    IntegrationProvider.MICROSOFT: SSOProvider.MICROSOFT,
}


async def exchange_sso_code(
    provider: IntegrationProvider,
    config: dict,
    code: str,
) -> dict:
    if settings.mock_sso:
        return {
            "status": "mocked",
            "access_token": "mock-access-token",
            "id_token": "mock-id-token",
            "token_type": "bearer",
        }

    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    redirect_uri = config.get("redirect_uri")

    if provider == IntegrationProvider.OKTA:
        issuer = config.get("issuer") or f"https://{config.get('domain')}/oauth2/default"
        token_url = f"{issuer}/v1/token"
    elif provider == IntegrationProvider.MICROSOFT:
        authority = (
            config.get("authority")
            or f"https://login.microsoftonline.com/{config.get('tenant_id')}"
        )
        token_url = f"{authority}/oauth2/v2.0/token"
    else:
        raise ValueError("Unsupported SSO provider")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if provider == IntegrationProvider.OKTA:
        data["scope"] = config.get("scopes", "openid profile email groups")
    elif provider == IntegrationProvider.MICROSOFT:
        data["scope"] = config.get("scopes", "openid profile email")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        return response.json()


def decode_id_token_claims(id_token: str) -> dict:
    """Decode JWT payload without verification (verification should be done at IdP level)."""
    try:
        parts = id_token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("Failed to decode ID token", error=str(e))
        return {}


async def provision_sso_user(
    session: AsyncSession,
    provider: IntegrationProvider,
    token_response: dict,
    organization_id: int | None = None,
) -> tuple[User, bool]:
    """
    JIT (Just-In-Time) provisioning: find or create a user from SSO claims.

    Returns (user, created) tuple.
    """
    id_token = token_response.get("id_token", "")
    claims = decode_id_token_claims(id_token)

    if not claims:
        raise ValueError("Could not extract claims from ID token")

    sso_provider = _PROVIDER_MAP.get(provider)
    if not sso_provider:
        raise ValueError(f"Unsupported provider: {provider}")

    subject = claims.get("sub", "")
    email = claims.get("email", "")
    name = claims.get("name") or claims.get("preferred_username", "")
    groups = claims.get("groups", [])

    if not email:
        raise ValueError("No email claim in ID token")

    # Check if SSO identity already exists
    existing_identity = (
        await session.exec(
            select(SSOIdentity).where(
                SSOIdentity.provider == sso_provider,
                SSOIdentity.subject == subject,
            )
        )
    ).first()

    if existing_identity:
        # Update last login
        existing_identity.last_login_at = datetime.utcnow()
        existing_identity.groups = groups
        existing_identity.id_token_claims = claims
        session.add(existing_identity)

        user = (
            await session.exec(select(User).where(User.id == existing_identity.user_id))
        ).first()
        if user:
            await session.commit()
            return user, False
        # Identity exists but user deleted — fall through to create

    # Look up user by email
    user = (await session.exec(select(User).where(User.email == email))).first()
    created = False

    if not user:
        # Auto-provision new user
        user = User(
            email=email,
            full_name=name,
            hashed_password="SSO_MANAGED",  # SSO users don't have passwords
            is_active=True,
            organization_id=organization_id,
        )
        session.add(user)
        await session.flush()  # Get user.id
        created = True

        # Add to organization if specified
        if organization_id:
            org_member = OrganizationMember(
                organization_id=organization_id,
                user_id=user.id,  # type: ignore[arg-type]
                role=_map_groups_to_role(groups),
            )
            session.add(org_member)

        logger.info("SSO user provisioned", email=email, provider=sso_provider.value)
    else:
        # Link existing user to org if not already linked
        if organization_id and not user.organization_id:
            user.organization_id = organization_id
            session.add(user)

    # Create or update SSO identity
    if not existing_identity:
        sso_identity = SSOIdentity(
            user_id=user.id,  # type: ignore[arg-type]
            provider=sso_provider,
            subject=subject,
            email=email,
            name=name,
            groups=groups,
            id_token_claims=claims,
            last_login_at=datetime.utcnow(),
        )
        session.add(sso_identity)

    await session.commit()
    return user, created


def _map_groups_to_role(groups: list[str]) -> OrgRole:
    """Map SSO group names to organization roles (highest privilege wins)."""
    group_lower = {g.lower() for g in groups}
    if any(k in group_lower for k in ("owner", "owners", "org-owner")):
        return OrgRole.OWNER
    if any(k in group_lower for k in ("admin", "admins", "org-admin", "administrators")):
        return OrgRole.ADMIN
    if any(k in group_lower for k in ("viewer", "viewers", "read-only")):
        return OrgRole.VIEWER
    return OrgRole.MEMBER
