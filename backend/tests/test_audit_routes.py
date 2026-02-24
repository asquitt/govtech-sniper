"""
Integration tests for audit.py routes:
  - GET  /api/v1/audit
  - GET  /api/v1/audit/summary
  - GET  /api/v1/audit/export
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    user = User(
        email="audit-second@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Audit Second",
        company_name="Other Co",
        tier="free",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_headers(second_user: User) -> dict:
    tokens = create_token_pair(second_user.id, second_user.email, second_user.tier)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture
async def audit_events(db_session: AsyncSession, test_user: User) -> list[AuditEvent]:
    events = []
    for i in range(3):
        event = AuditEvent(
            user_id=test_user.id,
            entity_type="rfp",
            entity_id=i + 1,
            action=f"rfp.action_{i}",
            event_metadata={"index": i},
        )
        db_session.add(event)
        events.append(event)
    await db_session.commit()
    for e in events:
        await db_session.refresh(e)
    return events


# ---------------------------------------------------------------------------
# GET /api/v1/audit
# ---------------------------------------------------------------------------


class TestListAuditEvents:
    """GET /api/v1/audit"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/audit")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/audit", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_returns_events(
        self, client: AsyncClient, auth_headers: dict, audit_events: list[AuditEvent]
    ):
        response = await client.get("/api/v1/audit", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_filter_by_entity_type(
        self, client: AsyncClient, auth_headers: dict, audit_events: list[AuditEvent]
    ):
        response = await client.get("/api/v1/audit?entity_type=rfp", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_filter_by_action(
        self, client: AsyncClient, auth_headers: dict, audit_events: list[AuditEvent]
    ):
        response = await client.get("/api/v1/audit?action=rfp.action_0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["action"] == "rfp.action_0"

    @pytest.mark.asyncio
    async def test_pagination(
        self, client: AsyncClient, auth_headers: dict, audit_events: list[AuditEvent]
    ):
        response = await client.get("/api/v1/audit?limit=2&offset=0", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_idor_isolation(
        self,
        client: AsyncClient,
        second_headers: dict,
        audit_events: list[AuditEvent],
    ):
        """Second user should not see first user's audit events."""
        response = await client.get("/api/v1/audit", headers=second_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# GET /api/v1/audit/summary
# ---------------------------------------------------------------------------


class TestAuditSummary:
    """GET /api/v1/audit/summary"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/audit/summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_summary(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/audit/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_events" in data
        assert "by_action" in data
        assert "by_entity_type" in data

    @pytest.mark.asyncio
    async def test_summary_with_events(
        self,
        client: AsyncClient,
        auth_headers: dict,
        audit_events: list[AuditEvent],
    ):
        response = await client.get("/api/v1/audit/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] >= 3
        assert len(data["by_action"]) >= 1

    @pytest.mark.asyncio
    async def test_custom_days(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/audit/summary?days=7", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["period_days"] == 7


# ---------------------------------------------------------------------------
# GET /api/v1/audit/export
# ---------------------------------------------------------------------------


class TestAuditExport:
    """GET /api/v1/audit/export"""

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/audit/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_json(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/audit/export?format=json", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "signature" in data
        assert "payload" in data
        assert "records" in data["payload"]
        assert "X-Audit-Signature" in response.headers

    @pytest.mark.asyncio
    async def test_export_csv(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/audit/export?format=csv", headers=auth_headers)
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "X-Audit-Signature" in response.headers

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/audit/export?format=xml", headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_export_creates_audit_event(self, client: AsyncClient, auth_headers: dict):
        """Exporting audit logs should itself create an audit event."""
        await client.get("/api/v1/audit/export?format=json", headers=auth_headers)
        response = await client.get("/api/v1/audit?action=audit.exported", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_export_with_events(
        self,
        client: AsyncClient,
        auth_headers: dict,
        audit_events: list[AuditEvent],
    ):
        response = await client.get("/api/v1/audit/export?format=json", headers=auth_headers)
        assert response.status_code == 200
        records = response.json()["payload"]["records"]
        assert len(records) >= 3
