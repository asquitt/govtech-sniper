"""
RFP Sniper - RFP Document Downloader
=====================================
Automatically download RFP PDFs and attachments from SAM.gov.
"""

import asyncio
import hashlib
import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.services.pdf_processor import get_pdf_processor

logger = structlog.get_logger(__name__)


@dataclass
class DownloadedDocument:
    """Result of a document download."""

    filename: str
    file_path: str
    file_size: int
    mime_type: str
    content_hash: str
    extracted_text: str | None = None
    page_count: int | None = None


class RFPDownloader:
    """
    Service for downloading RFP documents from SAM.gov.

    SAM.gov provides links to opportunity attachments. This service:
    1. Fetches the attachment list for an opportunity
    2. Downloads each attachment
    3. Extracts text from PDFs
    4. Stores files locally for processing
    """

    # SAM.gov attachment API endpoint
    ATTACHMENTS_URL = "https://api.sam.gov/prod/opportunities/v1/search"

    def __init__(self, api_key: str | None = None):
        """
        Initialize the RFP downloader.

        Args:
            api_key: SAM.gov API key
        """
        self.api_key = api_key or settings.sam_gov_api_key
        self.upload_dir = settings.upload_dir
        self.pdf_processor = get_pdf_processor()

        # Ensure upload directory exists
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(os.path.join(self.upload_dir, "rfps"), exist_ok=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_opportunity_attachments(
        self,
        notice_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get list of attachments for a SAM.gov opportunity.

        Args:
            notice_id: The SAM.gov notice ID

        Returns:
            List of attachment metadata dicts
        """
        if settings.mock_sam_gov and settings.sam_mock_attachments_dir:
            base_dir = Path(settings.sam_mock_attachments_dir)
            notice_dir = base_dir / str(notice_id)
            target_dir = notice_dir if notice_dir.exists() else base_dir
            if not target_dir.exists():
                logger.info(
                    "Mock attachments dir not found",
                    notice_id=notice_id,
                    dir=str(target_dir),
                )
                return []

            attachments = []
            for path in sorted(target_dir.iterdir()):
                if path.is_file():
                    attachments.append(
                        {
                            "url": f"file://{path}",
                            "filename": path.name,
                            "type": "mock_fixture",
                        }
                    )

            logger.info(
                "Using mock attachments",
                notice_id=notice_id,
                count=len(attachments),
                dir=str(target_dir),
            )
            return attachments

        if settings.mock_sam_gov:
            logger.info("Skipping attachment fetch in mock mode", notice_id=notice_id)
            return []

        if not self.api_key:
            logger.warning("SAM.gov API key not configured")
            return []

        # SAM.gov uses a different endpoint for attachments
        # The opportunity detail includes resource links
        detail_url = "https://api.sam.gov/prod/opportunities/v2/search"

        params = {
            "api_key": self.api_key,
            "noticeid": notice_id,
            "limit": 1,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    detail_url,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                opportunities = data.get("opportunitiesData", [])
                if not opportunities:
                    return []

                opp = opportunities[0]

                # Extract attachment info from resourceLinks
                attachments = []
                resource_links = opp.get("resourceLinks", [])

                for link in resource_links:
                    if isinstance(link, str):
                        # Simple URL
                        attachments.append(
                            {
                                "url": link,
                                "filename": link.split("/")[-1],
                                "type": "unknown",
                            }
                        )
                    elif isinstance(link, dict):
                        attachments.append(
                            {
                                "url": link.get("url", ""),
                                "filename": link.get("name", "attachment"),
                                "type": link.get("type", "unknown"),
                                "description": link.get("description", ""),
                            }
                        )

                # Also check for attachments in description links
                description = opp.get("description", "")
                if description:
                    # Extract URLs from description
                    import re

                    urls = re.findall(
                        r'https?://[^\s<>"{}|\\^`\[\]]+\.pdf', description, re.IGNORECASE
                    )
                    for url in urls:
                        if url not in [a["url"] for a in attachments]:
                            attachments.append(
                                {
                                    "url": url,
                                    "filename": url.split("/")[-1],
                                    "type": "pdf",
                                }
                            )

                logger.info(
                    "Found attachments",
                    notice_id=notice_id,
                    count=len(attachments),
                )

                return attachments

        except Exception as e:
            logger.error(f"Failed to get attachments: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def download_attachment(
        self,
        url: str,
        rfp_id: int,
        filename: str | None = None,
    ) -> DownloadedDocument | None:
        """
        Download an attachment from a URL.

        Args:
            url: URL to download
            rfp_id: RFP ID for organizing files
            filename: Override filename

        Returns:
            DownloadedDocument or None if failed
        """
        try:
            content: bytes
            mime_type: str

            if url.startswith("file://"):
                local_path = url[len("file://") :]
                logger.info("Loading attachment from file", path=local_path)
                with open(local_path, "rb") as f:
                    content = f.read()
                if not filename:
                    filename = os.path.basename(local_path)
                guessed_type, _ = mimetypes.guess_type(filename or local_path)
                mime_type = guessed_type or "application/octet-stream"
            else:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    logger.info("Downloading attachment", url=url[:100])

                    response = await client.get(url, timeout=120.0)
                    response.raise_for_status()

                    # Determine filename
                    if not filename:
                        # Try to get from Content-Disposition header
                        content_disposition = response.headers.get("Content-Disposition", "")
                        if "filename=" in content_disposition:
                            import re

                            match = re.search(r'filename="?([^";\n]+)"?', content_disposition)
                            if match:
                                filename = match.group(1)

                        if not filename:
                            # Use URL path
                            filename = url.split("/")[-1].split("?")[0]

                        if not filename:
                            filename = f"attachment_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

                    # Determine mime type
                    content_type = response.headers.get("Content-Type", "application/octet-stream")
                    mime_type = content_type.split(";")[0].strip()
                    content = response.content

            # Clean filename
            filename = "".join(c for c in (filename or "") if c.isalnum() or c in "._- ")
            if not filename:
                filename = f"attachment_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            filename = filename[:100]  # Limit length

            # Create directory for RFP
            rfp_dir = os.path.join(self.upload_dir, "rfps", str(rfp_id))
            os.makedirs(rfp_dir, exist_ok=True)

            # Save file
            file_path = os.path.join(rfp_dir, filename)

            with open(file_path, "wb") as f:
                f.write(content)

            # Calculate hash
            content_hash = hashlib.sha256(content).hexdigest()

            result = DownloadedDocument(
                filename=filename,
                file_path=file_path,
                file_size=len(content),
                mime_type=mime_type,
                content_hash=content_hash,
            )

            # Extract text if PDF
            if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
                try:
                    pdf_doc = self.pdf_processor.extract_text(content, filename)
                    result.extracted_text = pdf_doc.full_text
                    result.page_count = pdf_doc.total_pages
                    logger.info(
                        "PDF text extracted",
                        filename=filename,
                        pages=pdf_doc.total_pages,
                    )
                except Exception as e:
                    logger.warning(f"PDF extraction failed: {e}")
            elif mime_type.startswith("text/") or filename.lower().endswith(".txt"):
                try:
                    result.extracted_text = content.decode("utf-8", errors="ignore").strip()
                    result.page_count = 1
                    logger.info("Text attachment extracted", filename=filename)
                except Exception as e:
                    logger.warning(f"Text extraction failed: {e}")

            logger.info(
                "Attachment downloaded",
                filename=filename,
                size_kb=len(content) // 1024,
            )

            return result

        except Exception as e:
            logger.error(f"Download failed: {e}", url=url[:100])
            return None

    async def download_all_attachments(
        self,
        notice_id: str,
        rfp_id: int,
        max_attachments: int = 10,
    ) -> list[DownloadedDocument]:
        """
        Download all attachments for an opportunity.

        Args:
            notice_id: SAM.gov notice ID
            rfp_id: Local RFP ID
            max_attachments: Maximum number to download

        Returns:
            List of downloaded documents
        """
        attachments = await self.get_opportunity_attachments(notice_id)

        if not attachments:
            logger.info("No attachments found", notice_id=notice_id)
            return []

        # Limit attachments
        attachments = attachments[:max_attachments]

        downloaded = []
        for attachment in attachments:
            url = attachment.get("url")
            if not url:
                continue

            filename = attachment.get("filename")
            result = await self.download_attachment(url, rfp_id, filename)

            if result:
                downloaded.append(result)

            # Small delay between downloads
            await asyncio.sleep(0.5)

        logger.info(
            "Downloads complete",
            notice_id=notice_id,
            successful=len(downloaded),
            total=len(attachments),
        )

        return downloaded


# =============================================================================
# Win Probability Scoring
# =============================================================================


class WinProbabilityScorer:
    """
    Calculate win probability based on various factors.

    Factors considered:
    - Qualification match score
    - Past performance relevance
    - NAICS code match
    - Set-aside eligibility
    - Geographic preference
    - Incumbent analysis (future)
    """

    @staticmethod
    async def calculate_score(
        rfp_data: dict[str, Any],
        user_profile: dict[str, Any],
        past_performance: list[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Calculate win probability score.

        Args:
            rfp_data: RFP information
            user_profile: User's qualification profile
            past_performance: List of past performance records

        Returns:
            Score breakdown and total
        """
        scores = {}
        weights = {
            "naics_match": 0.15,
            "set_aside_match": 0.20,
            "clearance_match": 0.15,
            "geographic_match": 0.10,
            "contract_value_fit": 0.10,
            "past_performance": 0.20,
            "deadline_feasibility": 0.10,
        }

        # NAICS Code Match (0-100)
        rfp_naics = rfp_data.get("naics_code", "")
        user_naics = user_profile.get("naics_codes", [])

        if rfp_naics in user_naics:
            scores["naics_match"] = 100
        elif rfp_naics and any(rfp_naics[:4] == n[:4] for n in user_naics):
            scores["naics_match"] = 70  # Same industry group
        elif rfp_naics and any(rfp_naics[:2] == n[:2] for n in user_naics):
            scores["naics_match"] = 40  # Same sector
        else:
            scores["naics_match"] = 20  # No match

        # Set-Aside Match (0-100)
        rfp_set_aside = (rfp_data.get("set_aside") or "").lower()
        user_set_asides = [s.lower() for s in user_profile.get("set_aside_types", [])]

        if not rfp_set_aside or rfp_set_aside in ["full and open", "none", ""]:
            scores["set_aside_match"] = 100  # Open competition
        elif any(sa in rfp_set_aside for sa in user_set_asides):
            scores["set_aside_match"] = 100
        else:
            scores["set_aside_match"] = 0  # Not eligible

        # Clearance Match (0-100)
        clearance_levels = {
            "none": 0,
            "public_trust": 1,
            "secret": 2,
            "top_secret": 3,
            "ts_sci": 4,
        }

        rfp_clearance = rfp_data.get("required_clearance", "none").lower()
        user_clearance = user_profile.get("clearance_level", "none").lower()

        rfp_level = clearance_levels.get(rfp_clearance, 0)
        user_level = clearance_levels.get(user_clearance, 0)

        if user_level >= rfp_level:
            scores["clearance_match"] = 100
        else:
            scores["clearance_match"] = 0

        # Geographic Match (0-100)
        rfp_location = (rfp_data.get("place_of_performance") or "").upper()
        user_states = [s.upper() for s in user_profile.get("preferred_states", [])]

        if not rfp_location or not user_states:
            scores["geographic_match"] = 80  # No preference
        elif any(state in rfp_location for state in user_states):
            scores["geographic_match"] = 100
        else:
            scores["geographic_match"] = 50  # Different location

        # Contract Value Fit (0-100)
        rfp_value = rfp_data.get("estimated_value", 0)
        min_value = user_profile.get("min_contract_value", 0)
        max_value = user_profile.get("max_contract_value", float("inf"))

        if not rfp_value:
            scores["contract_value_fit"] = 70  # Unknown
        elif min_value <= rfp_value <= max_value:
            scores["contract_value_fit"] = 100
        elif rfp_value < min_value:
            scores["contract_value_fit"] = 40  # Too small
        else:
            scores["contract_value_fit"] = 60  # Too large

        # Past Performance Score (0-100)
        if past_performance:
            # Calculate based on relevance and recency
            pp_scores = []
            for pp in past_performance[:5]:  # Top 5
                relevance = pp.get("relevance_score", 50)
                pp_scores.append(relevance)
            scores["past_performance"] = sum(pp_scores) / len(pp_scores) if pp_scores else 50
        else:
            scores["past_performance"] = 30  # No past performance

        # Deadline Feasibility (0-100)
        deadline = rfp_data.get("response_deadline")
        if deadline:
            if isinstance(deadline, str):
                deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))

            days_until = (deadline - datetime.utcnow()).days

            if days_until < 0:
                scores["deadline_feasibility"] = 0  # Past due
            elif days_until < 7:
                scores["deadline_feasibility"] = 40  # Very tight
            elif days_until < 14:
                scores["deadline_feasibility"] = 70  # Tight
            elif days_until < 30:
                scores["deadline_feasibility"] = 90  # Comfortable
            else:
                scores["deadline_feasibility"] = 100  # Plenty of time
        else:
            scores["deadline_feasibility"] = 70  # Unknown

        # Calculate weighted total
        total_score = sum(scores[key] * weights[key] for key in weights if key in scores)

        # Determine rating
        if total_score >= 80:
            rating = "High"
            recommendation = "Strong match - prioritize this opportunity"
        elif total_score >= 60:
            rating = "Medium"
            recommendation = "Good potential - review requirements carefully"
        elif total_score >= 40:
            rating = "Low"
            recommendation = "May be challenging - consider resource availability"
        else:
            rating = "Very Low"
            recommendation = "Poor fit - consider passing unless strategic"

        return {
            "total_score": round(total_score, 1),
            "rating": rating,
            "recommendation": recommendation,
            "breakdown": scores,
            "weights": weights,
        }


# Singleton instances
_downloader: RFPDownloader | None = None
_scorer: WinProbabilityScorer | None = None


def get_rfp_downloader() -> RFPDownloader:
    """Get or create RFP downloader singleton."""
    global _downloader
    if _downloader is None:
        _downloader = RFPDownloader()
    return _downloader


def get_win_scorer() -> WinProbabilityScorer:
    """Get or create win probability scorer singleton."""
    global _scorer
    if _scorer is None:
        _scorer = WinProbabilityScorer()
    return _scorer
