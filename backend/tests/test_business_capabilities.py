"""
Integration coverage for business capability surfaces that were previously partial.
"""

from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CapturePlan, CaptureStage
from app.models.contract import ContractAward, ContractStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.rfp import RFP
from app.models.user import User


class TestBusinessCapabilities:
    @pytest.mark.asyncio
    async def test_revenue_endpoints_return_aggregated_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        rfp = RFP(
            user_id=test_user.id,
            title="Revenue Pipeline RFP",
            solicitation_number="REV-001",
            notice_id="rev-notice-001",
            agency="Department of Revenue",
            naics_code="541511",
            rfp_type="solicitation",
            response_deadline=datetime.utcnow() + timedelta(days=60),
            estimated_value=2_000_000,
            status="new",
            posted_date=datetime.utcnow(),
        )
        db_session.add(rfp)
        await db_session.flush()

        capture_plan = CapturePlan(
            rfp_id=rfp.id,
            owner_id=test_user.id,
            stage=CaptureStage.PURSUIT,
            win_probability=55,
        )
        db_session.add(capture_plan)

        contract = ContractAward(
            user_id=test_user.id,
            contract_number="REV-CON-001",
            title="Won Revenue Contract",
            agency="Department of Revenue",
            value=900_000,
            start_date=date.today(),
            status=ContractStatus.ACTIVE,
        )
        db_session.add(contract)
        await db_session.commit()

        summary = await client.get("/api/v1/revenue/pipeline-summary", headers=auth_headers)
        assert summary.status_code == 200
        summary_payload = summary.json()
        assert summary_payload["total_opportunities"] == 1
        assert summary_payload["total_weighted"] > 0
        assert summary_payload["won_value"] == 900000.0

        timeline = await client.get(
            "/api/v1/revenue/timeline",
            headers=auth_headers,
            params={"granularity": "quarterly"},
        )
        assert timeline.status_code == 200
        timeline_payload = timeline.json()
        assert timeline_payload["granularity"] == "quarterly"
        assert len(timeline_payload["points"]) >= 1

        by_agency = await client.get("/api/v1/revenue/by-agency", headers=auth_headers)
        assert by_agency.status_code == 200
        agencies = by_agency.json()["agencies"]
        assert any(item["agency"] == "Department of Revenue" for item in agencies)

    @pytest.mark.asyncio
    async def test_forecasts_matching_and_alert_dismissal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        rfp = RFP(
            user_id=test_user.id,
            title="Cloud Modernization Services",
            solicitation_number="FOR-001",
            notice_id="for-notice-001",
            agency="GSA",
            naics_code="541512",
            rfp_type="solicitation",
            estimated_value=1_500_000,
            status="new",
            posted_date=datetime.utcnow(),
        )
        db_session.add(rfp)
        await db_session.commit()

        create_forecast = await client.post(
            "/api/v1/forecasts",
            headers=auth_headers,
            json={
                "title": "Cloud Modernization Platform",
                "agency": "GSA",
                "naics_code": "541512",
                "estimated_value": 1_400_000,
            },
        )
        assert create_forecast.status_code == 200

        run_matching = await client.post("/api/v1/forecasts/match", headers=auth_headers)
        assert run_matching.status_code == 200
        assert run_matching.json()["new_alerts"] >= 1

        list_alerts = await client.get("/api/v1/forecasts/alerts", headers=auth_headers)
        assert list_alerts.status_code == 200
        alerts = list_alerts.json()
        assert len(alerts) >= 1

        dismiss = await client.patch(
            f"/api/v1/forecasts/alerts/{alerts[0]['id']}",
            headers=auth_headers,
        )
        assert dismiss.status_code == 200

        refreshed_alerts = await client.get("/api/v1/forecasts/alerts", headers=auth_headers)
        assert refreshed_alerts.status_code == 200
        assert all(alert["id"] != alerts[0]["id"] for alert in refreshed_alerts.json())

    @pytest.mark.asyncio
    async def test_events_crud_and_upcoming_filters(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        event_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
        create_event = await client.post(
            "/api/v1/events",
            headers=auth_headers,
            json={
                "title": "Industry Day",
                "date": event_date,
                "agency": "DHS",
                "event_type": "industry_day",
                "location": "Washington, DC",
            },
        )
        assert create_event.status_code == 200
        event = create_event.json()

        upcoming = await client.get("/api/v1/events/upcoming", headers=auth_headers)
        assert upcoming.status_code == 200
        assert any(item["id"] == event["id"] for item in upcoming.json())

        delete_event = await client.delete(
            f"/api/v1/events/{event['id']}",
            headers=auth_headers,
        )
        assert delete_event.status_code == 200

        all_events = await client.get("/api/v1/events", headers=auth_headers)
        assert all_events.status_code == 200
        assert all(item["id"] != event["id"] for item in all_events.json())

    @pytest.mark.asyncio
    async def test_signals_feed_mark_read_and_subscription_lifecycle(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        create_signal = await client.post(
            "/api/v1/signals",
            headers=auth_headers,
            json={
                "title": "Agency budget increase",
                "signal_type": "budget",
                "agency": "DoD",
                "content": "Budget increased for cybersecurity programs.",
                "relevance_score": 88,
            },
        )
        assert create_signal.status_code == 200
        signal_id = create_signal.json()["id"]

        feed = await client.get(
            "/api/v1/signals/feed",
            headers=auth_headers,
            params={"signal_type": "budget"},
        )
        assert feed.status_code == 200
        assert feed.json()["total"] >= 1

        mark_read = await client.patch(
            f"/api/v1/signals/{signal_id}/read",
            headers=auth_headers,
        )
        assert mark_read.status_code == 200

        signal_list = await client.get("/api/v1/signals", headers=auth_headers)
        assert signal_list.status_code == 200
        match = next(item for item in signal_list.json() if item["id"] == signal_id)
        assert match["is_read"] is True

        upsert_subscription = await client.post(
            "/api/v1/signals/subscription",
            headers=auth_headers,
            json={
                "agencies": ["DoD"],
                "naics_codes": ["541512"],
                "keywords": ["cybersecurity", "cloud"],
                "email_digest_enabled": True,
                "digest_frequency": "daily",
            },
        )
        assert upsert_subscription.status_code == 200
        assert upsert_subscription.json()["keywords"] == ["cybersecurity", "cloud"]

        subscription = await client.get("/api/v1/signals/subscription", headers=auth_headers)
        assert subscription.status_code == 200
        assert subscription.json()["agencies"] == ["DoD"]

    @pytest.mark.asyncio
    async def test_reports_generate_schedule_and_export(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        create_report = await client.post(
            "/api/v1/reports",
            headers=auth_headers,
            json={"name": "Pipeline Snapshot", "report_type": "pipeline"},
        )
        assert create_report.status_code == 200
        report_id = create_report.json()["id"]

        generate = await client.post(
            f"/api/v1/reports/{report_id}/generate",
            headers=auth_headers,
        )
        assert generate.status_code == 200
        generated = generate.json()
        assert generated["total_rows"] >= 1
        assert "columns" in generated

        schedule = await client.post(
            f"/api/v1/reports/{report_id}/schedule",
            headers=auth_headers,
            params={"frequency": "weekly"},
        )
        assert schedule.status_code == 200
        assert schedule.json()["schedule"] == "weekly"

        export = await client.post(
            f"/api/v1/reports/{report_id}/export",
            headers=auth_headers,
        )
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=" in export.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_intelligence_endpoints_and_debrief_contracts(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        won_rfp = RFP(
            user_id=test_user.id,
            title="Won Opportunity",
            solicitation_number="INT-WON-001",
            notice_id="int-won-notice-001",
            agency="VA",
            naics_code="541511",
            rfp_type="solicitation",
            estimated_value=500_000,
            response_deadline=datetime.utcnow() - timedelta(days=20),
            status="submitted",
            posted_date=datetime.utcnow() - timedelta(days=120),
        )
        active_rfp = RFP(
            user_id=test_user.id,
            title="Active Pipeline Opportunity",
            solicitation_number="INT-ACT-001",
            notice_id="int-act-notice-001",
            agency="VA",
            naics_code="541512",
            rfp_type="solicitation",
            estimated_value=1_200_000,
            response_deadline=datetime.utcnow() + timedelta(days=45),
            status="new",
            posted_date=datetime.utcnow() - timedelta(days=10),
        )
        db_session.add(won_rfp)
        db_session.add(active_rfp)
        await db_session.flush()

        won_capture = CapturePlan(
            rfp_id=won_rfp.id,
            owner_id=test_user.id,
            stage=CaptureStage.WON,
            win_probability=85,
        )
        active_capture = CapturePlan(
            rfp_id=active_rfp.id,
            owner_id=test_user.id,
            stage=CaptureStage.PURSUIT,
            win_probability=60,
        )
        proposal = Proposal(
            user_id=test_user.id,
            rfp_id=won_rfp.id,
            title="Submitted Intelligence Proposal",
            status=ProposalStatus.SUBMITTED,
            total_sections=6,
            completed_sections=6,
        )
        db_session.add(won_capture)
        db_session.add(active_capture)
        db_session.add(proposal)
        await db_session.commit()

        create_debrief = await client.post(
            "/api/v1/intelligence/debriefs",
            headers=auth_headers,
            params={
                "capture_plan_id": won_capture.id,
                "outcome": "won",
                "source": "internal_review",
            },
        )
        assert create_debrief.status_code == 200
        assert create_debrief.json()["status"] == "created"

        win_loss = await client.get("/api/v1/intelligence/win-loss", headers=auth_headers)
        assert win_loss.status_code == 200
        win_loss_payload = win_loss.json()
        assert "by_agency" in win_loss_payload
        assert len(win_loss_payload["debriefs"]) >= 1

        kpis = await client.get("/api/v1/intelligence/kpis", headers=auth_headers)
        assert kpis.status_code == 200
        kpi_payload = kpis.json()
        assert "active_pipeline" in kpi_payload
        assert "won_revenue" in kpi_payload

        forecast = await client.get(
            "/api/v1/intelligence/pipeline-forecast",
            headers=auth_headers,
            params={"granularity": "quarterly"},
        )
        assert forecast.status_code == 200
        forecast_payload = forecast.json()
        assert forecast_payload["granularity"] == "quarterly"
        assert len(forecast_payload["forecast"]) >= 1

        resources = await client.get(
            "/api/v1/intelligence/resource-allocation",
            headers=auth_headers,
        )
        assert resources.status_code == 200
        resources_payload = resources.json()
        assert "proposal_workload" in resources_payload
        assert "capture_workload" in resources_payload
