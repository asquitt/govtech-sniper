"""
FPDS ATOM Feed Provider
========================
Fetches contract award data from the Federal Procurement Data System (FPDS)
via its public ATOM feed.
"""

import httpx
import structlog
from defusedxml import ElementTree as ET

from app.services.data_providers.base import (
    DataSourceProvider,
    ProviderMaturity,
    RawOpportunity,
    SearchParams,
)

logger = structlog.get_logger(__name__)

FPDS_BASE_URL = "https://www.fpds.gov/ezsearch/LATEST"

# ATOM / FPDS namespaces
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "ns1": "https://www.fpds.gov/FPDS",
}


class FPDSProvider(DataSourceProvider):
    """Provider for FPDS contract award data via ATOM feed."""

    provider_name = "fpds"
    display_name = "FPDS"
    description = "Federal Procurement Data System — awarded contract records"
    is_active = True
    maturity = ProviderMaturity.HYBRID

    async def search(self, params: SearchParams) -> list[RawOpportunity]:
        query_parts: list[str] = []
        if params.keywords:
            query_parts.append(params.keywords)
        if params.naics_codes:
            for code in params.naics_codes:
                query_parts.append(f"NAICS:{code}")
        if params.agency:
            query_parts.append(f'AGENCY_NAME:"{params.agency}"')

        query_string = " ".join(query_parts) if query_parts else "LAST_MOD_DATE:[2024/01/01,]"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    FPDS_BASE_URL,
                    params={"s": "FPDS", "q": query_string, "feed": ""},
                )
                resp.raise_for_status()
                xml_text = resp.text
        except httpx.HTTPError as exc:
            logger.error("fpds.search failed", error=str(exc))
            return []

        return _parse_atom_feed(xml_text, params.limit)

    async def get_details(self, opportunity_id: str) -> RawOpportunity | None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    FPDS_BASE_URL,
                    params={"s": "FPDS", "q": f'PIID:"{opportunity_id}"', "feed": ""},
                )
                resp.raise_for_status()
                xml_text = resp.text
        except httpx.HTTPError as exc:
            logger.error("fpds.get_details failed", error=str(exc))
            return None

        results = _parse_atom_feed(xml_text, 1)
        return results[0] if results else None

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    FPDS_BASE_URL,
                    params={"s": "FPDS", "q": "LAST_MOD_DATE:[2024/01/01,]", "feed": ""},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _parse_atom_feed(xml_text: str, limit: int) -> list[RawOpportunity]:
    """Parse FPDS ATOM XML into RawOpportunity list."""
    results: list[RawOpportunity] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.error("fpds: XML parse error", error=str(exc))
        return []

    entries = root.findall("atom:entry", NS)
    for entry in entries[:limit]:
        title_el = entry.find("atom:title", NS)
        link_el = entry.find("atom:link", NS)

        # Dig into the FPDS content node for structured fields
        content = entry.find("atom:content", NS)
        award = None
        if content is not None:
            award = content.find("ns1:award", NS)

        external_id = ""
        agency_name = None
        naics_code = None
        description = None
        value = None
        posted_date = None

        if award is not None:
            award_id = award.find("ns1:awardID", NS)
            if award_id is not None:
                piid_el = award_id.find("ns1:awardContractID/ns1:PIID", NS)
                if piid_el is not None and piid_el.text:
                    external_id = piid_el.text

            contract_data = award.find("ns1:contractData", NS)
            if contract_data is not None:
                desc_el = contract_data.find("ns1:descriptionOfContractRequirement", NS)
                if desc_el is not None:
                    description = desc_el.text

            competition = award.find("ns1:competition", NS)
            if competition is not None:
                naics_el = competition.find("ns1:NAICSCode", NS)
                if naics_el is not None:
                    naics_code = naics_el.text

            dollar_values = award.find("ns1:dollarValues", NS)
            if dollar_values is not None:
                obligated = dollar_values.find("ns1:obligatedAmount", NS)
                if obligated is not None and obligated.text:
                    try:
                        value = float(obligated.text)
                    except ValueError:
                        pass

            relevant_dates = award.find("ns1:relevantContractDates", NS)
            if relevant_dates is not None:
                signed = relevant_dates.find("ns1:signedDate", NS)
                if signed is not None:
                    posted_date = signed.text

            purchasing_office = award.find("ns1:purchaserInformation", NS)
            if purchasing_office is not None:
                agency_el = purchasing_office.find("ns1:contractingOfficeAgencyID", NS)
                if agency_el is not None:
                    agency_name = agency_el.get("name") or agency_el.text

        if not external_id:
            id_el = entry.find("atom:id", NS)
            external_id = id_el.text if id_el is not None and id_el.text else "unknown"

        title_text = title_el.text if title_el is not None and title_el.text else "Untitled"
        source_url = link_el.get("href") if link_el is not None else None

        results.append(
            RawOpportunity(
                external_id=external_id,
                title=title_text,
                agency=agency_name,
                description=description,
                posted_date=posted_date,
                response_deadline=None,
                estimated_value=value,
                naics_code=naics_code,
                source_url=source_url,
                source_type="fpds",
                raw_data=None,  # Skip raw XML storage
            )
        )

    return results
