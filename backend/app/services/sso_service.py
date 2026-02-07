"""
RFP Sniper - SSO Service
========================
Token exchange helpers for Okta and Microsoft Entra ID.
"""


import httpx

from app.config import settings
from app.models.integration import IntegrationProvider


async def exchange_sso_code(
    provider: IntegrationProvider,
    config: dict,
    code: str,
) -> dict:
    if settings.mock_sso:
        return {
            "status": "mocked",
            "access_token": "mock-access-token",
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

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        return response.json()
