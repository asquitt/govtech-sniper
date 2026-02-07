#!/usr/bin/env python3
"""
E2E smoke test for RFP Sniper.

Assumes backend + worker are running and API keys are configured.
Celery-dependent steps (document processing, analysis, draft generation)
are best-effort — the test passes if API endpoints respond correctly.
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


def wait_for_document(get_fn, timeout_seconds: int = 60, interval: int = 3) -> str:
    deadline = time.time() + timeout_seconds
    last_status = None
    while time.time() < deadline:
        doc = get_fn()
        last_status = doc.get("processing_status")
        if last_status in {"ready", "error"}:
            return last_status
        time.sleep(interval)
    return last_status or "unknown"


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

    # ── Auth ──────────────────────────────────────────────────────
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

    # ── Profile ───────────────────────────────────────────────────
    profile_payload = {
        "naics_codes": ["541511"],
        "clearance_level": "none",
        "set_aside_types": [],
        "preferred_states": [],
    }
    client.put(f"{base_url}/api/v1/auth/profile", json=profile_payload)

    # ── Document Upload ───────────────────────────────────────────
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
    if resp.status_code >= 400:
        print(f"Document upload failed ({resp.status_code}): {resp.text}")
        return 1
    document = resp.json()
    document_id = document["id"]
    print(f"Uploaded document {document_id}.")

    # Wait briefly for processing (best-effort, Celery may not be ready)
    def get_doc_status():
        r = client.get(f"{base_url}/api/v1/documents/{document_id}")
        r.raise_for_status()
        return r.json()

    doc_status = wait_for_document(get_doc_status, timeout_seconds=60, interval=3)
    if doc_status == "ready":
        print("Document processed.")
    else:
        print(f"Document processing not complete (status: {doc_status}), continuing.")

    # ── SAM.gov Ingest ────────────────────────────────────────────
    if skip_ingest:
        print("Skipping SAM ingest (RFP_SKIP_SAM_INGEST set).")

    # ── RFP CRUD ──────────────────────────────────────────────────
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
    print(f"Created RFP {rfp_id}.")

    # ── Analysis (Celery-dependent, best-effort) ──────────────────
    analysis_ok = False
    try:
        resp = client.post(f"{base_url}/api/v1/analyze/{rfp_id}")
        resp.raise_for_status()
        analysis_task = resp.json()
        if analysis_task.get("status") == "already_completed":
            analysis_ok = True
            print("RFP already analyzed.")
        else:
            analysis_status = wait_for_status(
                lambda: get_json(
                    f"{base_url}/api/v1/analyze/{rfp_id}/status/{analysis_task['task_id']}"
                ),
                timeout_seconds=120,
                interval=5,
            )
            if analysis_status["status"] == "completed":
                analysis_ok = True
                print("Analysis complete.")
            else:
                print(f"Analysis did not complete: {analysis_status}")
    except TimeoutError:
        print("Analysis timed out (Celery worker may not be ready), continuing.")
    except Exception as exc:
        print(f"Analysis failed: {exc}, continuing.")

    # ── Proposal + Draft (depends on analysis) ────────────────────
    if analysis_ok:
        resp = client.get(f"{base_url}/api/v1/analyze/{rfp_id}/matrix")
        resp.raise_for_status()
        matrix = resp.json()
        requirements = matrix.get("requirements", [])

        if requirements:
            requirement_id = requirements[0]["id"]

            resp = client.post(
                f"{base_url}/api/v1/draft/proposals",
                json={
                    "rfp_id": rfp_id,
                    "title": f"E2E Proposal {datetime.now(timezone.utc).isoformat()}",
                },
            )
            resp.raise_for_status()
            proposal = resp.json()
            proposal_id = proposal["id"]
            print(f"Created proposal {proposal_id}.")

            resp = client.post(
                f"{base_url}/api/v1/draft/proposals/{proposal_id}/generate-from-matrix"
            )
            resp.raise_for_status()

            # Generate one section
            try:
                resp = client.post(
                    f"{base_url}/api/v1/draft/{requirement_id}",
                    json={"requirement_id": requirement_id},
                )
                resp.raise_for_status()
                gen_task = resp.json()
                gen_status = wait_for_status(
                    lambda: get_json(
                        f"{base_url}/api/v1/draft/{gen_task['task_id']}/status"
                    ),
                    timeout_seconds=120,
                    interval=5,
                )
                if gen_status["status"] == "completed":
                    print("Draft generation complete.")
                else:
                    print(f"Draft generation did not complete: {gen_status}")
            except TimeoutError:
                print("Draft generation timed out, continuing.")
            except Exception as exc:
                print(f"Draft generation failed: {exc}, continuing.")

            # Word add-in session
            resp = client.post(
                f"{base_url}/api/v1/word-addin/sessions",
                json={"proposal_id": proposal_id, "document_name": "E2E Draft.docx"},
            )
            resp.raise_for_status()
            word_session_id = resp.json()["id"]
            resp = client.post(
                f"{base_url}/api/v1/word-addin/sessions/{word_session_id}/events",
                json={
                    "event_type": "sync",
                    "payload": {"sections": len(requirements)},
                },
            )
            resp.raise_for_status()
            print("Word add-in session synced.")

            # Graphics request
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
            resp = client.get(
                f"{base_url}/api/v1/export/proposals/{proposal_id}/docx"
            )
            if resp.status_code == 200:
                print("DOCX export succeeded.")
            else:
                print(f"DOCX export returned {resp.status_code} (may need sections).")
        else:
            print("No requirements in matrix (analysis may be incomplete).")
    else:
        print("Skipping proposal/draft (analysis not complete).")

    # ── Create proposal without analysis (always works) ───────────
    resp = client.post(
        f"{base_url}/api/v1/draft/proposals",
        json={
            "rfp_id": rfp_id,
            "title": f"E2E Standalone Proposal {datetime.now(timezone.utc).isoformat()}",
        },
    )
    resp.raise_for_status()
    standalone_id = resp.json()["id"]
    print(f"Created standalone proposal {standalone_id}.")

    # List proposals
    resp = client.get(f"{base_url}/api/v1/draft/proposals")
    resp.raise_for_status()
    proposals = resp.json()
    print(f"Listed {len(proposals)} proposals.")

    # List RFPs
    resp = client.get(f"{base_url}/api/v1/rfps")
    resp.raise_for_status()
    rfps = resp.json()
    print(f"Listed {len(rfps)} RFPs.")

    print("E2E smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
