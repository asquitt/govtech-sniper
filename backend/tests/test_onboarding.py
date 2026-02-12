from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.main import app
from app.models.user import User, UserTier


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


class TestOnboardingTimestamps:
    async def test_progress_records_step_timestamps(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "step_timestamps" in data
        assert "create_account" in data["step_timestamps"]

    async def test_manual_complete_records_timestamp(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/v1/onboarding/steps/upload_rfp/complete",
            headers=auth_headers,
        )
        assert response.status_code == 200

        progress = await client.get("/api/v1/onboarding/progress", headers=auth_headers)
        data = progress.json()
        assert "upload_rfp" in data["step_timestamps"]
        # Timestamp should be an ISO format string
        ts = data["step_timestamps"]["upload_rfp"]
        assert "T" in ts  # basic ISO format check

    async def test_activation_metrics_endpoint(self, client: AsyncClient, auth_headers: dict):
        # First create some onboarding data
        await client.get("/api/v1/onboarding/progress", headers=auth_headers)

        # Metrics endpoint requires enterprise tier — default test user is 'professional'
        response = await client.get("/api/v1/onboarding/activation-metrics", headers=auth_headers)
        assert response.status_code == 403

    async def test_activation_metrics_shape(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user
    ):
        """Verify response shape by temporarily upgrading user to admin tier."""
        user = (await db_session.execute(select(User).where(User.id == test_user.id))).scalar_one()
        user.tier = UserTier.ENTERPRISE
        db_session.add(user)
        await db_session.commit()

        # Seed onboarding data
        await client.get("/api/v1/onboarding/progress", headers=auth_headers)

        response = await client.get("/api/v1/onboarding/activation-metrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "fully_activated" in data
        assert "step_completion_rates" in data
        assert "median_time_to_first_proposal_hours" in data
        assert isinstance(data["total_users"], int)
        assert isinstance(data["step_completion_rates"], dict)


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
