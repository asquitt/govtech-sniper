from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.main import app


class TestOnboarding:
    async def test_get_progress_returns_default_steps(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/onboarding/progress", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_steps"] == 6
        assert data["completed_count"] >= 1
        assert any(step["id"] == "create_account" and step["completed"] for step in data["steps"])

    async def test_mark_step_complete_and_dismiss(self, client: AsyncClient, auth_headers: dict):
        complete_response = await client.post(
            "/api/v1/onboarding/steps/upload_rfp/complete",
            headers=auth_headers,
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["step_id"] == "upload_rfp"

        progress_response = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        assert progress_response.status_code == 200
        progress_payload = progress_response.json()
        upload_step = next(step for step in progress_payload["steps"] if step["id"] == "upload_rfp")
        assert upload_step["completed"] is True

        dismiss_response = await client.post("/api/v1/onboarding/dismiss", headers=auth_headers)
        assert dismiss_response.status_code == 200

        progress_after_dismiss = await client.get(
            "/api/v1/onboarding/progress", headers=auth_headers
        )
        assert progress_after_dismiss.status_code == 200
        assert progress_after_dismiss.json()["is_dismissed"] is True


class TestNotifications:
    async def test_list_without_trailing_slash_does_not_redirect(
        self, db_session: AsyncSession, auth_headers: dict
    ):
        async def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
        transport = ASGITransport(app=app)

        try:
            async with AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=False
            ) as client:
                response = await client.get(
                    "/api/v1/notifications?limit=20",
                    headers=auth_headers,
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.headers.get("location") is None
        assert response.json() == []
