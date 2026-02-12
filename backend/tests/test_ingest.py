from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.api.routes import ingest as ingest_routes
from app.models.user import User
from app.schemas.rfp import SAMIngestResponse
from app.services.auth_service import create_token_pair, hash_password
from app.services.ingest_service import SAMGovAPIError, SAMGovService


class TestIngest:
    async def test_trigger_ingest_falls_back_to_sync_when_worker_is_unavailable(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(ingest_routes.settings, "mock_sam_gov", True)
        monkeypatch.setattr(ingest_routes.settings, "debug", True)
        monkeypatch.setattr(ingest_routes, "_celery_broker_available", lambda: True)
        monkeypatch.setattr(ingest_routes, "_celery_worker_available", lambda: False)

        async def fake_sync_ingest(**kwargs):
            return SAMIngestResponse(
                task_id="sync-ingest-worker-missing",
                message="Ingest completed synchronously",
                status="completed",
                opportunities_found=2,
            )

        monkeypatch.setattr(ingest_routes, "_run_synchronous_ingest", fake_sync_ingest)

        response = await client.post(
            "/api/v1/ingest/sam",
            headers=auth_headers,
            json={
                "keywords": "software",
                "days_back": 30,
                "limit": 10,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["task_id"] == "sync-ingest-worker-missing"
        assert payload["opportunities_found"] == 2

    async def test_trigger_ingest_falls_back_to_sync_when_broker_is_unavailable(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(ingest_routes.settings, "mock_sam_gov", True)
        monkeypatch.setattr(ingest_routes.settings, "debug", True)
        monkeypatch.setattr(ingest_routes, "_celery_broker_available", lambda: False)

        async def fake_sync_ingest(**kwargs):
            return SAMIngestResponse(
                task_id="sync-ingest-1",
                message="Ingest completed synchronously",
                status="completed",
                opportunities_found=3,
            )

        monkeypatch.setattr(ingest_routes, "_run_synchronous_ingest", fake_sync_ingest)

        response = await client.post(
            "/api/v1/ingest/sam",
            headers=auth_headers,
            json={
                "keywords": "software",
                "days_back": 30,
                "limit": 10,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["task_id"] == "sync-ingest-1"
        assert payload["opportunities_found"] == 3

    async def test_sync_ingest_invalidates_cached_rfp_list(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(ingest_routes.settings, "mock_sam_gov", True)
        monkeypatch.setattr(ingest_routes.settings, "debug", True)
        monkeypatch.setattr(ingest_routes, "_celery_broker_available", lambda: False)

        # Prime the cache with an empty list.
        initial = await client.get("/api/v1/rfps", headers=auth_headers)
        assert initial.status_code == 200
        assert initial.json() == []

        ingest_response = await client.post(
            "/api/v1/ingest/sam",
            headers=auth_headers,
            json={
                "keywords": "software",
                "days_back": 30,
                "limit": 3,
            },
        )
        assert ingest_response.status_code == 200
        assert ingest_response.json()["status"] == "completed"

        refreshed = await client.get("/api/v1/rfps", headers=auth_headers)
        assert refreshed.status_code == 200
        assert len(refreshed.json()) > 0

    async def test_sync_ingest_allows_same_solicitation_numbers_across_users(
        self,
        client: AsyncClient,
        db_session,
        auth_headers: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(ingest_routes.settings, "mock_sam_gov", True)
        monkeypatch.setattr(ingest_routes.settings, "debug", True)
        monkeypatch.setattr(ingest_routes, "_celery_broker_available", lambda: False)

        first_ingest = await client.post(
            "/api/v1/ingest/sam",
            headers=auth_headers,
            json={
                "keywords": "software",
                "days_back": 30,
                "limit": 3,
            },
        )
        assert first_ingest.status_code == 200
        assert first_ingest.json()["status"] == "completed"

        second_user = User(
            email="second-ingest-user@example.com",
            hashed_password=hash_password("TestPassword123!"),
            full_name="Second Ingest User",
            company_name="Second Co",
            tier="free",
            is_active=True,
            is_verified=True,
        )
        db_session.add(second_user)
        await db_session.commit()
        await db_session.refresh(second_user)
        second_token = create_token_pair(
            second_user.id,
            second_user.email,
            second_user.tier,
        ).access_token
        second_headers = {"Authorization": f"Bearer {second_token}"}

        second_ingest = await client.post(
            "/api/v1/ingest/sam",
            headers=second_headers,
            json={
                "keywords": "software",
                "days_back": 30,
                "limit": 3,
            },
        )
        assert second_ingest.status_code == 200
        assert second_ingest.json()["status"] == "completed"

        first_rfps = await client.get("/api/v1/rfps", headers=auth_headers)
        assert first_rfps.status_code == 200
        second_rfps = await client.get("/api/v1/rfps", headers=second_headers)
        assert second_rfps.status_code == 200
        assert len(second_rfps.json()) > 0

        first_solicitations = {rfp["solicitation_number"] for rfp in first_rfps.json()}
        second_solicitations = {rfp["solicitation_number"] for rfp in second_rfps.json()}

        assert first_solicitations == second_solicitations
        assert all(
            not solicitation.endswith(f"-U{second_user.id}")
            for solicitation in second_solicitations
        )

    async def test_trigger_ingest_returns_429_when_sam_is_rate_limited(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        monkeypatch.setattr(ingest_routes.settings, "mock_sam_gov", False)
        monkeypatch.setattr(ingest_routes.settings, "sam_gov_api_key", "test-key")
        monkeypatch.setattr(ingest_routes.settings, "debug", True)
        monkeypatch.setattr(ingest_routes, "_celery_broker_available", lambda: False)

        async def fake_sync_ingest(**kwargs):
            raise SAMGovAPIError(
                "SAM.gov rate limited",
                status_code=429,
                is_rate_limited=True,
                retry_after_seconds=45,
            )

        monkeypatch.setattr(ingest_routes, "_run_synchronous_ingest", fake_sync_ingest)

        response = await client.post(
            "/api/v1/ingest/sam",
            headers=auth_headers,
            json={"keywords": "software", "days_back": 30, "limit": 10},
        )

        assert response.status_code == 429
        assert "Retry in about 45 seconds" in response.json()["detail"]
        assert response.headers.get("retry-after") == "45"

    async def test_quick_search_returns_429_when_sam_is_rate_limited(
        self,
        client: AsyncClient,
        monkeypatch,
    ):
        monkeypatch.setattr(ingest_routes.settings, "mock_sam_gov", False)
        monkeypatch.setattr(ingest_routes.settings, "sam_gov_api_key", "test-key")

        async def fake_search(self, params):
            raise SAMGovAPIError(
                "SAM.gov rate limited",
                status_code=429,
                is_rate_limited=True,
                retry_after_seconds=30,
            )

        monkeypatch.setattr(SAMGovService, "search_opportunities", fake_search)

        response = await client.post(
            "/api/v1/ingest/sam/quick-search",
            params={"keywords": "software", "limit": 5, "days_back": 30},
        )

        assert response.status_code == 429
        assert "Retry in about 30 seconds" in response.json()["detail"]
        assert response.headers.get("retry-after") == "30"

    def test_open_circuit_uses_retry_after_window(self, monkeypatch):
        monkeypatch.setattr(ingest_routes.settings, "sam_circuit_breaker_enabled", True)
        monkeypatch.setattr(ingest_routes.settings, "sam_circuit_breaker_cooldown_seconds", 900)
        monkeypatch.setattr(ingest_routes.settings, "sam_circuit_breaker_max_seconds", 3600)

        service = SAMGovService(api_key="test-key")
        service.__class__._circuit_open_until = None
        service.__class__._circuit_reason = None

        start = datetime.utcnow()
        service._open_circuit(60, reason="rate_limited")

        assert service.__class__._circuit_open_until is not None
        remaining = (service.__class__._circuit_open_until - start).total_seconds()
        assert 55 <= remaining <= 65

    def test_open_circuit_honors_long_retry_after_even_with_low_configured_cap(self, monkeypatch):
        monkeypatch.setattr(ingest_routes.settings, "sam_circuit_breaker_enabled", True)
        monkeypatch.setattr(ingest_routes.settings, "sam_circuit_breaker_cooldown_seconds", 900)
        monkeypatch.setattr(ingest_routes.settings, "sam_circuit_breaker_max_seconds", 60)

        service = SAMGovService(api_key="test-key")
        service.__class__._circuit_open_until = None
        service.__class__._circuit_reason = None

        start = datetime.utcnow()
        service._open_circuit(7200, reason="rate_limited")

        assert service.__class__._circuit_open_until is not None
        remaining = (service.__class__._circuit_open_until - start).total_seconds()
        assert 7190 <= remaining <= 7210

    @pytest.mark.asyncio
    async def test_circuit_open_error_includes_remaining_retry_after(self, monkeypatch):
        monkeypatch.setattr(ingest_routes.settings, "sam_circuit_breaker_enabled", True)

        service = SAMGovService(api_key="test-key")
        service.__class__._circuit_reason = "rate_limited"
        service.__class__._circuit_open_until = datetime.utcnow() + timedelta(seconds=30)

        with pytest.raises(SAMGovAPIError) as exc_info:
            await service._make_request({"limit": 1})

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after_seconds is not None
        assert 1 <= exc_info.value.retry_after_seconds <= 30
