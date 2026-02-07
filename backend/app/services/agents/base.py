"""Base agent class for autonomous task execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentRunResult:
    agent_type: str
    run_id: str
    status: str
    result: dict = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.utcnow)


class BaseAgent(ABC):
    agent_type: str = "base"
    description: str = "Base agent"

    @abstractmethod
    async def execute(self, params: dict, user_id: int) -> AgentRunResult:
        pass
