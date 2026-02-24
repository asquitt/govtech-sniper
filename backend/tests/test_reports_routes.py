"""
Integration tests for reports.py — /reports/ CRUD, generate, export, schedule, share, delivery
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password


async def _create_second_user(db_session: AsyncSession) -> tuple[User, dict]:
    user2 = User(
        email="other@example.com",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    tokens = create_token_pair(user2.id, user2.email, user2.tier)
    return user2, {"Authorization": f"Bearer {tokens.access_token}"}


def _report_payload(name: str = "Pipeline Report") -> dict:
    return {
        "name": name,
        "report_type": "pipeline",
        "config": {"columns": ["opportunity", "agency"], "filters": {}},
    }


class TestCreateReport:
    """POST /api/v1/reports"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/reports", json=_report_payload())
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_report(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Pipeline Report"
        assert data["report_type"] == "pipeline"


class TestListReports:
    """GET /api/v1/reports"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/reports")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_own_reports(self, client: AsyncClient, auth_headers: dict, test_user: User):
        await client.post("/api/v1/reports", headers=auth_headers, json=_report_payload("R1"))
        await client.post("/api/v1/reports", headers=auth_headers, json=_report_payload("R2"))

        response = await client.get("/api/v1/reports", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestGetReport:
    """GET /api/v1/reports/{report_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/reports/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_own_report(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/reports/{report_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == report_id

    @pytest.mark.asyncio
    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/reports/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_idor_report(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, headers2 = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/reports", headers=headers2, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/reports/{report_id}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateReport:
    """PATCH /api/v1/reports/{report_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/reports/1", json={"name": "X"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_report(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/reports/{report_id}",
            headers=auth_headers,
            json={"name": "Updated Report"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Report"

    @pytest.mark.asyncio
    async def test_update_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, headers2 = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/reports", headers=headers2, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/reports/{report_id}",
            headers=auth_headers,
            json={"name": "Hacked"},
        )
        assert response.status_code in (403, 404)


class TestDeleteReport:
    """DELETE /api/v1/reports/{report_id}"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/reports/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_report(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/reports/{report_id}", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_idor(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        user2, headers2 = await _create_second_user(db_session)
        create_response = await client.post(
            "/api/v1/reports", headers=headers2, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/reports/{report_id}", headers=auth_headers)
        assert response.status_code in (403, 404)


class TestGenerateReport:
    """POST /api/v1/reports/{report_id}/generate"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/reports/1/generate")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_report(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.post(f"/api/v1/reports/{report_id}/generate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "columns" in data
        assert "rows" in data
        assert "total_rows" in data


class TestExportReport:
    """POST /api/v1/reports/{report_id}/export"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/reports/1/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_csv(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.post(f"/api/v1/reports/{report_id}/export", headers=auth_headers)
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "attachment" in response.headers.get("content-disposition", "")


class TestScheduleReport:
    """POST /api/v1/reports/{report_id}/schedule"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/reports/1/schedule")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_set_schedule(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/reports/{report_id}/schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "recipients": ["team@example.com"],
                "enabled": True,
                "subject": "Weekly Pipeline",
            },
        )
        assert response.status_code == 200
        assert response.json()["schedule"] == "weekly"


class TestShareReport:
    """PATCH /api/v1/reports/{report_id}/share"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.patch("/api/v1/reports/1/share", json={"is_shared": True})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_share_report(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/reports/{report_id}/share",
            headers=auth_headers,
            json={"is_shared": True, "shared_with_emails": ["team@example.com"]},
        )
        assert response.status_code == 200
        assert response.json()["is_shared"] is True
        assert "team@example.com" in response.json()["shared_with_emails"]


class TestDeliverySchedule:
    """GET /api/v1/reports/{report_id}/delivery"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/reports/1/delivery")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_delivery_schedule(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/reports/{report_id}/delivery", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "frequency" in data


class TestSendDelivery:
    """POST /api/v1/reports/{report_id}/delivery/send"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/reports/1/delivery/send")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_send_without_schedule_fails(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/reports/{report_id}/delivery/send", headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_send_delivery(self, client: AsyncClient, auth_headers: dict, test_user: User):
        create_response = await client.post(
            "/api/v1/reports", headers=auth_headers, json=_report_payload()
        )
        report_id = create_response.json()["id"]

        # Set schedule first
        await client.post(
            f"/api/v1/reports/{report_id}/schedule",
            headers=auth_headers,
            json={
                "frequency": "weekly",
                "recipients": ["team@example.com"],
                "enabled": True,
            },
        )

        response = await client.post(
            f"/api/v1/reports/{report_id}/delivery/send", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["recipient_count"] == 1
