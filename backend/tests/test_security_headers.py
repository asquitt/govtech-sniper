"""Tests for security headers middleware."""

import pytest
from httpx import AsyncClient


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
        """HSTS should not be set in debug/test mode."""
        response = await client.get("/health")
        # In test mode (debug=True), HSTS should not be present
        assert "strict-transport-security" not in response.headers
