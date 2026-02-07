"""Autonomous AI agent framework."""

from app.services.agents.research_agent import ResearchAgent
from app.services.agents.capture_agent import CaptureAgent
from app.services.agents.proposal_prep_agent import ProposalPrepAgent

AGENT_REGISTRY = {
    "research": ResearchAgent,
    "capture": CaptureAgent,
    "proposal_prep": ProposalPrepAgent,
}


def get_agent(agent_type: str):
    agent_class = AGENT_REGISTRY.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return agent_class()
