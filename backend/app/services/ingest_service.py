"""
RFP Sniper - SAM.gov Ingest Service
====================================
Connects to SAM.gov API to fetch government opportunities.

API Documentation: https://open.gsa.gov/api/get-opportunities-public-api/
"""

import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional, Dict, Any
import structlog

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.schemas.rfp import SAMOpportunity, SAMSearchParams
from app.models.rfp import RFPType

logger = structlog.get_logger(__name__)


class SAMGovAPIError(Exception):
    """Custom exception for SAM.gov API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
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
    
    # Procurement type mapping
    PTYPE_MAP = {
        "o": RFPType.SOLICITATION,
        "p": RFPType.PRESOLICITATION,
        "k": RFPType.COMBINED,
        "r": RFPType.SOURCES_SOUGHT,
        "s": RFPType.SPECIAL_NOTICE,
        "a": RFPType.AWARD,
    }

    def __init__(self, api_key: Optional[str] = None, mock_variant: Optional[str] = None):
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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def _make_request(
        self,
        params: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to SAM.gov API with retry logic.
        
        Args:
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Parsed JSON response
        """
        self._validate_api_key()
        
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
                                retry_dt = retry_dt.replace(tzinfo=timezone.utc)
                            retry_after = max(
                                1,
                                int((retry_dt - datetime.now(timezone.utc)).total_seconds()),
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
                await asyncio.sleep(retry_after)
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=response.request,
                    response=response,
                )
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            return response.json()
    
    def _parse_opportunity(self, raw: Dict[str, Any]) -> SAMOpportunity:
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
                        response_deadline = datetime.strptime(deadline_str[:19], fmt[:19].replace("%z", ""))
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

    def parse_opportunity(self, raw: Dict[str, Any]) -> SAMOpportunity:
        """Public wrapper for parsing a raw opportunity payload."""
        return self._parse_opportunity(raw)

    def _mock_raw_opportunities(self, params: SAMSearchParams) -> List[Dict[str, Any]]:
        """Return deterministic mock raw opportunities for local testing."""
        now = datetime.utcnow()
        keywords = params.keywords.strip()
        naics_code = params.naics_codes[0] if params.naics_codes else "541511"
        set_aside = (
            params.set_aside_types[0]
            if params.set_aside_types
            else "Total Small Business"
        )
        variant = (self.mock_variant or "v1").lower()
        description_suffix = "Includes software engineering, cloud migration, and DevOps."
        if variant != "v1":
            description_suffix = "Includes modernization, security hardening, and performance tuning."

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
                "responseDeadLine": (
                    now + timedelta(days=21 if variant == "v1" else 28)
                ).strftime("%Y-%m-%d"),
                "naicsCode": naics_code,
                "typeOfSetAsideDescription": set_aside,
                "type": "o",
                "uiLink": "https://sam.gov/opp/mock-001",
                "description": (
                    f"Mock opportunity for {keywords} modernization support. "
                    f"{description_suffix}"
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
                "responseDeadLine": (
                    now + timedelta(days=30 if variant == "v1" else 35)
                ).strftime("%Y-%m-%d"),
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
                "responseDeadLine": (
                    now + timedelta(days=25 if variant == "v1" else 23)
                ).strftime("%Y-%m-%d"),
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
        return base[:params.limit]

    def _mock_opportunities(self, params: SAMSearchParams) -> List[SAMOpportunity]:
        """Return deterministic mock opportunities for local testing."""
        raw = self._mock_raw_opportunities(params)
        return [self._parse_opportunity(item) for item in raw]

    async def search_opportunities_with_raw(
        self,
        params: SAMSearchParams,
    ) -> List[Dict[str, Any]]:
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
        query_params: Dict[str, Any] = {
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
    ) -> List[SAMOpportunity]:
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
    ) -> Optional[Dict[str, Any]]:
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
        detail_url = f"https://api.sam.gov/prod/opportunities/v2/search"
        
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
    naics_codes: Optional[List[str]] = None,
) -> List[SAMOpportunity]:
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
