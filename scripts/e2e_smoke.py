#!/usr/bin/env python3
"""
E2E smoke test for RFP Sniper.

Assumes backend + worker are running and API keys are configured.
"""

import os
import sys
import time
import random
import string
from datetime import datetime, timezone

import httpx


def random_email(prefix: str = "e2e") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}-{suffix}@example.com"


def wait_for_status(fetch_fn, timeout_seconds: int = 300, interval: int = 3) -> dict:
    deadline = time.time() + timeout_seconds
    last = None
    while time.time() < deadline:
        last = fetch_fn()
        status = last.get("status")
        if status in {"completed", "failed"}:
            return last
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for task completion. Last status: {last}")


def wait_for_document(get_fn, timeout_seconds: int = 180, interval: int = 3) -> str:
    deadline = time.time() + timeout_seconds
    last_status = None
    while time.time() < deadline:
        doc = get_fn()
        last_status = doc.get("processing_status")
        if last_status in {"ready", "error"}:
            return last_status
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for document processing. Last status: {last_status}")


def main() -> int:
    base_url = os.getenv("RFP_API_URL", "http://localhost:8000")
    keywords = os.getenv("RFP_TEST_KEYWORDS", "software")
    password = os.getenv("RFP_TEST_PASSWORD", "TestPassword123!")
    email = os.getenv("RFP_TEST_EMAIL", random_email())
    skip_ingest = os.getenv("RFP_SKIP_SAM_INGEST", "").lower() in {"1", "true", "yes"}
    ingest_timeout = int(os.getenv("RFP_INGEST_TIMEOUT", "180"))

    print(f"Base URL: {base_url}")
    print(f"Test user: {email}")

    client = httpx.Client(timeout=60.0)

    # Register or login
    register_payload = {
        "email": email,
        "password": password,
        "full_name": "E2E Tester",
        "company_name": "E2E Co",
    }

    try:
        resp = client.post(f"{base_url}/api/v1/auth/register", json=register_payload)
        if resp.status_code == 201:
            tokens = resp.json()
            print("Registered new user.")
        elif resp.status_code == 400 and "already registered" in resp.text.lower():
            resp = client.post(
                f"{base_url}/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            resp.raise_for_status()
            tokens = resp.json()
            print("Logged in existing user.")
        else:
            resp.raise_for_status()
            tokens = resp.json()
    except Exception as exc:
        print(f"Auth failed: {exc}")
        return 1

    access_token = tokens["access_token"]
    client.headers.update({"Authorization": f"Bearer {access_token}"})

    def get_json(url: str):
        r = client.get(url)
        r.raise_for_status()
        return r.json()

    # Update profile (optional but helps filtering)
    profile_payload = {
        "naics_codes": ["541511"],
        "clearance_level": "none",
        "set_aside_types": [],
        "preferred_states": [],
    }
    client.put(f"{base_url}/api/v1/auth/profile", json=profile_payload)

    # Upload a small text document
    doc_text = (
        "E2E Capability Statement\n\n"
        "We provide software engineering, cloud migration, and DevOps services.\n"
        "Our team has delivered multiple federal projects with on-time performance.\n"
    )
    files = {
        "file": ("e2e-capability.txt", doc_text.encode("utf-8"), "text/plain"),
    }
    data = {
        "title": "E2E Capability Statement",
        "document_type": "capability_statement",
        "description": "E2E test document",
    }
    resp = client.post(f"{base_url}/api/v1/documents", files=files, data=data)
    resp.raise_for_status()
    document = resp.json()
    document_id = document["id"]
    print(f"Uploaded document {document_id}, waiting for processing...")

    def get_doc_status():
        r = client.get(f"{base_url}/api/v1/documents/{document_id}")
        r.raise_for_status()
        return r.json()

    doc_status = wait_for_document(get_doc_status, timeout_seconds=180, interval=3)
    if doc_status != "ready":
        print(f"Document processing failed: {doc_status}")
        return 1
    print("Document processed.")

    # Ingest SAM.gov opportunities
    ingest_ok = False
    if skip_ingest:
        print("Skipping SAM ingest (RFP_SKIP_SAM_INGEST set).")
    else:
        ingest_payload = {
            "keywords": keywords,
            "days_back": 7,
            "limit": 5,
        }
        try:
            resp = client.post(
                f"{base_url}/api/v1/ingest/sam",
                params={"apply_filter": False},
                json=ingest_payload,
            )
            resp.raise_for_status()
            ingest_task = resp.json()
            print(f"Ingest task queued: {ingest_task['task_id']}")

            try:
                ingest_status = wait_for_status(
                    lambda: get_json(
                        f"{base_url}/api/v1/ingest/sam/status/{ingest_task['task_id']}"
                    ),
                    timeout_seconds=ingest_timeout,
                    interval=5,
                )
                if ingest_status["status"] == "completed":
                    ingest_ok = True
                    print("Ingest complete.")
                else:
                    print(f"Ingest failed: {ingest_status}")
            except TimeoutError as exc:
                print(f"Ingest timed out after {ingest_timeout}s: {exc}")
        except Exception as exc:
            print(f"Ingest request failed: {exc}")

    # List RFPs and select one (fallback to manual creation if ingest returns none)
    resp = client.get(f"{base_url}/api/v1/rfps", params={"limit": 1})
    resp.raise_for_status()
    rfps = resp.json()
    if not rfps:
        print("No RFPs found after ingest. Creating a manual RFP for E2E...")
        now_utc = datetime.now(timezone.utc)
        manual_payload = {
            "title": "E2E Sample RFP",
            "solicitation_number": f"E2E-{now_utc.strftime('%Y%m%d%H%M%S')}",
            "agency": "Test Agency",
            "description": (
                "The contractor shall provide software development services. "
                "The proposal must include a technical approach, staffing plan, "
                "and past performance references."
            ),
        }
        resp = client.post(f"{base_url}/api/v1/rfps", json=manual_payload)
        resp.raise_for_status()
        rfp_id = resp.json()["id"]
    else:
        rfp_id = rfps[0]["id"]
    print(f"Selected RFP {rfp_id}")

    # Trigger analysis
    resp = client.post(f"{base_url}/api/v1/analyze/{rfp_id}")
    resp.raise_for_status()
    analysis_task = resp.json()
    if analysis_task.get("status") == "already_completed":
        print("RFP already analyzed.")
    else:
        analysis_status = wait_for_status(
            lambda: get_json(
                f"{base_url}/api/v1/analyze/{rfp_id}/status/{analysis_task['task_id']}"
            ),
            timeout_seconds=600,
            interval=5,
        )
        if analysis_status["status"] != "completed":
            print(f"Analysis failed: {analysis_status}")
            return 1
        print("Analysis complete.")

    # Fetch compliance matrix
    resp = client.get(f"{base_url}/api/v1/analyze/{rfp_id}/matrix")
    resp.raise_for_status()
    matrix = resp.json()
    requirements = matrix.get("requirements", [])
    if not requirements:
        print("No requirements found in compliance matrix.")
        return 1
    requirement_id = requirements[0]["id"]
    print(f"Using requirement {requirement_id}")

    # Create proposal + sections
    resp = client.post(
        f"{base_url}/api/v1/draft/proposals",
        json={"rfp_id": rfp_id, "title": f"E2E Proposal {datetime.now(timezone.utc).isoformat()}"},
    )
    resp.raise_for_status()
    proposal = resp.json()
    proposal_id = proposal["id"]
    print(f"Created proposal {proposal_id}")

    resp = client.post(
        f"{base_url}/api/v1/draft/proposals/{proposal_id}/generate-from-matrix"
    )
    resp.raise_for_status()

    # Generate one section
    resp = client.post(
        f"{base_url}/api/v1/draft/{requirement_id}",
        json={"requirement_id": requirement_id},
    )
    resp.raise_for_status()
    gen_task = resp.json()
    gen_status = wait_for_status(
        lambda: get_json(f"{base_url}/api/v1/draft/{gen_task['task_id']}/status"),
        timeout_seconds=600,
        interval=5,
    )
    if gen_status["status"] != "completed":
        print(f"Draft generation failed: {gen_status}")
        return 1
    print("Draft generation complete.")

    # Create Word add-in session + event
    resp = client.post(
        f"{base_url}/api/v1/word-addin/sessions",
        json={"proposal_id": proposal_id, "document_name": "E2E Draft.docx"},
    )
    resp.raise_for_status()
    word_session_id = resp.json()["id"]
    resp = client.post(
        f"{base_url}/api/v1/word-addin/sessions/{word_session_id}/events",
        json={"event_type": "sync", "payload": {"sections": len(requirements)}},
    )
    resp.raise_for_status()
    print("Word add-in session synced.")

    # Create graphics request
    resp = client.post(
        f"{base_url}/api/v1/graphics",
        json={
            "proposal_id": proposal_id,
            "title": "E2E Cover Graphic",
            "description": "Cover page visual for E2E run.",
        },
    )
    resp.raise_for_status()
    print("Graphics request created.")

    # Export DOCX
    resp = client.get(f"{base_url}/api/v1/export/proposals/{proposal_id}/docx")
    if resp.status_code != 200:
        print(f"DOCX export failed: {resp.status_code} {resp.text}")
        return 1
    print("DOCX export succeeded.")

    print("E2E smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
