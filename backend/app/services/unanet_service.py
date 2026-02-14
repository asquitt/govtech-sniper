"""
RFP Sniper - Unanet Integration Service
=========================================
Production Unanet API client with deterministic fallback behavior.
"""

from __future__ import annotations

import datetime
from typing import Any

import httpx
import structlog

from app.models.integration import IntegrationConfig

logger = structlog.get_logger(__name__)


class UnanetServiceError(RuntimeError):
    """Raised when Unanet integration operations fail."""


class UnanetService:
    """Handles communication with the Unanet API."""

    def __init__(self, config: IntegrationConfig) -> None:
        self.config = config
        raw = config.config or {}
        self.base_url: str = str(raw.get("base_url", "")).strip().rstrip("/")
        self.api_key: str | None = raw.get("api_key")
        self.access_token: str | None = raw.get("access_token")
        self.username: str | None = raw.get("username")
        self.password: str | None = raw.get("password")
        self.auth_type: str = str(raw.get("auth_type", "")).strip().lower()
        self.api_key_header: str = str(raw.get("api_key_header", "X-API-Key"))
        self.timeout_seconds: float = float(raw.get("timeout_seconds", 20))
        self.verify_ssl: bool = bool(raw.get("verify_ssl", True))
        self.projects_endpoint: str = str(raw.get("projects_endpoint", "/api/projects"))
        self.sync_endpoint: str | None = raw.get("sync_endpoint")
        self.resources_endpoint: str = str(raw.get("resources_endpoint", "/api/resources"))
        self.financials_endpoint: str = str(raw.get("financials_endpoint", "/api/financials"))
        self.resource_sync_endpoint: str | None = raw.get("resource_sync_endpoint")
        self.financial_sync_endpoint: str | None = raw.get("financial_sync_endpoint")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        auth_type = self.auth_type
        if not auth_type:
            if self.access_token:
                auth_type = "bearer"
            elif self.api_key:
                auth_type = "api_key"
            elif self.username and self.password:
                auth_type = "basic"
            else:
                auth_type = "none"

        if auth_type == "bearer" and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif auth_type == "api_key" and self.api_key:
            headers[self.api_key_header] = self.api_key
        return headers

    def _auth(self) -> tuple[str, str] | None:
        auth_type = self.auth_type
        if not auth_type:
            auth_type = "basic" if self.username and self.password else "none"
        if auth_type == "basic" and self.username and self.password:
            return (self.username, self.password)
        return None

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        base = self.base_url.rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        if not self.base_url:
            raise UnanetServiceError("Unanet base_url is not configured")

        url = self._url(endpoint)
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                verify=self.verify_ssl,
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=self._headers(),
                    auth=self._auth(),
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "unanet_http_status_error",
                status_code=exc.response.status_code,
                endpoint=endpoint,
                response_text=exc.response.text[:300],
            )
            raise UnanetServiceError(
                f"Unanet API returned status {exc.response.status_code} for {endpoint}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("unanet_http_error", endpoint=endpoint, error=str(exc))
            raise UnanetServiceError(f"Failed request to Unanet endpoint {endpoint}") from exc

        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            return response.json()

        body = response.text.strip()
        if not body:
            return {}
        return {"raw": body}

    async def list_projects(self) -> list[dict]:
        """Return normalized project list from Unanet."""
        payload = await self._request("GET", self.projects_endpoint)
        records = _extract_records(payload)
        return [_normalize_project(record) for record in records]

    async def list_resources(self) -> list[dict]:
        """Return normalized resource planning records from Unanet."""
        payload = await self._request("GET", self.resources_endpoint)
        records = _extract_records(payload)
        return [_normalize_resource(record) for record in records]

    async def list_financials(self) -> list[dict]:
        """Return normalized financial records from Unanet."""
        payload = await self._request("GET", self.financials_endpoint)
        records = _extract_records(payload)
        return [_normalize_financial_record(record) for record in records]

    async def sync_projects(self) -> dict:
        """Trigger a sync operation and return canonical status payload."""
        synced_at = datetime.datetime.now(datetime.UTC).isoformat()
        if self.sync_endpoint:
            payload = await self._request("POST", self.sync_endpoint, json_body={})
            projects_synced = _extract_synced_count(payload)
            errors = _extract_errors(payload)
            status = "success" if not errors else "failed"
            return {
                "status": status,
                "projects_synced": projects_synced,
                "errors": errors,
                "synced_at": synced_at,
            }

        projects = await self.list_projects()
        return {
            "status": "success",
            "projects_synced": len(projects),
            "errors": [],
            "synced_at": synced_at,
        }

    async def sync_resources(self) -> dict:
        """Trigger resource data sync and return canonical status payload."""
        synced_at = datetime.datetime.now(datetime.UTC).isoformat()
        if self.resource_sync_endpoint:
            payload = await self._request("POST", self.resource_sync_endpoint, json_body={})
            resources_synced = _extract_synced_count(payload)
            errors = _extract_errors(payload)
            status = "success" if not errors else "failed"
            return {
                "status": status,
                "resources_synced": resources_synced,
                "errors": errors,
                "synced_at": synced_at,
            }

        resources = await self.list_resources()
        return {
            "status": "success",
            "resources_synced": len(resources),
            "errors": [],
            "synced_at": synced_at,
        }

    async def sync_financials(self) -> dict:
        """Trigger financial data sync and return canonical status payload."""
        synced_at = datetime.datetime.now(datetime.UTC).isoformat()
        if self.financial_sync_endpoint:
            payload = await self._request("POST", self.financial_sync_endpoint, json_body={})
            records_synced = _extract_synced_count(payload)
            errors = _extract_errors(payload)
            status = "success" if not errors else "failed"
            return {
                "status": status,
                "records_synced": records_synced,
                "total_funded_value": float(_extract_total_funded_value(payload)),
                "errors": errors,
                "synced_at": synced_at,
            }

        financial_records = await self.list_financials()
        return {
            "status": "success",
            "records_synced": len(financial_records),
            "total_funded_value": float(
                sum(float(record.get("funded_value", 0.0)) for record in financial_records)
            ),
            "errors": [],
            "synced_at": synced_at,
        }

    async def get_project(self, project_id: str) -> dict | None:
        """Fetch a single project if supported by endpoint conventions."""
        if not project_id:
            return None
        try:
            payload = await self._request(
                "GET", f"{self.projects_endpoint.rstrip('/')}/{project_id}"
            )
            records = _extract_records(payload)
            if not records and isinstance(payload, dict):
                records = [payload]
            if not records:
                return None
            return _normalize_project(records[0])
        except UnanetServiceError:
            projects = await self.list_projects()
            for project in projects:
                if project["id"] == project_id:
                    return project
            return None

    async def health_check(self) -> bool:
        """Best-effort health check against configured project endpoint."""
        try:
            await self._request("GET", self.projects_endpoint, params={"limit": 1})
            return True
        except UnanetServiceError:
            return False


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in (
            "projects",
            "resources",
            "financials",
            "labor_categories",
            "contracts",
            "items",
            "results",
            "data",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _extract_synced_count(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in ("projects_synced", "synced", "count", "items_synced"):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return int(value)
    records = _extract_records(payload)
    return len(records)


def _extract_errors(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list):
            return [str(item) for item in errors]
        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            return [error]
    return []


def _extract_total_funded_value(payload: Any) -> float:
    if isinstance(payload, dict):
        for key in ("total_funded_value", "funded_value_total", "total_funded", "total_value"):
            value = payload.get(key)
            if value is not None:
                return _as_float(value)
    return 0.0


def _normalize_project(payload: dict[str, Any]) -> dict:
    project_id = (
        payload.get("id")
        or payload.get("project_id")
        or payload.get("projectNumber")
        or payload.get("project_number")
        or payload.get("code")
        or "unknown"
    )
    name = payload.get("name") or payload.get("project_name") or payload.get("title") or "Unnamed"
    status = payload.get("status") or payload.get("state") or "unknown"
    start_date = _normalize_date(payload.get("start_date") or payload.get("startDate"))
    end_date = _normalize_date(payload.get("end_date") or payload.get("endDate"))
    budget = _as_float(payload.get("budget") or payload.get("totalBudget") or payload.get("value"))
    percent_complete = int(
        _as_float(
            payload.get("percent_complete")
            or payload.get("percentComplete")
            or payload.get("progress")
            or payload.get("completion")
        )
    )
    percent_complete = max(0, min(100, percent_complete))
    return {
        "id": str(project_id),
        "name": str(name),
        "status": str(status),
        "start_date": start_date,
        "end_date": end_date,
        "budget": budget,
        "percent_complete": percent_complete,
    }


def _normalize_resource(payload: dict[str, Any]) -> dict:
    resource_id = (
        payload.get("id")
        or payload.get("resource_id")
        or payload.get("labor_category_id")
        or payload.get("category_code")
        or payload.get("code")
        or "unknown"
    )
    labor_category = (
        payload.get("labor_category")
        or payload.get("laborCategory")
        or payload.get("name")
        or payload.get("title")
        or "Unknown Labor Category"
    )
    role = payload.get("role") or payload.get("labor_role") or payload.get("family") or "general"
    hourly_rate = _as_float(
        payload.get("hourly_rate")
        or payload.get("rate")
        or payload.get("bill_rate")
        or payload.get("billing_rate")
    )
    cost_rate = _as_float(
        payload.get("cost_rate")
        or payload.get("cost")
        or payload.get("burdened_cost_rate")
        or payload.get("costRate")
    )
    availability_hours = _as_float(
        payload.get("availability_hours")
        or payload.get("available_hours")
        or payload.get("capacity_hours")
    )
    source_project_id = (
        payload.get("project_id")
        or payload.get("projectNumber")
        or payload.get("project_code")
        or payload.get("projectCode")
    )
    status_value = str(payload.get("status") or "").lower()
    is_active = bool(
        payload.get("is_active")
        if payload.get("is_active") is not None
        else payload.get("active")
        if payload.get("active") is not None
        else status_value not in {"inactive", "disabled"}
    )
    effective_date = _normalize_date(
        payload.get("effective_date") or payload.get("start_date") or payload.get("effectiveDate")
    )
    currency = str(payload.get("currency") or "USD")
    return {
        "id": str(resource_id),
        "labor_category": str(labor_category),
        "role": str(role),
        "hourly_rate": hourly_rate,
        "cost_rate": cost_rate,
        "currency": currency,
        "availability_hours": availability_hours,
        "source_project_id": str(source_project_id) if source_project_id is not None else None,
        "effective_date": effective_date,
        "is_active": is_active,
    }


def _normalize_financial_record(payload: dict[str, Any]) -> dict:
    record_id = (
        payload.get("id")
        or payload.get("record_id")
        or payload.get("transaction_id")
        or payload.get("invoice_id")
        or "unknown"
    )
    project_id = (
        payload.get("project_id")
        or payload.get("projectNumber")
        or payload.get("contract_id")
        or payload.get("projectCode")
    )
    project_name = (
        payload.get("project_name")
        or payload.get("contract_name")
        or payload.get("name")
        or "Unknown Project"
    )
    fiscal_year_raw = payload.get("fiscal_year") or payload.get("fy") or payload.get("year")
    fiscal_year = int(_as_float(fiscal_year_raw)) if fiscal_year_raw is not None else None
    booked_revenue = _as_float(
        payload.get("booked_revenue") or payload.get("revenue") or payload.get("recognized_revenue")
    )
    funded_value = _as_float(
        payload.get("funded_value")
        or payload.get("ceiling_value")
        or payload.get("contract_value")
        or payload.get("value")
    )
    invoiced_to_date = _as_float(
        payload.get("invoiced_to_date")
        or payload.get("invoiced")
        or payload.get("actuals")
        or payload.get("actual_cost")
    )
    remaining_value = _as_float(payload.get("remaining_value"))
    if remaining_value == 0.0 and funded_value > 0:
        remaining_value = max(funded_value - invoiced_to_date, 0.0)

    burn_rate_percent = _as_float(payload.get("burn_rate_percent") or payload.get("burn_rate"))
    if burn_rate_percent == 0.0 and funded_value > 0:
        burn_rate_percent = round((invoiced_to_date / funded_value) * 100.0, 2)

    as_of_date = _normalize_date(
        payload.get("as_of_date")
        or payload.get("period_end")
        or payload.get("updated_at")
        or payload.get("asOfDate")
    )
    currency = str(payload.get("currency") or "USD")
    status = str(payload.get("status") or payload.get("state") or "unknown")

    return {
        "id": str(record_id),
        "project_id": str(project_id) if project_id is not None else None,
        "project_name": str(project_name),
        "fiscal_year": fiscal_year,
        "booked_revenue": booked_revenue,
        "funded_value": funded_value,
        "invoiced_to_date": invoiced_to_date,
        "remaining_value": remaining_value,
        "burn_rate_percent": burn_rate_percent,
        "currency": currency,
        "status": status,
        "as_of_date": as_of_date,
    }


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return 0.0
    return 0.0


def _normalize_date(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned[:10] if len(cleaned) >= 10 else cleaned
    return None
