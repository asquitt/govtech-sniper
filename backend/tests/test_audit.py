"""
RFP Sniper - Audit Tests
========================
Integration tests for audit log endpoints (list, summary, export).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.user import User


@pytest_asyncio.fixture
async def audit_events(db_session: AsyncSession, test_user: User) -> list[AuditEvent]:
    """Seed deterministic audit events for testing."""
    events = [
        AuditEvent(
            user_id=test_user.id,
            entity_type="rfp",
            entity_id=1,
            action="rfp.created",
            event_metadata={"title": "Test RFP"},
        ),
        AuditEvent(
            user_id=test_user.id,
            entity_type="rfp",
            entity_id=1,
            action="rfp.analyzed",
            event_metadata={"status": "complete"},
        ),
        AuditEvent(
            user_id=test_user.id,
            entity_type="proposal",
            entity_id=10,
            action="proposal.created",
            event_metadata={"title": "My Proposal"},
        ),
        AuditEvent(
            user_id=test_user.id,
            entity_type="award",
            entity_id=5,
            action="award.created",
            event_metadata={"awardee": "Acme"},
        ),
    ]
    for e in events:
        db_session.add(e)
    await db_session.commit()
    for e in events:
        await db_session.refresh(e)
    return events


# ---- Auth guards ----


class TestAuditAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/audit")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_summary_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/audit/summary")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/audit/export")
        assert resp.status_code == 401


# ---- List endpoint ----


class TestAuditList:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/audit", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_all(self, client: AsyncClient, auth_headers: dict, audit_events):
        resp = await client.get("/api/v1/audit", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 4

    @pytest.mark.asyncio
    async def test_list_filter_by_entity_type(
        self, client: AsyncClient, auth_headers: dict, audit_events
    ):
        resp = await client.get(
            "/api/v1/audit",
            headers=auth_headers,
            params={"entity_type": "rfp"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(e["entity_type"] == "rfp" for e in data)

    @pytest.mark.asyncio
    async def test_list_filter_by_action(
        self, client: AsyncClient, auth_headers: dict, audit_events
    ):
        resp = await client.get(
            "/api/v1/audit",
            headers=auth_headers,
            params={"action": "award.created"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["action"] == "award.created"

    @pytest.mark.asyncio
    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict, audit_events):
        resp = await client.get(
            "/api/v1/audit",
            headers=auth_headers,
            params={"limit": 2, "offset": 0},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp2 = await client.get(
            "/api/v1/audit",
            headers=auth_headers,
            params={"limit": 2, "offset": 2},
        )
        assert resp2.status_code == 200
        assert len(resp2.json()) == 2

        # No overlap between pages
        ids_page1 = {e["id"] for e in resp.json()}
        ids_page2 = {e["id"] for e in resp2.json()}
        assert ids_page1.isdisjoint(ids_page2)


# ---- Summary endpoint ----


class TestAuditSummary:
    @pytest.mark.asyncio
    async def test_summary_empty(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/audit/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 0
        assert data["by_action"] == []
        assert data["by_entity_type"] == []

    @pytest.mark.asyncio
    async def test_summary_with_events(self, client: AsyncClient, auth_headers: dict, audit_events):
        resp = await client.get("/api/v1/audit/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 4
        assert data["period_days"] == 30

        action_names = {item["action"] for item in data["by_action"]}
        assert "rfp.created" in action_names
        assert "proposal.created" in action_names

        entity_names = {item["entity_type"] for item in data["by_entity_type"]}
        assert "rfp" in entity_names
        assert "proposal" in entity_names

    @pytest.mark.asyncio
    async def test_summary_custom_days(self, client: AsyncClient, auth_headers: dict, audit_events):
        resp = await client.get(
            "/api/v1/audit/summary",
            headers=auth_headers,
            params={"days": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_days"] == 1
        # Events created just now should be within 1-day window
        assert data["total_events"] == 4


# ---- Export endpoint ----


class TestAuditExport:
    @pytest.mark.asyncio
    async def test_export_json_with_signature(
        self, client: AsyncClient, auth_headers: dict, audit_events
    ):
        resp = await client.get(
            "/api/v1/audit/export",
            headers=auth_headers,
            params={"format": "json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "signature" in data
        assert "payload" in data
        assert data["payload"]["count"] >= 4
        assert len(data["payload"]["records"]) >= 4
        assert resp.headers.get("X-Audit-Signature") == data["signature"]

    @pytest.mark.asyncio
    async def test_export_csv_with_signature(
        self, client: AsyncClient, auth_headers: dict, audit_events
    ):
        resp = await client.get(
            "/api/v1/audit/export",
            headers=auth_headers,
            params={"format": "csv"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-Audit-Signature")
        content = resp.text
        # CSV should have header + data rows
        lines = content.strip().split("\n")
        assert len(lines) >= 5  # header + 4 events
        assert "id,user_id,entity_type" in lines[0]

    @pytest.mark.asyncio
    async def test_export_empty(self, client: AsyncClient, auth_headers: dict):
        """Export with no events still returns valid structure."""
        resp = await client.get(
            "/api/v1/audit/export",
            headers=auth_headers,
            params={"format": "json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # count may include the audit.exported event itself
        assert data["payload"]["count"] >= 0

    @pytest.mark.asyncio
    async def test_export_json_records_contain_expected_fields(
        self, client: AsyncClient, auth_headers: dict, audit_events
    ):
        resp = await client.get(
            "/api/v1/audit/export",
            headers=auth_headers,
            params={"format": "json"},
        )
        assert resp.status_code == 200
        record = resp.json()["payload"]["records"][0]
        assert "id" in record
        assert "user_id" in record
        assert "entity_type" in record
        assert "action" in record
        assert "metadata" in record
        assert "created_at" in record


# ---- Original combined flow test ----


class TestAuditFlows:
    @pytest.mark.asyncio
    async def test_audit_list_and_summary_via_side_effect(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Generate audit events via integration create, then verify audit trail."""
        response = await client.post(
            "/api/v1/integrations",
            headers=auth_headers,
            json={
                "provider": "okta",
                "name": "Okta SSO",
                "config": {"domain": "example.okta.com"},
            },
        )
        assert response.status_code == 200

        response = await client.get("/api/v1/audit", headers=auth_headers)
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert any(event["action"] == "integration.created" for event in events)

        response = await client.get("/api/v1/audit/summary", headers=auth_headers)
        assert response.status_code == 200
        summary = response.json()
        assert summary["total_events"] >= 1
