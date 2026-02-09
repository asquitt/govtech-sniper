from httpx import AsyncClient

from app.api.routes import ingest as ingest_routes
from app.models.user import User
from app.schemas.rfp import SAMIngestResponse
from app.services.auth_service import create_token_pair, hash_password


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

    async def test_sync_ingest_handles_global_solicitation_uniqueness_for_mock_data(
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

        second_rfps = await client.get("/api/v1/rfps", headers=second_headers)
        assert second_rfps.status_code == 200
        assert len(second_rfps.json()) > 0
