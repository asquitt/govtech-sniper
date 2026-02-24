"""Unit tests for webhook_service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.webhook import (
    WebhookDeliveryStatus,
    WebhookSubscription,
)
from app.services.auth_service import hash_password
from app.services.webhook_service import dispatch_webhook_event


@pytest_asyncio.fixture
async def webhook_user(db_session: AsyncSession) -> User:
    user = User(
        email="webhook@example.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Webhook User",
        company_name="WH Co",
        tier="professional",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def active_subscription(db_session: AsyncSession, webhook_user: User) -> WebhookSubscription:
    sub = WebhookSubscription(
        user_id=webhook_user.id,
        name="Test Webhook",
        target_url="https://example.com/webhook",
        event_types=["rfp.created", "proposal.updated"],
        is_active=True,
        secret="webhook-secret-123",
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)
    return sub


@pytest_asyncio.fixture
async def catch_all_subscription(
    db_session: AsyncSession, webhook_user: User
) -> WebhookSubscription:
    sub = WebhookSubscription(
        user_id=webhook_user.id,
        name="Catch All",
        target_url="https://example.com/all",
        event_types=None,  # No filter = catch all
        is_active=True,
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# No subscriptions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_no_subscriptions(db_session: AsyncSession, webhook_user: User):
    deliveries = await dispatch_webhook_event(
        db_session,
        user_id=webhook_user.id,
        event_type="rfp.created",
        payload={"rfp_id": 1},
    )
    assert deliveries == []


# ---------------------------------------------------------------------------
# Event type filtering
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_skips_non_matching_event(
    db_session: AsyncSession,
    webhook_user: User,
    active_subscription: WebhookSubscription,
):
    deliveries = await dispatch_webhook_event(
        db_session,
        user_id=webhook_user.id,
        event_type="unrelated.event",
        payload={"data": "test"},
    )
    assert deliveries == []


# ---------------------------------------------------------------------------
# Delivery disabled (skipped)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_skips_when_delivery_disabled(
    db_session: AsyncSession,
    webhook_user: User,
    active_subscription: WebhookSubscription,
):
    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.webhook_delivery_enabled = False

        deliveries = await dispatch_webhook_event(
            db_session,
            user_id=webhook_user.id,
            event_type="rfp.created",
            payload={"rfp_id": 1},
        )
        assert len(deliveries) == 1
        assert deliveries[0].status == WebhookDeliveryStatus.SKIPPED


# ---------------------------------------------------------------------------
# Successful delivery
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_successful_delivery(
    db_session: AsyncSession,
    webhook_user: User,
    active_subscription: WebhookSubscription,
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"

    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.webhook_delivery_enabled = True

        with patch("app.services.webhook_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            deliveries = await dispatch_webhook_event(
                db_session,
                user_id=webhook_user.id,
                event_type="rfp.created",
                payload={"rfp_id": 42},
            )
            assert len(deliveries) == 1
            assert deliveries[0].status == WebhookDeliveryStatus.DELIVERED
            assert deliveries[0].response_code == 200
            assert deliveries[0].delivered_at is not None


# ---------------------------------------------------------------------------
# Failed delivery (HTTP error)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_failed_delivery_http_error(
    db_session: AsyncSession,
    webhook_user: User,
    active_subscription: WebhookSubscription,
):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.webhook_delivery_enabled = True

        with patch("app.services.webhook_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            deliveries = await dispatch_webhook_event(
                db_session,
                user_id=webhook_user.id,
                event_type="rfp.created",
                payload={"rfp_id": 1},
            )
            assert len(deliveries) == 1
            assert deliveries[0].status == WebhookDeliveryStatus.FAILED
            assert deliveries[0].response_code == 500


# ---------------------------------------------------------------------------
# Failed delivery (network exception)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_failed_delivery_exception(
    db_session: AsyncSession,
    webhook_user: User,
    active_subscription: WebhookSubscription,
):
    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.webhook_delivery_enabled = True

        with patch("app.services.webhook_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = ConnectionError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            deliveries = await dispatch_webhook_event(
                db_session,
                user_id=webhook_user.id,
                event_type="rfp.created",
                payload={"rfp_id": 1},
            )
            assert len(deliveries) == 1
            assert deliveries[0].status == WebhookDeliveryStatus.FAILED
            assert "Connection refused" in deliveries[0].response_body


# ---------------------------------------------------------------------------
# Catch-all subscription (no event_types filter)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_catch_all_subscription(
    db_session: AsyncSession,
    webhook_user: User,
    catch_all_subscription: WebhookSubscription,
):
    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.webhook_delivery_enabled = False

        deliveries = await dispatch_webhook_event(
            db_session,
            user_id=webhook_user.id,
            event_type="any.event.at.all",
            payload={"data": "test"},
        )
        assert len(deliveries) == 1
        assert deliveries[0].status == WebhookDeliveryStatus.SKIPPED


# ---------------------------------------------------------------------------
# Secret header
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_includes_secret_header(
    db_session: AsyncSession,
    webhook_user: User,
    active_subscription: WebhookSubscription,
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"

    with patch("app.services.webhook_service.settings") as mock_settings:
        mock_settings.webhook_delivery_enabled = True

        with patch("app.services.webhook_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            await dispatch_webhook_event(
                db_session,
                user_id=webhook_user.id,
                event_type="rfp.created",
                payload={"rfp_id": 1},
            )
            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert headers.get("X-Webhook-Secret") == "webhook-secret-123"
            assert headers.get("X-Webhook-Event") == "rfp.created"


# ---------------------------------------------------------------------------
# Inactive subscription ignored
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_inactive_subscription_ignored(db_session: AsyncSession, webhook_user: User):
    sub = WebhookSubscription(
        user_id=webhook_user.id,
        name="Inactive",
        target_url="https://example.com/inactive",
        is_active=False,
    )
    db_session.add(sub)
    await db_session.commit()

    deliveries = await dispatch_webhook_event(
        db_session,
        user_id=webhook_user.id,
        event_type="rfp.created",
        payload={"rfp_id": 1},
    )
    assert deliveries == []
