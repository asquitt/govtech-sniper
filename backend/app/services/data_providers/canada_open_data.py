"""
CanadaBuys Open Data Helpers
============================
Shared utilities for Canada procurement providers backed by CanadaBuys CSV feeds.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from io import StringIO
from typing import Any

import httpx

from app.services.data_providers.base import RawOpportunity, SearchParams

OPEN_TENDERS_CSV_URL = (
    "https://canadabuys.canada.ca/opendata/pub/openTenderNotice-ouvertAvisAppelOffres.csv"
)

_PROVINCIAL_PORTAL_URLS: dict[str, str] = {
    "AB": "https://www.purchasingconnection.ca/",
    "BC": "https://www2.gov.bc.ca/gov/content/bc-procurement-resources/bc-bid-resources",
    "MB": "http://www.gov.mb.ca/tenders",
    "NB": "https://nbon-rpanb.gnb.ca/",
    "NL": "https://www.gov.nl.ca/ppa/",
    "NS": "https://www.novascotia.ca/find-public-tender-notices",
    "NT": "http://contracts.fin.gov.nt.ca/",
    "NU": "https://www.nunavuttenders.ca/",
    "ON": "https://ontariotenders.bravosolution.com/",
    "PE": "https://www.princeedwardisland.ca/tenders",
    "QC": "https://seao.gouv.qc.ca/avis-du-jour",
    "SK": "http://sasktenders.ca/",
    "YT": "https://yukon.ca/en/bid-on-government-contract#create-a-free-account",
}

_PROVINCE_NORMALIZATION: dict[str, str] = {
    "AB": "AB",
    "ALBERTA": "AB",
    "BC": "BC",
    "BRITISH COLUMBIA": "BC",
    "MB": "MB",
    "MANITOBA": "MB",
    "NB": "NB",
    "NEW BRUNSWICK": "NB",
    "NL": "NL",
    "NEWFOUNDLAND AND LABRADOR": "NL",
    "NS": "NS",
    "NOVA SCOTIA": "NS",
    "NT": "NT",
    "NORTHWEST TERRITORIES": "NT",
    "NU": "NU",
    "NUNAVUT": "NU",
    "ON": "ON",
    "ONTARIO": "ON",
    "PE": "PE",
    "PEI": "PE",
    "PRINCE EDWARD ISLAND": "PE",
    "QC": "QC",
    "QUEBEC": "QC",
    "QUÉBEC": "QC",
    "SK": "SK",
    "SASKATCHEWAN": "SK",
    "YT": "YT",
    "YUKON": "YT",
}

_TITLE_EN = "title-titre-eng"
_TITLE_FR = "title-titre-fra"
_REFERENCE = "referenceNumber-numeroReference"
_SOLICITATION = "solicitationNumber-numeroSollicitation"
_PUBLICATION_DATE = "publicationDate-datePublication"
_CLOSING_DATE = "tenderClosingDate-appelOffresDateCloture"
_STATUS_EN = "tenderStatus-appelOffresStatut-eng"
_GSIN = "gsin-nibs"
_UNSPSC = "unspsc"
_CONTRACTING_ENTITY_EN = "contractingEntityName-nomEntitContractante-eng"
_CONTRACTING_PROVINCE_EN = "contractingEntityAddressProvince-entiteContractanteAdresseProvince-eng"
_NOTICE_URL_EN = "noticeURL-URLavis-eng"
_DESCRIPTION_EN = "tenderDescription-descriptionAppelOffres-eng"
_REGIONS_OPP_EN = "regionsOfOpportunity-regionAppelOffres-eng"
_REGIONS_DELIVERY_EN = "regionsOfDelivery-regionsLivraison-eng"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is not None:
            return parsed.replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def _normalize_region_token(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip().upper().replace(".", "").replace("  ", " ")
    if token in _PROVINCE_NORMALIZATION:
        return _PROVINCE_NORMALIZATION[token]
    return None


def _extract_region_codes(row: dict[str, str]) -> list[str]:
    values = [
        row.get(_CONTRACTING_PROVINCE_EN),
        row.get(_REGIONS_OPP_EN),
        row.get(_REGIONS_DELIVERY_EN),
    ]
    discovered: list[str] = []
    for value in values:
        if not value:
            continue
        tokens = [
            token.strip()
            for token in value.replace("/", ",").replace(";", ",").split(",")
            if token.strip()
        ]
        for token in tokens:
            normalized = _normalize_region_token(token)
            if normalized and normalized not in discovered:
                discovered.append(normalized)
    return discovered


def _normalize_naics_codes(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    normalized: set[str] = set()
    for value in values:
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            normalized.add(digits)
    return normalized


def _matches_filters(
    row: dict[str, str],
    params: SearchParams,
    *,
    provincial_only: bool,
) -> bool:
    if provincial_only and not _extract_region_codes(row):
        return False

    status = (row.get(_STATUS_EN) or "").strip().lower()
    if status and status not in {"open", "active"}:
        return False

    published_at = _parse_datetime(row.get(_PUBLICATION_DATE))
    if published_at and params.days_back > 0:
        cutoff = datetime.utcnow() - timedelta(days=params.days_back)
        if published_at < cutoff:
            return False

    title = row.get(_TITLE_EN) or row.get(_TITLE_FR) or ""
    description = row.get(_DESCRIPTION_EN) or ""
    agency = row.get(_CONTRACTING_ENTITY_EN) or ""

    if params.keywords:
        keyword = params.keywords.strip().lower()
        text_blob = " ".join([title, description, agency]).lower()
        if keyword not in text_blob:
            return False

    if params.agency:
        agency_keyword = params.agency.strip().lower()
        if agency_keyword not in agency.lower():
            return False

    desired_codes = _normalize_naics_codes(params.naics_codes)
    if desired_codes:
        gsin = "".join(ch for ch in (row.get(_GSIN) or "") if ch.isdigit())
        unspsc = "".join(ch for ch in (row.get(_UNSPSC) or "") if ch.isdigit())
        if not any(code in gsin or code in unspsc for code in desired_codes):
            return False

    return True


def _build_external_id(row: dict[str, str]) -> str:
    reference = (row.get(_REFERENCE) or "").strip()
    solicitation = (row.get(_SOLICITATION) or "").strip()
    base = reference or solicitation or f"CAN-{abs(hash(str(row))) % 10_000_000}"
    return f"CA-{base}"


def _build_source_url(row: dict[str, str], external_id: str) -> str:
    source_url = (row.get(_NOTICE_URL_EN) or "").strip()
    if source_url:
        return source_url
    notice_key = external_id.removeprefix("CA-")
    return f"https://canadabuys.canada.ca/en/tender-opportunities?tender={notice_key}"


def row_to_opportunity(
    row: dict[str, str],
    *,
    source_type: str,
    include_portal_metadata: bool,
) -> RawOpportunity:
    external_id = _build_external_id(row)
    region_codes = _extract_region_codes(row)
    primary_region = region_codes[0] if region_codes else None

    raw_data: dict[str, Any] = dict(row)
    if include_portal_metadata and region_codes:
        raw_data["provincial_portal_urls"] = {
            code: _PROVINCIAL_PORTAL_URLS.get(code)
            for code in region_codes
            if code in _PROVINCIAL_PORTAL_URLS
        }

    return RawOpportunity(
        external_id=external_id,
        title=(row.get(_TITLE_EN) or row.get(_TITLE_FR) or "Untitled").strip()[:500],
        agency=(row.get(_CONTRACTING_ENTITY_EN) or "Government of Canada").strip()[:255],
        description=(row.get(_DESCRIPTION_EN) or None),
        posted_date=row.get(_PUBLICATION_DATE),
        response_deadline=row.get(_CLOSING_DATE),
        estimated_value=None,
        currency="CAD",
        jurisdiction=f"CA-{primary_region}" if primary_region else "CA",
        naics_code=(row.get(_GSIN) or row.get(_UNSPSC) or None),
        source_url=_build_source_url(row, external_id),
        source_type=source_type,
        raw_data=raw_data,
    )


def _iter_csv_rows(csv_text: str) -> list[dict[str, str]]:
    normalized = csv_text.lstrip("\ufeff")
    reader = csv.DictReader(StringIO(normalized))
    return [{k: (v or "") for k, v in row.items()} for row in reader]


async def fetch_canadabuys_rows(
    *,
    params: SearchParams,
    provincial_only: bool = False,
) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.get(OPEN_TENDERS_CSV_URL)
        resp.raise_for_status()
        csv_text = resp.text

    rows = _iter_csv_rows(csv_text)
    matched: list[dict[str, str]] = []
    for row in rows:
        if not _matches_filters(row, params, provincial_only=provincial_only):
            continue
        matched.append(row)
        if len(matched) >= params.limit:
            break
    return matched
