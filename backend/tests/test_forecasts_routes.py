"""
Integration tests for forecasts.py — /api/v1/forecasts/
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


class TestListForecasts:
    """Tests for GET /api/v1/forecasts."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/forecasts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/forecasts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


class TestCreateForecast:
    """Tests for POST /api/v1/forecasts."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/forecasts",
            json={"title": "Test Forecast"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_forecast(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={
                "title": "FY26 Cloud Services",
                "agency": "DoD",
                "naics_code": "541512",
                "estimated_value": 5000000,
                "fiscal_year": 2026,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "FY26 Cloud Services"
        assert data["agency"] == "DoD"
        assert data["fiscal_year"] == 2026

    @pytest.mark.asyncio
    async def test_create_minimal(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={"title": "Minimal"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Minimal"


class TestUpdateForecast:
    """Tests for PATCH /api/v1/forecasts/{forecast_id}."""

    @pytest.mark.asyncio
    async def test_update_forecast(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={"title": "Before Update"},
        )
        fid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/forecasts/{fid}",
            headers=auth_headers,
            json={"title": "After Update", "agency": "NASA"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "After Update"
        assert response.json()["agency"] == "NASA"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(
            "/api/v1/forecasts/99999",
            headers=auth_headers,
            json={"title": "Ghost"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        create_resp = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={"title": "Owner A"},
        )
        fid = create_resp.json()["id"]

        user_b = User(
            email="other@example.com",
            hashed_password=hash_password("Pwd123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user_b)
        await db_session.commit()
        await db_session.refresh(user_b)
        tokens = create_token_pair(user_b.id, user_b.email, user_b.tier)
        headers_b = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"/api/v1/forecasts/{fid}",
            headers=headers_b,
            json={"title": "Hacked"},
        )
        assert response.status_code == 404


class TestDeleteForecast:
    """Tests for DELETE /api/v1/forecasts/{forecast_id}."""

    @pytest.mark.asyncio
    async def test_delete_forecast(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={"title": "To Delete"},
        )
        fid = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/forecasts/{fid}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Forecast deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete("/api/v1/forecasts/99999", headers=auth_headers)
        assert response.status_code == 404


class TestLinkForecast:
    """Tests for POST /api/v1/forecasts/{forecast_id}/link/{rfp_id}."""

    @pytest.mark.asyncio
    async def test_link_forecast_to_rfp(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        create_resp = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={"title": "Linkable"},
        )
        fid = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/forecasts/{fid}/link/{test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["linked_rfp_id"] == test_rfp.id

    @pytest.mark.asyncio
    async def test_link_forecast_not_found(
        self, client: AsyncClient, auth_headers: dict, test_rfp: RFP
    ):
        response = await client.post(
            f"/api/v1/forecasts/99999/link/{test_rfp.id}", headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_rfp_not_found(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={"title": "NoRFP"},
        )
        fid = create_resp.json()["id"]

        response = await client.post(f"/api/v1/forecasts/{fid}/link/99999", headers=auth_headers)
        assert response.status_code == 404


class TestForecastMatching:
    """Tests for POST /api/v1/forecasts/match."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/forecasts/match")
        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.routes.forecasts.run_forecast_matching", new_callable=AsyncMock)
    async def test_trigger_matching(
        self, mock_match: AsyncMock, client: AsyncClient, auth_headers: dict
    ):
        mock_match.return_value = []
        response = await client.post("/api/v1/forecasts/match", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["new_alerts"] == 0


class TestForecastAlerts:
    """Tests for GET /api/v1/forecasts/alerts."""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/forecasts/alerts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_alerts_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/forecasts/alerts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


class TestDismissAlert:
    """Tests for PATCH /api/v1/forecasts/alerts/{alert_id}."""

    @pytest.mark.asyncio
    async def test_dismiss_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch("/api/v1/forecasts/alerts/99999", headers=auth_headers)
        assert response.status_code == 404
