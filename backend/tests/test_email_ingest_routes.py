"""
Integration tests for email_ingest.py:
  - POST   /email-ingest/config
  - GET    /email-ingest/config
  - PATCH  /email-ingest/config/{id}
  - DELETE /email-ingest/config/{id}
  - POST   /email-ingest/config/{id}/test
  - GET    /email-ingest/history
  - POST   /email-ingest/process/{id}
  - POST   /email-ingest/sync-now
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_ingest import EmailIngestConfig, EmailProcessingStatus, IngestedEmail
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password
from app.services.encryption_service import encrypt_value


@pytest.fixture
async def email_config(db_session: AsyncSession, test_user: User) -> EmailIngestConfig:
    """Create an email ingest config for testing."""
    cfg = EmailIngestConfig(
        user_id=test_user.id,
        imap_server="imap.test.com",
        imap_port=993,
        email_address="inbox@test.com",
        encrypted_password=encrypt_value("secret"),
        folder="INBOX",
    )
    db_session.add(cfg)
    await db_session.commit()
    await db_session.refresh(cfg)
    return cfg


class TestCreateConfig:
    """Tests for POST /api/v1/email-ingest/config."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/email-ingest/config",
            json={
                "imap_server": "imap.test.com",
                "email_address": "a@b.com",
                "password": "pass",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post(
            "/api/v1/email-ingest/config",
            headers=auth_headers,
            json={
                "imap_server": "imap.example.com",
                "email_address": "rfps@example.com",
                "password": "secret123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imap_server"] == "imap.example.com"
        assert data["email_address"] == "rfps@example.com"
        # Password should be masked
        assert data["encrypted_password"] == "********"


class TestListConfigs:
    """Tests for GET /api/v1/email-ingest/config."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/email-ingest/config")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        email_config: EmailIngestConfig,
        test_user: User,
    ):
        response = await client.get("/api/v1/email-ingest/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["imap_server"] == "imap.test.com"

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        email_config: EmailIngestConfig,
        db_session: AsyncSession,
    ):
        other = User(
            email="other@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get("/api/v1/email-ingest/config", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestUpdateConfig:
    """Tests for PATCH /api/v1/email-ingest/config/{id}."""

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, client: AsyncClient):
        response = await client.patch(
            "/api/v1/email-ingest/config/1",
            json={"folder": "Sent"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        email_config: EmailIngestConfig,
        test_user: User,
    ):
        response = await client.patch(
            f"/api/v1/email-ingest/config/{email_config.id}",
            headers=auth_headers,
            json={"folder": "RFP-Inbox"},
        )
        assert response.status_code == 200
        assert response.json()["folder"] == "RFP-Inbox"

    @pytest.mark.asyncio
    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.patch(
            "/api/v1/email-ingest/config/99999",
            headers=auth_headers,
            json={"folder": "Nope"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_idor(
        self,
        client: AsyncClient,
        email_config: EmailIngestConfig,
        db_session: AsyncSession,
    ):
        other = User(
            email="other2@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.patch(
            f"/api/v1/email-ingest/config/{email_config.id}",
            headers=headers,
            json={"folder": "Hacked"},
        )
        assert response.status_code == 404


class TestDeleteConfig:
    """Tests for DELETE /api/v1/email-ingest/config/{id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/email-ingest/config/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        email_config: EmailIngestConfig,
        test_user: User,
    ):
        response = await client.delete(
            f"/api/v1/email-ingest/config/{email_config.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Config deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.delete("/api/v1/email-ingest/config/99999", headers=auth_headers)
        assert response.status_code == 404


class TestTestConnection:
    """Tests for POST /api/v1/email-ingest/config/{id}/test."""

    @pytest.mark.asyncio
    async def test_test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/email-ingest/config/1/test")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_test_not_found(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.post("/api/v1/email-ingest/config/99999/test", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_test_connection_fails_gracefully(
        self,
        client: AsyncClient,
        auth_headers: dict,
        email_config: EmailIngestConfig,
        test_user: User,
    ):
        """Test connection to a fake IMAP server should fail with 400 or error."""
        response = await client.post(
            f"/api/v1/email-ingest/config/{email_config.id}/test",
            headers=auth_headers,
        )
        # Expect failure since the IMAP server is fake
        assert response.status_code in (400, 500, 502)


class TestListHistory:
    """Tests for GET /api/v1/email-ingest/history."""

    @pytest.mark.asyncio
    async def test_history_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/email-ingest/history")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_history_empty(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/email-ingest/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_history_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        email_config: EmailIngestConfig,
        test_user: User,
        db_session: AsyncSession,
    ):
        email = IngestedEmail(
            config_id=email_config.id,
            message_id="<test@example.com>",
            subject="RFP Opportunity",
            sender="agency@gov.com",
        )
        db_session.add(email)
        await db_session.commit()

        response = await client.get("/api/v1/email-ingest/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["subject"] == "RFP Opportunity"


class TestReprocessEmail:
    """Tests for POST /api/v1/email-ingest/process/{id}."""

    @pytest.mark.asyncio
    async def test_reprocess_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/email-ingest/process/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reprocess_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        email_config: EmailIngestConfig,
        test_user: User,
        db_session: AsyncSession,
    ):
        email = IngestedEmail(
            config_id=email_config.id,
            message_id="<test2@example.com>",
            subject="Reprocess Me",
            sender="agency@gov.com",
            processing_status=EmailProcessingStatus.ERROR,
            error_message="Previous failure",
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        response = await client.post(
            f"/api/v1/email-ingest/process/{email.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["processing_status"] == "pending"
        assert data["error_message"] is None

    @pytest.mark.asyncio
    async def test_reprocess_not_found(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post("/api/v1/email-ingest/process/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reprocess_idor(
        self,
        client: AsyncClient,
        email_config: EmailIngestConfig,
        db_session: AsyncSession,
    ):
        email = IngestedEmail(
            config_id=email_config.id,
            message_id="<idor@example.com>",
            subject="IDOR test",
            sender="agency@gov.com",
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        other = User(
            email="other3@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        tokens = create_token_pair(other.id, other.email, other.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.post(f"/api/v1/email-ingest/process/{email.id}", headers=headers)
        assert response.status_code == 403


class TestSyncNow:
    """Tests for POST /api/v1/email-ingest/sync-now."""

    @pytest.mark.asyncio
    async def test_sync_now_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/email-ingest/sync-now",
            json={"run_poll": False, "run_process": False},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_now_no_configs(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        response = await client.post(
            "/api/v1/email-ingest/sync-now",
            headers=auth_headers,
            json={"run_poll": False, "run_process": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["configs_checked"] == 0
