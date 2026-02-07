"""
RFP Sniper - Salesforce Integration Service
=============================================
OAuth2 password-flow client for Salesforce REST API.
Handles bidirectional sync between capture plans and SF Opportunities.
"""

import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.integration import (
    IntegrationConfig,
    IntegrationSyncRun,
    IntegrationSyncStatus,
    IntegrationProvider,
)
from app.models.capture import CapturePlan
from app.models.rfp import RFP

logger = logging.getLogger(__name__)

SF_API_VERSION = "v59.0"


class SalesforceService:
    """Thin wrapper around Salesforce REST API."""

    def __init__(
        self,
        instance_url: str,
        client_id: str,
        client_secret: str,
        username: str,
        security_token: str,
    ):
        self.instance_url = instance_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.security_token = security_token
        self._access_token: Optional[str] = None
        self._token_instance_url: Optional[str] = None

    async def _get_token(self) -> str:
        """Acquire access token via OAuth2 password flow."""
        if self._access_token:
            return self._access_token

        token_url = f"{self.instance_url}/services/oauth2/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": self.username,
                    "password": self.security_token,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            self._access_token = body["access_token"]
            self._token_instance_url = body.get("instance_url", self.instance_url)
            return self._access_token

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _base_url(self) -> str:
        base = self._token_instance_url or self.instance_url
        return f"{base}/services/data/{SF_API_VERSION}"

    async def list_opportunities(self) -> list[dict]:
        """Query Salesforce for all Opportunities."""
        token = await self._get_token()
        query = (
            "SELECT Id, Name, Amount, StageName, CloseDate "
            "FROM Opportunity ORDER BY CloseDate DESC LIMIT 200"
        )
        url = f"{self._base_url()}/query/"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params={"q": query},
                headers=self._headers(token),
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json().get("records", [])

    async def push_opportunity(
        self,
        capture_plan: CapturePlan,
        rfp: RFP,
        sf_id: Optional[str] = None,
    ) -> dict:
        """Create or update a Salesforce Opportunity from a capture plan."""
        token = await self._get_token()
        payload = {
            "Name": rfp.title or f"Opportunity {rfp.id}",
            "StageName": capture_plan.stage.value.title(),
            "CloseDate": (
                rfp.response_date.isoformat()
                if rfp.response_date
                else datetime.utcnow().date().isoformat()
            ),
        }
        if capture_plan.win_probability is not None:
            payload["Probability"] = capture_plan.win_probability

        async with httpx.AsyncClient() as client:
            if sf_id:
                url = f"{self._base_url()}/sobjects/Opportunity/{sf_id}"
                resp = await client.patch(
                    url,
                    json=payload,
                    headers=self._headers(token),
                    timeout=30.0,
                )
            else:
                url = f"{self._base_url()}/sobjects/Opportunity"
                resp = await client.post(
                    url,
                    json=payload,
                    headers=self._headers(token),
                    timeout=30.0,
                )
            resp.raise_for_status()
            return resp.json() if resp.content else {"success": True}

    async def pull_opportunities(self) -> list[dict]:
        """Fetch SF Opportunities and return normalized dicts."""
        records = await self.list_opportunities()
        return [
            {
                "sf_id": r.get("Id", ""),
                "name": r.get("Name", ""),
                "amount": r.get("Amount"),
                "stage": r.get("StageName"),
                "close_date": r.get("CloseDate"),
            }
            for r in records
        ]

    async def sync_bidirectional(
        self,
        user_id: int,
        integration_id: int,
        session: AsyncSession,
    ) -> dict:
        """Full bidirectional sync: push capture plans, pull SF opportunities."""
        sync_run = IntegrationSyncRun(
            integration_id=integration_id,
            provider=IntegrationProvider.SALESFORCE,
            status=IntegrationSyncStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        session.add(sync_run)
        await session.flush()

        pushed = 0
        pulled = 0
        errors: list[str] = []

        # Push: send capture plans to SF
        result = await session.execute(
            select(CapturePlan).where(CapturePlan.owner_id == user_id)
        )
        plans = result.scalars().all()

        for plan in plans:
            rfp_result = await session.execute(
                select(RFP).where(RFP.id == plan.rfp_id)
            )
            rfp = rfp_result.scalar_one_or_none()
            if not rfp:
                continue
            try:
                await self.push_opportunity(plan, rfp)
                pushed += 1
            except Exception as exc:
                errors.append(f"Push plan {plan.id}: {exc}")

        # Pull: fetch SF opportunities
        try:
            opps = await self.pull_opportunities()
            pulled = len(opps)
        except Exception as exc:
            errors.append(f"Pull opportunities: {exc}")

        # Finalize sync run
        sync_run.status = (
            IntegrationSyncStatus.SUCCESS if not errors
            else IntegrationSyncStatus.FAILED
        )
        sync_run.items_synced = pushed + pulled
        sync_run.error = "; ".join(errors) if errors else None
        sync_run.details = {"pushed": pushed, "pulled": pulled, "errors": errors}
        sync_run.completed_at = datetime.utcnow()
        await session.commit()

        return {
            "status": "success" if not errors else "failed",
            "pushed": pushed,
            "pulled": pulled,
            "errors": errors,
            "completed_at": sync_run.completed_at,
        }


def create_salesforce_service(config: dict) -> SalesforceService:
    """Factory to build SalesforceService from integration config dict."""
    required = ["instance_url", "client_id", "client_secret", "username", "security_token"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise ValueError(f"Missing Salesforce config fields: {', '.join(missing)}")

    return SalesforceService(
        instance_url=config["instance_url"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        username=config["username"],
        security_token=config["security_token"],
    )
