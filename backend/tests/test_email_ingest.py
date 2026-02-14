from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.collaboration import SharedWorkspace
from app.models.email_ingest import EmailIngestConfig, EmailProcessingStatus, IngestedEmail
from app.models.inbox import InboxMessage
from app.models.rfp import RFP
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password
from app.services.email_ingest_service import EmailIngestService


def _auth_headers(user: User) -> dict[str, str]:
    tokens = create_token_pair(user.id, user.email, str(user.tier))
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest.mark.asyncio
async def test_sync_now_creates_rfp_and_forwards_to_workspace_inbox(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = SharedWorkspace(
        owner_id=test_user.id, name="Capture Ops", description="Email routed"
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    headers = _auth_headers(test_user)
    config_response = await client.post(
        "/api/v1/email-ingest/config",
        headers=headers,
        json={
            "imap_server": "imap.example.com",
            "imap_port": 993,
            "email_address": "capture@example.com",
            "password": "secret",
            "folder": "INBOX",
            "workspace_id": workspace.id,
            "auto_create_rfps": True,
            "min_rfp_confidence": 0.35,
        },
    )
    assert config_response.status_code == 200
    config_id = config_response.json()["id"]

    async def fake_connect_and_fetch(self, folder="INBOX", limit=50):
        return [
            {
                "message_id": "<msg-rfp-001@example.com>",
                "subject": "FWD: RFP W91ABC-26-R-0001 Cybersecurity Operations",
                "sender": "Contracting Officer <ko@gsa.gov>",
                "date": "Fri, 14 Feb 2026 14:00:00 +0000",
                "body_text": (
                    "Solicitation Number: W91ABC-26-R-0001\n"
                    "Request for Proposal for SOC operations.\n"
                    "NAICS 541512. Proposal due March 20."
                ),
                "attachment_count": 1,
                "attachment_names": ["rfp-package.pdf"],
                "attachment_text": "Statement of Work and Period of Performance details.",
            }
        ]

    monkeypatch.setattr(EmailIngestService, "connect_and_fetch", fake_connect_and_fetch)

    sync_response = await client.post(
        "/api/v1/email-ingest/sync-now",
        headers=headers,
        json={"run_poll": True, "run_process": True},
    )
    assert sync_response.status_code == 200
    payload = sync_response.json()
    assert payload["fetched"] == 1
    assert payload["processed"] == 1
    assert payload["created_rfps"] == 1
    assert payload["inbox_forwarded"] == 1

    ingested_email = (
        await db_session.execute(select(IngestedEmail).where(IngestedEmail.config_id == config_id))
    ).scalar_one()
    assert ingested_email.processing_status == EmailProcessingStatus.PROCESSED
    assert ingested_email.attachment_count == 1
    assert ingested_email.attachment_names == ["rfp-package.pdf"]
    assert ingested_email.classification_confidence is not None
    assert ingested_email.created_rfp_id is not None
    assert ingested_email.processed_at is not None

    rfp = (
        await db_session.execute(select(RFP).where(RFP.id == ingested_email.created_rfp_id))
    ).scalar_one()
    assert rfp.solicitation_number == "W91ABC-26-R-0001"
    assert rfp.source_type == "email"
    assert rfp.user_id == test_user.id

    inbox_messages = (
        (
            await db_session.execute(
                select(InboxMessage).where(InboxMessage.workspace_id == workspace.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(inbox_messages) == 1
    assert "Email ingest created RFP" in inbox_messages[0].subject


@pytest.mark.asyncio
async def test_sync_now_ignores_low_confidence_email(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    headers = _auth_headers(test_user)
    config_response = await client.post(
        "/api/v1/email-ingest/config",
        headers=headers,
        json={
            "imap_server": "imap.example.com",
            "imap_port": 993,
            "email_address": "capture@example.com",
            "password": "secret",
            "folder": "INBOX",
            "auto_create_rfps": True,
            "min_rfp_confidence": 0.9,
        },
    )
    assert config_response.status_code == 200

    async def fake_connect_and_fetch(self, folder="INBOX", limit=50):
        return [
            {
                "message_id": "<msg-generic-001@example.com>",
                "subject": "Weekly Team Lunch",
                "sender": "Teammate <teammate@example.com>",
                "date": "Fri, 14 Feb 2026 15:00:00 +0000",
                "body_text": "Lets pick a lunch location for next week.",
                "attachment_count": 0,
                "attachment_names": [],
                "attachment_text": "",
            }
        ]

    monkeypatch.setattr(EmailIngestService, "connect_and_fetch", fake_connect_and_fetch)

    sync_response = await client.post(
        "/api/v1/email-ingest/sync-now",
        headers=headers,
        json={"run_poll": True, "run_process": True},
    )
    assert sync_response.status_code == 200
    payload = sync_response.json()
    assert payload["created_rfps"] == 0
    assert payload["processed"] == 1

    ingested_email = (await db_session.execute(select(IngestedEmail))).scalar_one()
    assert ingested_email.processing_status == EmailProcessingStatus.IGNORED
    assert ingested_email.created_rfp_id is None
    assert ingested_email.classification_confidence is not None
    assert ingested_email.error_message is not None

    rfps = (await db_session.execute(select(RFP))).scalars().all()
    assert rfps == []


@pytest.mark.asyncio
async def test_create_config_rejects_unscoped_workspace(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    external_owner = User(
        email="external-owner@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="External Owner",
        company_name="External",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(external_owner)
    await db_session.commit()
    await db_session.refresh(external_owner)

    external_workspace = SharedWorkspace(
        owner_id=external_owner.id,
        name="External Workspace",
        description="Not shared",
        created_at=datetime.utcnow(),
    )
    db_session.add(external_workspace)
    await db_session.commit()
    await db_session.refresh(external_workspace)

    response = await client.post(
        "/api/v1/email-ingest/config",
        headers=_auth_headers(test_user),
        json={
            "imap_server": "imap.example.com",
            "imap_port": 993,
            "email_address": "capture@example.com",
            "password": "secret",
            "folder": "INBOX",
            "workspace_id": external_workspace.id,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized for workspace"


@pytest.mark.asyncio
async def test_sync_now_allows_same_message_id_across_different_configs(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    second_user = User(
        email="email-ingest-second-user@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Second Email User",
        company_name="Second Company",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(second_user)
    await db_session.commit()
    await db_session.refresh(second_user)

    first_headers = _auth_headers(test_user)
    second_headers = _auth_headers(second_user)

    first_config_response = await client.post(
        "/api/v1/email-ingest/config",
        headers=first_headers,
        json={
            "imap_server": "imap.example.com",
            "imap_port": 993,
            "email_address": "capture+first@example.com",
            "password": "secret",
            "folder": "INBOX",
        },
    )
    assert first_config_response.status_code == 200
    first_config_id = first_config_response.json()["id"]

    second_config_response = await client.post(
        "/api/v1/email-ingest/config",
        headers=second_headers,
        json={
            "imap_server": "imap.example.com",
            "imap_port": 993,
            "email_address": "capture+second@example.com",
            "password": "secret",
            "folder": "INBOX",
        },
    )
    assert second_config_response.status_code == 200
    second_config_id = second_config_response.json()["id"]

    async def fake_connect_and_fetch(self, folder="INBOX", limit=50):
        return [
            {
                "message_id": "<shared-msg-id@example.com>",
                "subject": "RFP Shared Message Id Validation",
                "sender": "Contracting Officer <ko@gsa.gov>",
                "date": "Fri, 14 Feb 2026 16:00:00 +0000",
                "body_text": (
                    "Solicitation Number: SHARED-MSG-001\n"
                    "Request for Proposal for cross-tenant duplicate-scoping validation."
                ),
                "attachment_count": 0,
                "attachment_names": [],
                "attachment_text": "",
            }
        ]

    monkeypatch.setattr(EmailIngestService, "connect_and_fetch", fake_connect_and_fetch)

    first_sync_response = await client.post(
        "/api/v1/email-ingest/sync-now",
        headers=first_headers,
        json={"run_poll": True, "run_process": False},
    )
    assert first_sync_response.status_code == 200
    first_payload = first_sync_response.json()
    assert first_payload["fetched"] == 1
    assert first_payload["duplicates"] == 0
    assert first_payload["poll_errors"] == 0

    second_sync_response = await client.post(
        "/api/v1/email-ingest/sync-now",
        headers=second_headers,
        json={"run_poll": True, "run_process": False},
    )
    assert second_sync_response.status_code == 200
    second_payload = second_sync_response.json()
    assert second_payload["fetched"] == 1
    assert second_payload["duplicates"] == 0
    assert second_payload["poll_errors"] == 0

    ingested_rows = (
        (
            await db_session.execute(
                select(IngestedEmail).where(
                    IngestedEmail.message_id == "<shared-msg-id@example.com>"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(ingested_rows) == 2
    assert {item.config_id for item in ingested_rows} == {first_config_id, second_config_id}

    configs = (
        (
            await db_session.execute(
                select(EmailIngestConfig).where(
                    EmailIngestConfig.id.in_([first_config_id, second_config_id])
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(configs) == 2
