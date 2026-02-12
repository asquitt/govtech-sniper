"""Autonomous agent routes for research, capture, proposal prep, and intel workflows."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.database import get_session
from app.models.award import AwardRecord
from app.models.budget_intel import BudgetIntelligence
from app.models.capture import BidDecision, CaptureCompetitor, CapturePlan, CaptureStage
from app.models.contact import OpportunityContact
from app.models.proposal import Proposal, ProposalSection
from app.models.rfp import RFP, ComplianceMatrix
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/agents", tags=["Autonomous Agents"])


class AgentDescriptor(BaseModel):
    id: str
    name: str
    description: str


class AgentRunResponse(BaseModel):
    agent: str
    rfp_id: int
    summary: str
    actions_taken: list[str]
    artifacts: dict


CATALOG = [
    AgentDescriptor(
        id="research",
        name="Research Agent",
        description="Builds agency/incumbent/market context from contacts, awards, and budgets.",
    ),
    AgentDescriptor(
        id="capture_planning",
        name="Capture Planning Agent",
        description="Creates or updates a capture plan and seeds initial stage guidance.",
    ),
    AgentDescriptor(
        id="proposal_prep",
        name="Proposal Prep Agent",
        description="Sets up proposal workspace sections from compliance requirements.",
    ),
    AgentDescriptor(
        id="competitive_intel",
        name="Competitive Intel Agent",
        description="Summarizes competitors and prior award signals for the target opportunity.",
    ),
]


async def _get_owned_rfp(session: AsyncSession, user: UserAuth, rfp_id: int) -> RFP:
    result = await session.execute(select(RFP).where(RFP.id == rfp_id, RFP.user_id == user.id))
    rfp = result.scalar_one_or_none()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@router.get("/catalog", response_model=list[AgentDescriptor])
async def list_agents(
    current_user: UserAuth = Depends(get_current_user),
) -> list[AgentDescriptor]:
    return CATALOG


@router.post("/research/{rfp_id}", response_model=AgentRunResponse)
async def run_research_agent(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentRunResponse:
    rfp = await _get_owned_rfp(session, current_user, rfp_id)

    contacts_result = await session.execute(
        select(OpportunityContact)
        .where(OpportunityContact.user_id == current_user.id, OpportunityContact.rfp_id == rfp_id)
        .order_by(OpportunityContact.created_at.desc())
    )
    contacts = contacts_result.scalars().all()

    awards_result = await session.execute(
        select(AwardRecord)
        .where(AwardRecord.user_id == current_user.id)
        .where((AwardRecord.rfp_id == rfp_id) | (AwardRecord.agency == rfp.agency))
        .order_by(AwardRecord.award_date.desc())
    )
    awards = awards_result.scalars().all()

    budgets_result = await session.execute(
        select(BudgetIntelligence)
        .where(BudgetIntelligence.user_id == current_user.id)
        .where(
            (BudgetIntelligence.rfp_id == rfp_id) | (BudgetIntelligence.title.contains(rfp.agency))
        )
        .order_by(BudgetIntelligence.updated_at.desc())
    )
    budgets = budgets_result.scalars().all()

    top_awardees = [award.awardee_name for award in awards[:3]]
    contact_names = [contact.name for contact in contacts[:3]]
    budget_titles = [entry.title for entry in budgets[:3]]

    summary = (
        f"Research compiled for {rfp.title}: {len(contacts)} contacts, {len(awards)} related awards, "
        f"and {len(budgets)} budget intelligence records."
    )

    actions = [
        "Gathered agency contact intelligence",
        "Pulled incumbent and adjacent award signals",
        "Cross-referenced budget intelligence",
    ]

    return AgentRunResponse(
        agent="research",
        rfp_id=rfp_id,
        summary=summary,
        actions_taken=actions,
        artifacts={
            "top_contact_names": contact_names,
            "top_awardees": top_awardees,
            "budget_documents": budget_titles,
        },
    )


@router.post("/capture-planning/{rfp_id}", response_model=AgentRunResponse)
async def run_capture_planning_agent(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentRunResponse:
    rfp = await _get_owned_rfp(session, current_user, rfp_id)

    existing_result = await session.execute(
        select(CapturePlan).where(
            CapturePlan.rfp_id == rfp_id, CapturePlan.owner_id == current_user.id
        )
    )
    plan = existing_result.scalar_one_or_none()

    actions: list[str] = []
    if not plan:
        plan = CapturePlan(
            rfp_id=rfp_id,
            owner_id=current_user.id,
            stage=CaptureStage.QUALIFIED,
            bid_decision=BidDecision.PENDING,
            win_probability=int(rfp.match_score or rfp.qualification_score or 55),
            notes="Seeded by capture planning agent.",
        )
        session.add(plan)
        actions.append("Created capture plan")
    else:
        if plan.win_probability is None and (rfp.match_score or rfp.qualification_score):
            plan.win_probability = int(rfp.match_score or rfp.qualification_score)
            actions.append("Updated win probability from opportunity intelligence")
        if not plan.notes:
            plan.notes = "Maintained by capture planning agent."
        plan.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(plan)

    summary = (
        f"Capture planning complete for {rfp.title}. Stage={plan.stage.value}, "
        f"bid_decision={plan.bid_decision.value}, win_probability={plan.win_probability}."
    )

    return AgentRunResponse(
        agent="capture_planning",
        rfp_id=rfp_id,
        summary=summary,
        actions_taken=actions or ["Validated existing capture plan"],
        artifacts={
            "capture_plan_id": plan.id,
            "stage": plan.stage.value,
            "win_probability": plan.win_probability,
        },
    )


def _seed_sections_from_matrix(
    proposal_id: int, matrix: ComplianceMatrix | None
) -> list[ProposalSection]:
    sections: list[ProposalSection] = []

    if matrix and matrix.requirements:
        for idx, requirement in enumerate(matrix.requirements[:12], start=1):
            section_title = (
                requirement.get("category") or requirement.get("section") or f"Section {idx}"
            )
            section = ProposalSection(
                proposal_id=proposal_id,
                title=f"{section_title} Response",
                section_number=str(idx),
                requirement_id=requirement.get("id"),
                requirement_text=requirement.get("requirement_text"),
                display_order=idx,
            )
            sections.append(section)
        return sections

    defaults = [
        "Executive Summary",
        "Technical Approach",
        "Management Approach",
        "Staffing Plan",
        "Past Performance",
        "Pricing Narrative",
    ]
    for idx, title in enumerate(defaults, start=1):
        sections.append(
            ProposalSection(
                proposal_id=proposal_id,
                title=title,
                section_number=str(idx),
                display_order=idx,
            )
        )
    return sections


@router.post("/proposal-prep/{rfp_id}", response_model=AgentRunResponse)
async def run_proposal_prep_agent(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentRunResponse:
    rfp = await _get_owned_rfp(session, current_user, rfp_id)

    proposal_result = await session.execute(
        select(Proposal).where(Proposal.rfp_id == rfp_id, Proposal.user_id == current_user.id)
    )
    proposal = proposal_result.scalar_one_or_none()

    actions: list[str] = []
    if not proposal:
        proposal = Proposal(
            user_id=current_user.id,
            rfp_id=rfp_id,
            title=f"Proposal for {rfp.title}",
            status="in_progress",
        )
        session.add(proposal)
        await session.flush()
        actions.append("Created proposal workspace")

    matrix_result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = matrix_result.scalar_one_or_none()

    existing_sections_result = await session.execute(
        select(ProposalSection).where(ProposalSection.proposal_id == proposal.id)
    )
    existing_sections = existing_sections_result.scalars().all()

    if not existing_sections:
        seeded = _seed_sections_from_matrix(proposal.id, matrix)
        for section in seeded:
            session.add(section)
        proposal.total_sections = len(seeded)
        proposal.completed_sections = 0
        actions.append(f"Seeded {len(seeded)} proposal sections")

    proposal.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(proposal)

    sections_result = await session.execute(
        select(ProposalSection)
        .where(ProposalSection.proposal_id == proposal.id)
        .order_by(ProposalSection.display_order)
    )
    sections = sections_result.scalars().all()

    summary = (
        f"Proposal prep complete for {rfp.title}. Workspace #{proposal.id} now has "
        f"{len(sections)} sections ready for drafting."
    )

    return AgentRunResponse(
        agent="proposal_prep",
        rfp_id=rfp_id,
        summary=summary,
        actions_taken=actions or ["Validated existing proposal workspace"],
        artifacts={
            "proposal_id": proposal.id,
            "section_count": len(sections),
            "section_titles": [section.title for section in sections[:8]],
        },
    )


@router.post("/competitive-intel/{rfp_id}", response_model=AgentRunResponse)
async def run_competitive_intel_agent(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentRunResponse:
    rfp = await _get_owned_rfp(session, current_user, rfp_id)

    competitors_result = await session.execute(
        select(CaptureCompetitor)
        .where(CaptureCompetitor.user_id == current_user.id, CaptureCompetitor.rfp_id == rfp_id)
        .order_by(CaptureCompetitor.updated_at.desc())
    )
    competitors = competitors_result.scalars().all()

    awards_result = await session.execute(
        select(AwardRecord)
        .where(AwardRecord.user_id == current_user.id)
        .where((AwardRecord.agency == rfp.agency) | (AwardRecord.naics_code == rfp.naics_code))
        .order_by(AwardRecord.award_date.desc())
    )
    awards = awards_result.scalars().all()

    top_competitors = [competitor.name for competitor in competitors[:5]]
    top_awards = [
        {
            "awardee": award.awardee_name,
            "amount": award.award_amount,
            "contract_vehicle": award.contract_vehicle,
        }
        for award in awards[:5]
    ]

    summary = (
        f"Competitive intel synthesized for {rfp.title}: {len(competitors)} tracked competitors and "
        f"{len(awards)} related award records in peer agency/NAICS cohorts."
    )

    actions = [
        "Compiled competitor roster",
        "Ranked recent award patterns",
        "Prepared partner targeting shortlist",
    ]

    return AgentRunResponse(
        agent="competitive_intel",
        rfp_id=rfp_id,
        summary=summary,
        actions_taken=actions,
        artifacts={
            "competitors": top_competitors,
            "award_patterns": top_awards,
        },
    )
