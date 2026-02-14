"""Tests for security headers middleware."""

import pytest
from httpx import AsyncClient

from app.main import SecurityHeadersMiddleware, app


def _security_headers_debug_enabled() -> bool:
    for middleware in app.user_middleware:
        if middleware.cls is SecurityHeadersMiddleware:
            return bool(middleware.kwargs.get("debug", False))
    raise AssertionError("SecurityHeadersMiddleware is not configured")


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_health_endpoint_has_security_headers(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-xss-protection"] == "1; mode=block"
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "content-security-policy" in response.headers
        assert "default-src 'self'" in response.headers["content-security-policy"]

    @pytest.mark.asyncio
    async def test_hsts_absent_in_debug_mode(self, client: AsyncClient):
        """HSTS behavior should match configured debug mode."""
        response = await client.get("/health")
        if _security_headers_debug_enabled():
            assert "strict-transport-security" not in response.headers
            return
        assert (
            response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
        )
