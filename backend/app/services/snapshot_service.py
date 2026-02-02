"""
RFP Sniper - Snapshot Helpers
==============================
Extract summaries and diffs from raw SAM.gov payloads.
"""

import hashlib
import json
from typing import Dict, Any, List, Optional

from app.schemas.rfp import SAMOpportunitySnapshotSummary, SAMOpportunityFieldChange


def _normalize_resource_links(resource_links: List[Any]) -> List[str]:
    normalized: List[str] = []
    for link in resource_links:
        if isinstance(link, str):
            if link:
                normalized.append(link)
        elif isinstance(link, dict):
            url = link.get("url") or link.get("name") or ""
            if url:
                normalized.append(url)
    return sorted(set(normalized))


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_snapshot_summary(raw_payload: Dict[str, Any]) -> SAMOpportunitySnapshotSummary:
    org_hierarchy = raw_payload.get("organizationHierarchy", []) or []
    agency = org_hierarchy[0].get("name") if org_hierarchy else None
    sub_agency = org_hierarchy[1].get("name") if len(org_hierarchy) > 1 else None

    description = raw_payload.get("description") or ""
    description_hash = _hash_text(description) if description else None

    resource_links = _normalize_resource_links(raw_payload.get("resourceLinks") or [])
    resource_links_hash = _hash_text(json.dumps(resource_links, sort_keys=True)) if resource_links else None

    return SAMOpportunitySnapshotSummary(
        notice_id=raw_payload.get("noticeId") or raw_payload.get("noticeID"),
        solicitation_number=raw_payload.get("solicitationNumber") or raw_payload.get("noticeId"),
        title=raw_payload.get("title"),
        posted_date=raw_payload.get("postedDate"),
        response_deadline=raw_payload.get("responseDeadLine"),
        agency=agency,
        sub_agency=sub_agency,
        naics_code=raw_payload.get("naicsCode"),
        set_aside=raw_payload.get("typeOfSetAsideDescription"),
        rfp_type=raw_payload.get("type"),
        ui_link=raw_payload.get("uiLink"),
        resource_links_count=len(resource_links),
        resource_links_hash=resource_links_hash,
        description_length=len(description),
        description_hash=description_hash,
    )


def diff_snapshot_summaries(
    before: SAMOpportunitySnapshotSummary,
    after: SAMOpportunitySnapshotSummary,
) -> List[SAMOpportunityFieldChange]:
    changes: List[SAMOpportunityFieldChange] = []
    fields = before.model_fields.keys()
    for field in fields:
        old_val = getattr(before, field)
        new_val = getattr(after, field)
        if old_val != new_val:
            changes.append(
                SAMOpportunityFieldChange(
                    field=field,
                    from_value=old_val,
                    to_value=new_val,
                )
            )
    return changes
