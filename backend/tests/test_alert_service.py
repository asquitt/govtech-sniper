"""
Integration tests for alert_service.py
=======================================
Tests the get_alert_counts helper against a real DB session,
verifying aggregation of sync failures, webhook failures, and auth failures.
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.integration import (
    IntegrationConfig,
    IntegrationProvider,
    IntegrationSyncRun,
    IntegrationSyncStatus,
)
from app.models.user import User
from app.models.webhook import (
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookSubscription,
)
from app.services.alert_service import get_alert_counts
from app.services.auth_service import hash_password


@pytest_asyncio.fixture
async def alert_user(db_session: AsyncSession) -> User:
    user = User(
        email="alerts@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Alert Tester",
        company_name="Alert Co",
        tier="professional",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(
        email="other@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Other User",
        company_name="Other Co",
        tier="free",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# No Data
# =============================================================================


class TestAlertCountsEmpty:
    @pytest.mark.asyncio
    async def test_returns_zeros_with_no_data(self, db_session: AsyncSession, alert_user: User):
        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["sync_failures"] == 0
        assert counts["webhook_failures"] == 0
        assert counts["auth_failures"] == 0

    @pytest.mark.asyncio
    async def test_returns_zeros_with_no_user_filter(self, db_session: AsyncSession):
        counts = await get_alert_counts(db_session, user_id=None, days=30)
        assert counts["sync_failures"] == 0
        assert counts["webhook_failures"] == 0
        assert counts["auth_failures"] == 0


# =============================================================================
# Sync Failures
# =============================================================================


class TestSyncFailures:
    @pytest.mark.asyncio
    async def test_counts_recent_sync_failures(self, db_session: AsyncSession, alert_user: User):
        integration = IntegrationConfig(
            user_id=alert_user.id,
            provider=IntegrationProvider.SHAREPOINT,
            name="Test SharePoint",
        )
        db_session.add(integration)
        await db_session.flush()

        # Add 2 failed sync runs within window
        for _ in range(2):
            run = IntegrationSyncRun(
                integration_id=integration.id,
                provider=IntegrationProvider.SHAREPOINT,
                status=IntegrationSyncStatus.FAILED,
                started_at=datetime.utcnow() - timedelta(days=1),
            )
            db_session.add(run)

        # Add 1 successful run (should not count)
        success_run = IntegrationSyncRun(
            integration_id=integration.id,
            provider=IntegrationProvider.SHAREPOINT,
            status=IntegrationSyncStatus.SUCCESS,
            started_at=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(success_run)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["sync_failures"] == 2

    @pytest.mark.asyncio
    async def test_excludes_old_sync_failures(self, db_session: AsyncSession, alert_user: User):
        integration = IntegrationConfig(
            user_id=alert_user.id,
            provider=IntegrationProvider.SALESFORCE,
            name="Old CRM",
        )
        db_session.add(integration)
        await db_session.flush()

        # Run from 60 days ago - outside 30-day window
        old_run = IntegrationSyncRun(
            integration_id=integration.id,
            provider=IntegrationProvider.SALESFORCE,
            status=IntegrationSyncStatus.FAILED,
            started_at=datetime.utcnow() - timedelta(days=60),
        )
        db_session.add(old_run)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["sync_failures"] == 0

    @pytest.mark.asyncio
    async def test_sync_failures_scoped_to_user(
        self, db_session: AsyncSession, alert_user: User, other_user: User
    ):
        # Integration for other_user
        integration = IntegrationConfig(
            user_id=other_user.id,
            provider=IntegrationProvider.OKTA,
            name="Other SSO",
        )
        db_session.add(integration)
        await db_session.flush()

        run = IntegrationSyncRun(
            integration_id=integration.id,
            provider=IntegrationProvider.OKTA,
            status=IntegrationSyncStatus.FAILED,
            started_at=datetime.utcnow(),
        )
        db_session.add(run)
        await db_session.commit()

        # alert_user should see 0
        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["sync_failures"] == 0


# =============================================================================
# Webhook Failures
# =============================================================================


class TestWebhookFailures:
    @pytest.mark.asyncio
    async def test_counts_recent_webhook_failures(self, db_session: AsyncSession, alert_user: User):
        sub = WebhookSubscription(
            user_id=alert_user.id,
            name="Fail Webhook",
            target_url="https://example.com/fail",
            is_active=True,
        )
        db_session.add(sub)
        await db_session.flush()

        for _ in range(3):
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type="rfp.created",
                payload={},
                status=WebhookDeliveryStatus.FAILED,
                created_at=datetime.utcnow() - timedelta(days=2),
            )
            db_session.add(delivery)

        # 1 delivered (should not count)
        ok_delivery = WebhookDelivery(
            subscription_id=sub.id,
            event_type="rfp.created",
            payload={},
            status=WebhookDeliveryStatus.DELIVERED,
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(ok_delivery)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["webhook_failures"] == 3

    @pytest.mark.asyncio
    async def test_excludes_old_webhook_failures(self, db_session: AsyncSession, alert_user: User):
        sub = WebhookSubscription(
            user_id=alert_user.id,
            name="Old Webhook",
            target_url="https://example.com/old",
            is_active=True,
        )
        db_session.add(sub)
        await db_session.flush()

        old_delivery = WebhookDelivery(
            subscription_id=sub.id,
            event_type="rfp.created",
            payload={},
            status=WebhookDeliveryStatus.FAILED,
            created_at=datetime.utcnow() - timedelta(days=60),
        )
        db_session.add(old_delivery)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["webhook_failures"] == 0

    @pytest.mark.asyncio
    async def test_webhook_failures_scoped_to_user(
        self, db_session: AsyncSession, alert_user: User, other_user: User
    ):
        sub = WebhookSubscription(
            user_id=other_user.id,
            name="Other Webhook",
            target_url="https://example.com/other",
            is_active=True,
        )
        db_session.add(sub)
        await db_session.flush()

        delivery = WebhookDelivery(
            subscription_id=sub.id,
            event_type="test",
            payload={},
            status=WebhookDeliveryStatus.FAILED,
            created_at=datetime.utcnow(),
        )
        db_session.add(delivery)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["webhook_failures"] == 0


# =============================================================================
# Auth Failures
# =============================================================================


class TestAuthFailures:
    @pytest.mark.asyncio
    async def test_counts_recent_auth_failures(self, db_session: AsyncSession, alert_user: User):
        for _ in range(4):
            event = AuditEvent(
                user_id=alert_user.id,
                entity_type="user",
                entity_id=alert_user.id,
                action="user.login_failed",
                created_at=datetime.utcnow() - timedelta(hours=6),
            )
            db_session.add(event)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=7)
        assert counts["auth_failures"] == 4

    @pytest.mark.asyncio
    async def test_excludes_old_auth_failures(self, db_session: AsyncSession, alert_user: User):
        event = AuditEvent(
            user_id=alert_user.id,
            entity_type="user",
            entity_id=alert_user.id,
            action="user.login_failed",
            created_at=datetime.utcnow() - timedelta(days=45),
        )
        db_session.add(event)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["auth_failures"] == 0

    @pytest.mark.asyncio
    async def test_excludes_non_login_failed_events(
        self, db_session: AsyncSession, alert_user: User
    ):
        # A successful login should not count
        event = AuditEvent(
            user_id=alert_user.id,
            entity_type="user",
            entity_id=alert_user.id,
            action="user.login",
            created_at=datetime.utcnow(),
        )
        db_session.add(event)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["auth_failures"] == 0

    @pytest.mark.asyncio
    async def test_auth_failures_scoped_to_user(
        self, db_session: AsyncSession, alert_user: User, other_user: User
    ):
        event = AuditEvent(
            user_id=other_user.id,
            entity_type="user",
            entity_id=other_user.id,
            action="user.login_failed",
            created_at=datetime.utcnow(),
        )
        db_session.add(event)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["auth_failures"] == 0


# =============================================================================
# Combined / No User Filter
# =============================================================================


class TestAlertCountsCombined:
    @pytest.mark.asyncio
    async def test_all_counts_together(self, db_session: AsyncSession, alert_user: User):
        # 1 sync failure
        integration = IntegrationConfig(
            user_id=alert_user.id,
            provider=IntegrationProvider.WEBHOOK,
            name="WH Int",
        )
        db_session.add(integration)
        await db_session.flush()

        sync_run = IntegrationSyncRun(
            integration_id=integration.id,
            provider=IntegrationProvider.WEBHOOK,
            status=IntegrationSyncStatus.FAILED,
            started_at=datetime.utcnow(),
        )
        db_session.add(sync_run)

        # 2 webhook failures
        sub = WebhookSubscription(
            user_id=alert_user.id,
            name="WH Sub",
            target_url="https://example.com",
            is_active=True,
        )
        db_session.add(sub)
        await db_session.flush()

        for _ in range(2):
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type="test",
                payload={},
                status=WebhookDeliveryStatus.FAILED,
                created_at=datetime.utcnow(),
            )
            db_session.add(delivery)

        # 3 auth failures
        for _ in range(3):
            event = AuditEvent(
                user_id=alert_user.id,
                entity_type="user",
                entity_id=alert_user.id,
                action="user.login_failed",
                created_at=datetime.utcnow(),
            )
            db_session.add(event)

        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=alert_user.id, days=30)
        assert counts["sync_failures"] == 1
        assert counts["webhook_failures"] == 2
        assert counts["auth_failures"] == 3

    @pytest.mark.asyncio
    async def test_no_user_filter_counts_all(
        self, db_session: AsyncSession, alert_user: User, other_user: User
    ):
        # Auth failure for each user
        for u in [alert_user, other_user]:
            event = AuditEvent(
                user_id=u.id,
                entity_type="user",
                entity_id=u.id,
                action="user.login_failed",
                created_at=datetime.utcnow(),
            )
            db_session.add(event)
        await db_session.commit()

        counts = await get_alert_counts(db_session, user_id=None, days=30)
        assert counts["auth_failures"] == 2

    @pytest.mark.asyncio
    async def test_days_parameter_controls_window(self, db_session: AsyncSession, alert_user: User):
        # Event 5 days ago
        event = AuditEvent(
            user_id=alert_user.id,
            entity_type="user",
            entity_id=alert_user.id,
            action="user.login_failed",
            created_at=datetime.utcnow() - timedelta(days=5),
        )
        db_session.add(event)
        await db_session.commit()

        # 3-day window should miss it
        counts_3 = await get_alert_counts(db_session, user_id=alert_user.id, days=3)
        assert counts_3["auth_failures"] == 0

        # 7-day window should include it
        counts_7 = await get_alert_counts(db_session, user_id=alert_user.id, days=7)
        assert counts_7["auth_failures"] == 1
