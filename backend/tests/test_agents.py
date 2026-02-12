"""Integration tests for autonomous agent endpoints."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlmodel import select

from app.models.award import AwardRecord
from app.models.budget_intel import BudgetIntelligence
from app.models.capture import CaptureCompetitor
from app.models.contact import OpportunityContact
from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP


class TestAutonomousAgents:
    @pytest.mark.asyncio
    async def test_catalog_and_research_agent(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        test_user,
        db_session,
    ):
        db_session.add(
            OpportunityContact(
                user_id=test_user.id,
                rfp_id=test_rfp.id,
                name="Jamie Contracting Officer",
                agency=test_rfp.agency,
                role="CO",
                email="jamie@example.gov",
            )
        )
        db_session.add(
            AwardRecord(
                user_id=test_user.id,
                rfp_id=test_rfp.id,
                agency=test_rfp.agency,
                awardee_name="PrimeGov LLC",
                award_amount=4_500_000,
                award_date=datetime.utcnow(),
                naics_code=test_rfp.naics_code,
            )
        )
        db_session.add(
            BudgetIntelligence(
                user_id=test_user.id,
                rfp_id=test_rfp.id,
                title=f"{test_rfp.agency} FY26 Mission IT Budget",
                fiscal_year=2026,
                amount=12_000_000,
            )
        )
        await db_session.commit()

        catalog = await client.get("/api/v1/agents/catalog", headers=auth_headers)
        assert catalog.status_code == 200
        ids = {item["id"] for item in catalog.json()}
        assert {"research", "capture_planning", "proposal_prep", "competitive_intel"}.issubset(ids)

        response = await client.post(f"/api/v1/agents/research/{test_rfp.id}", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["agent"] == "research"
        assert payload["rfp_id"] == test_rfp.id
        assert payload["artifacts"]["top_contact_names"][0] == "Jamie Contracting Officer"

    @pytest.mark.asyncio
    async def test_capture_planning_and_proposal_prep_agents(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_rfp: RFP,
        db_session,
    ):
        capture_response = await client.post(
            f"/api/v1/agents/capture-planning/{test_rfp.id}",
            headers=auth_headers,
        )
        assert capture_response.status_code == 200
        capture_payload = capture_response.json()
        assert capture_payload["agent"] == "capture_planning"
        assert capture_payload["artifacts"]["capture_plan_id"] is not None

        prep_response = await client.post(
            f"/api/v1/agents/proposal-prep/{test_rfp.id}",
            headers=auth_headers,
        )
        assert prep_response.status_code == 200
        prep_payload = prep_response.json()
        proposal_id = prep_payload["artifacts"]["proposal_id"]
        assert prep_payload["artifacts"]["section_count"] >= 1

        proposal = await db_session.get(Proposal, proposal_id)
        assert proposal is not None
        assert proposal.total_sections >= 1

        sections_result = await db_session.execute(
            select(ProposalSection).where(ProposalSection.proposal_id == proposal_id)
        )
        sections = sections_result.scalars().all()
        assert len(sections) >= 1

    @pytest.mark.asyncio
    async def test_competitive_intel_agent(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        test_rfp: RFP,
        db_session,
    ):
        db_session.add(
            CaptureCompetitor(
                user_id=test_user.id,
                rfp_id=test_rfp.id,
                name="Incumbent Systems",
                incumbent=True,
                strengths="Past agency wins",
            )
        )
        db_session.add(
            AwardRecord(
                user_id=test_user.id,
                agency=test_rfp.agency,
                awardee_name="Incumbent Systems",
                award_amount=9_250_000,
                award_date=datetime.utcnow(),
                naics_code=test_rfp.naics_code,
            )
        )
        await db_session.commit()

        response = await client.post(
            f"/api/v1/agents/competitive-intel/{test_rfp.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["agent"] == "competitive_intel"
        assert "Incumbent Systems" in payload["artifacts"]["competitors"]
        assert payload["artifacts"]["award_patterns"]
