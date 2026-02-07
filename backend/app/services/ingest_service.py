"""
RFP Sniper - SAM.gov Ingest Service
====================================
Connects to SAM.gov API to fetch government opportunities.

API Documentation: https://open.gsa.gov/api/get-opportunities-public-api/
"""

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.rfp import RFPType
from app.schemas.rfp import SAMOpportunity, SAMSearchParams

logger = structlog.get_logger(__name__)


class SAMGovAPIError(Exception):
    """Custom exception for SAM.gov API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        retryable: bool = True,
        is_rate_limited: bool = False,
        retry_after_seconds: int | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.retryable = retryable
        self.is_rate_limited = is_rate_limited
        self.retry_after_seconds = retry_after_seconds
        super().__init__(self.message)


class SAMGovService:
    """
    Service for interacting with SAM.gov Opportunities API.

    Handles:
    - Searching for opportunities by keyword, NAICS, set-aside
    - Rate limiting and retry logic
    - Parsing API responses into domain models
    """

    # SAM.gov API rate limits
    RATE_LIMIT_CALLS = 10
    RATE_LIMIT_PERIOD = 60  # seconds

    _circuit_open_until: datetime | None = None
    _circuit_reason: str | None = None

    # Procurement type mapping
    PTYPE_MAP = {
        "o": RFPType.SOLICITATION,
        "p": RFPType.PRESOLICITATION,
        "k": RFPType.COMBINED,
        "r": RFPType.SOURCES_SOUGHT,
        "s": RFPType.SPECIAL_NOTICE,
        "a": RFPType.AWARD,
    }

    def __init__(self, api_key: str | None = None, mock_variant: str | None = None):
        """
        Initialize SAM.gov service.

        Args:
            api_key: SAM.gov API key. Falls back to settings if not provided.
        """
        self.api_key = api_key or settings.sam_gov_api_key
        self.base_url = settings.sam_gov_base_url
        self.mock = settings.mock_sam_gov
        self.mock_variant = mock_variant or settings.mock_sam_gov_variant or "v1"

        if self.mock:
            logger.info("SAM.gov mock mode enabled")

        if not self.api_key and not self.mock:
            logger.warning("SAM.gov API key not configured")

    def _validate_api_key(self) -> None:
        """Ensure API key is configured."""
        if self.mock:
            return
        if not self.api_key:
            raise SAMGovAPIError(
                "SAM.gov API key not configured. Set SAM_GOV_API_KEY environment variable."
            )

    def _is_circuit_open(self) -> bool:
        if not settings.sam_circuit_breaker_enabled:
            return False
        if not self._circuit_open_until:
            return False
        return datetime.utcnow() < self._circuit_open_until

    def _open_circuit(self, retry_after: int | None, reason: str) -> None:
        if not settings.sam_circuit_breaker_enabled:
            return
        cooldown = settings.sam_circuit_breaker_cooldown_seconds
        max_seconds = settings.sam_circuit_breaker_max_seconds
        if retry_after and retry_after > 0:
            cooldown = max(cooldown, retry_after)
        cooldown = min(cooldown, max_seconds)
        self.__class__._circuit_open_until = datetime.utcnow() + timedelta(seconds=cooldown)
        self.__class__._circuit_reason = reason
        logger.warning(
            "SAM.gov circuit opened",
            reason=reason,
            open_seconds=cooldown,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def _make_request(
        self,
        params: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Make authenticated request to SAM.gov API with retry logic.

        Args:
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response
        """
        self._validate_api_key()
        if self._is_circuit_open():
            reason = self.__class__._circuit_reason or "rate_limited"
            raise SAMGovAPIError(
                f"SAM.gov circuit open ({reason}). Try again later.",
                status_code=429,
                retryable=False,
                is_rate_limited=True,
            )

        # Add API key to params
        params["api_key"] = self.api_key

        async with httpx.AsyncClient() as client:
            logger.info(
                "Making SAM.gov API request",
                params={k: v for k, v in params.items() if k != "api_key"},
            )

            response = await client.get(
                self.base_url,
                params=params,
                timeout=timeout,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after_header = response.headers.get("Retry-After")
                retry_after = 60
                if retry_after_header:
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        try:
                            retry_dt = parsedate_to_datetime(retry_after_header)
                            if retry_dt.tzinfo is None:
                                retry_dt = retry_dt.replace(tzinfo=UTC)
                            retry_after = max(
                                1,
                                int((retry_dt - datetime.now(UTC)).total_seconds()),
                            )
                        except Exception:
                            retry_after = 60
                max_retry_after = 60
                if retry_after > max_retry_after:
                    logger.warning(
                        "Retry-After exceeded cap; capping to avoid long sleeps",
                        retry_after=retry_after,
                        cap=max_retry_after,
                    )
                    retry_after = max_retry_after
                logger.warning(f"Rate limited by SAM.gov. Retry after {retry_after}s")
                self._open_circuit(retry_after, reason="rate_limited")
                raise SAMGovAPIError(
                    "SAM.gov rate limited",
                    status_code=429,
                    retryable=False,
                    is_rate_limited=True,
                    retry_after_seconds=retry_after,
                )

            # Raise for other HTTP errors
            response.raise_for_status()

            return response.json()

    def _parse_opportunity(self, raw: dict[str, Any]) -> SAMOpportunity:
        """
        Parse raw SAM.gov API response into SAMOpportunity model.

        Args:
            raw: Raw opportunity dict from API

        Returns:
            Parsed SAMOpportunity
        """
        # Extract agency from hierarchy
        org_hierarchy = raw.get("organizationHierarchy", [])
        agency = org_hierarchy[0].get("name", "Unknown") if org_hierarchy else "Unknown"
        sub_agency = org_hierarchy[1].get("name") if len(org_hierarchy) > 1 else None

        # Parse dates
        posted_date = None
        if raw.get("postedDate"):
            try:
                posted_date = datetime.strptime(raw["postedDate"], "%Y-%m-%d")
            except ValueError:
                pass

        response_deadline = None
        if raw.get("responseDeadLine"):
            try:
                # API returns various formats
                deadline_str = raw["responseDeadLine"]
                for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        response_deadline = datetime.strptime(
                            deadline_str[:19], fmt[:19].replace("%z", "")
                        )
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Determine RFP type
        ptype = raw.get("type", "o").lower()
        rfp_type = self.PTYPE_MAP.get(ptype, RFPType.SOLICITATION)

        return SAMOpportunity(
            title=raw.get("title", "Untitled"),
            solicitation_number=raw.get("solicitationNumber", raw.get("noticeId", "UNKNOWN")),
            agency=agency,
            sub_agency=sub_agency,
            posted_date=posted_date,
            response_deadline=response_deadline,
            naics_code=raw.get("naicsCode"),
            set_aside=raw.get("typeOfSetAsideDescription"),
            rfp_type=rfp_type,
            ui_link=raw.get("uiLink"),
            description=raw.get("description"),
        )

    def parse_opportunity(self, raw: dict[str, Any]) -> SAMOpportunity:
        """Public wrapper for parsing a raw opportunity payload."""
        return self._parse_opportunity(raw)

    def _mock_raw_opportunities(self, params: SAMSearchParams) -> list[dict[str, Any]]:
        """Return deterministic mock raw opportunities for local testing."""
        now = datetime.utcnow()
        keywords = params.keywords.strip()
        naics_code = params.naics_codes[0] if params.naics_codes else "541511"
        set_aside = params.set_aside_types[0] if params.set_aside_types else "Total Small Business"
        variant = (self.mock_variant or "v1").lower()
        description_suffix = "Includes software engineering, cloud migration, and DevOps."
        if variant != "v1":
            description_suffix = (
                "Includes modernization, security hardening, and performance tuning."
            )

        base = [
            {
                "noticeId": "MOCK-SAM-001",
                "solicitationNumber": "MOCK-SAM-001",
                "title": f"Mock SAM Opportunity: {keywords} Modernization",
                "organizationHierarchy": [
                    {"name": "Department of Innovation"},
                    {"name": "Office of Digital Services"},
                ],
                "postedDate": (now - timedelta(days=3)).strftime("%Y-%m-%d"),
                "responseDeadLine": (now + timedelta(days=21 if variant == "v1" else 28)).strftime(
                    "%Y-%m-%d"
                ),
                "naicsCode": naics_code,
                "typeOfSetAsideDescription": set_aside,
                "type": "o",
                "uiLink": "https://sam.gov/opp/mock-001",
                "description": (
                    f"Mock opportunity for {keywords} modernization support. {description_suffix}"
                ),
                "resourceLinks": [
                    {"url": "https://sam.gov/files/mock-001-base.pdf", "name": "RFP.pdf"}
                ]
                + (
                    [{"url": "https://sam.gov/files/mock-001-addendum.pdf", "name": "Addendum.pdf"}]
                    if variant != "v1"
                    else []
                ),
            },
            {
                "noticeId": "MOCK-SAM-002",
                "solicitationNumber": "MOCK-SAM-002",
                "title": f"Mock SAM Opportunity: {keywords} Managed Services",
                "organizationHierarchy": [
                    {"name": "General Services Administration"},
                    {"name": "Technology Services"},
                ],
                "postedDate": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
                "responseDeadLine": (now + timedelta(days=30 if variant == "v1" else 35)).strftime(
                    "%Y-%m-%d"
                ),
                "naicsCode": naics_code,
                "typeOfSetAsideDescription": "8(a) Competitive",
                "type": "k",
                "uiLink": "https://sam.gov/opp/mock-002",
                "description": (
                    f"Managed services for {keywords} programs, including help desk "
                    f"support, monitoring, and security compliance."
                ),
                "resourceLinks": [
                    {"url": "https://sam.gov/files/mock-002-statement.pdf", "name": "Statement.pdf"}
                ],
            },
            {
                "noticeId": "MOCK-SAM-003",
                "solicitationNumber": "MOCK-SAM-003",
                "title": f"Mock SAM Opportunity: {keywords} Data Analytics",
                "organizationHierarchy": [
                    {"name": "Department of Health and Human Services"},
                    {"name": "Office of the CIO"},
                ],
                "postedDate": (now - timedelta(days=12)).strftime("%Y-%m-%d"),
                "responseDeadLine": (now + timedelta(days=25 if variant == "v1" else 23)).strftime(
                    "%Y-%m-%d"
                ),
                "naicsCode": naics_code,
                "typeOfSetAsideDescription": "Small Business Set-Aside",
                "type": "r",
                "uiLink": "https://sam.gov/opp/mock-003",
                "description": (
                    f"Data analytics and reporting for {keywords} initiatives. "
                    "Focus on dashboards, ETL, and compliance metrics."
                ),
                "resourceLinks": [
                    {"url": "https://sam.gov/files/mock-003-data.pdf", "name": "Data.pdf"}
                ],
            },
        ]
        return base[: params.limit]

    def _mock_opportunities(self, params: SAMSearchParams) -> list[SAMOpportunity]:
        """Return deterministic mock opportunities for local testing."""
        raw = self._mock_raw_opportunities(params)
        return [self._parse_opportunity(item) for item in raw]

    async def search_opportunities_with_raw(
        self,
        params: SAMSearchParams,
    ) -> list[dict[str, Any]]:
        """
        Search SAM.gov for opportunities and return raw payloads.

        Args:
            params: Search parameters

        Returns:
            List of raw opportunity dicts
        """
        if self.mock:
            logger.info(
                "Returning mock SAM.gov opportunities (raw)",
                keywords=params.keywords,
                limit=params.limit,
            )
            return self._mock_raw_opportunities(params)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=params.days_back)

        # Build query params
        query_params: dict[str, Any] = {
            "postedFrom": start_date.strftime("%m/%d/%Y"),
            "postedTo": end_date.strftime("%m/%d/%Y"),
            "keywords": params.keywords,
            "limit": params.limit,
            "ptype": "o,k",  # Solicitations and Combined
            "sort": "-postedDate",
        }

        if params.active_only:
            query_params["active"] = "true"

        if params.naics_codes:
            query_params["ncode"] = ",".join(params.naics_codes)

        if params.set_aside_types:
            query_params["typeOfSetAside"] = ",".join(params.set_aside_types)

        try:
            data = await self._make_request(query_params)
            opportunities_data = data.get("opportunitiesData", [])
            logger.info(f"Found {len(opportunities_data)} opportunities from SAM.gov")
            return opportunities_data
        except httpx.HTTPStatusError as e:
            raise SAMGovAPIError(
                f"SAM.gov API error: {e.response.status_code}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            )
        except httpx.TimeoutException:
            raise SAMGovAPIError("SAM.gov API timeout")
        except Exception as e:
            raise SAMGovAPIError(f"Unexpected error: {str(e)}")

    async def search_opportunities(
        self,
        params: SAMSearchParams,
    ) -> list[SAMOpportunity]:
        """
        Search SAM.gov for opportunities matching criteria.

        Args:
            params: Search parameters

        Returns:
            List of matching opportunities
        """
        raw_opportunities = await self.search_opportunities_with_raw(params)

        opportunities = []
        for raw_opp in raw_opportunities:
            try:
                opp = self._parse_opportunity(raw_opp)
                opportunities.append(opp)
            except Exception as e:
                logger.warning(f"Failed to parse opportunity: {e}", raw=raw_opp)
                continue

        return opportunities

    async def get_opportunity_details(
        self,
        notice_id: str,
    ) -> dict[str, Any] | None:
        """
        Get detailed information about a specific opportunity.

        Args:
            notice_id: The SAM.gov notice ID

        Returns:
            Detailed opportunity data or None if not found
        """
        if self.mock:
            return {
                "noticeId": notice_id,
                "title": f"Mock SAM Opportunity {notice_id}",
                "uiLink": f"https://sam.gov/opp/{notice_id}",
            }
        self._validate_api_key()

        # Use the single opportunity endpoint
        detail_url = "https://api.sam.gov/prod/opportunities/v2/search"

        params = {
            "api_key": self.api_key,
            "noticeid": notice_id,
            "limit": 1,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(detail_url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                opportunities = data.get("opportunitiesData", [])
                if opportunities:
                    return opportunities[0]
                return None

        except Exception as e:
            logger.error(f"Failed to get opportunity details: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if SAM.gov API is accessible.

        Returns:
            True if API is healthy
        """
        if self.mock:
            return True
        try:
            # Make a minimal request
            params = {
                "api_key": self.api_key,
                "limit": 1,
                "postedFrom": datetime.now().strftime("%m/%d/%Y"),
                "postedTo": datetime.now().strftime("%m/%d/%Y"),
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=10.0,
                )
                return response.status_code == 200

        except Exception:
            return False


# =============================================================================
# Convenience Functions
# =============================================================================


async def ingest_opportunities(
    keywords: str,
    user_id: int,
    days_back: int = 90,
    limit: int = 25,
    naics_codes: list[str] | None = None,
) -> list[SAMOpportunity]:
    """
    High-level function to ingest opportunities from SAM.gov.

    This is typically called from a Celery task.

    Args:
        keywords: Search keywords
        user_id: User ID for attribution
        days_back: How many days back to search
        limit: Maximum results
        naics_codes: Filter by NAICS codes

    Returns:
        List of opportunities found
    """
    service = SAMGovService()

    params = SAMSearchParams(
        keywords=keywords,
        days_back=days_back,
        limit=limit,
        naics_codes=naics_codes,
    )

    return await service.search_opportunities(params)
