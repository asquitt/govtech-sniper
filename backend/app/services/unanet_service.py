"""
RFP Sniper - Unanet Integration Service
=========================================
Stub service for syncing projects with Unanet ERP.
"""

from datetime import datetime
from typing import Optional

from app.models.integration import IntegrationConfig


class UnanetService:
    """Handles communication with the Unanet API (stub)."""

    def __init__(self, config: IntegrationConfig) -> None:
        self.config = config
        self.base_url: Optional[str] = (config.config or {}).get("base_url")
        self.api_key: Optional[str] = (config.config or {}).get("api_key")

    async def list_projects(self) -> list[dict]:
        """Return mock project list from Unanet."""
        return [
            {
                "id": "PROJ-001",
                "name": "GSA MAS IT Modernization",
                "status": "active",
                "start_date": "2025-01-15",
                "end_date": "2025-12-31",
                "budget": 450000.00,
                "percent_complete": 35,
            },
            {
                "id": "PROJ-002",
                "name": "DHS Cyber Assessment",
                "status": "active",
                "start_date": "2025-03-01",
                "end_date": "2025-09-30",
                "budget": 275000.00,
                "percent_complete": 60,
            },
            {
                "id": "PROJ-003",
                "name": "VA Claims Processing Upgrade",
                "status": "proposal",
                "start_date": None,
                "end_date": None,
                "budget": 820000.00,
                "percent_complete": 0,
            },
        ]

    async def sync_projects(self) -> dict:
        """Trigger a mock sync between Sniper and Unanet."""
        return {
            "status": "success",
            "projects_synced": 3,
            "errors": [],
            "synced_at": datetime.utcnow().isoformat(),
        }

    async def get_project(self, project_id: str) -> Optional[dict]:
        """Return a single mock project by ID."""
        projects = await self.list_projects()
        for project in projects:
            if project["id"] == project_id:
                return project
        return None
