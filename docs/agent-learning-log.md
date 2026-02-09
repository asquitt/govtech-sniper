# Agent Learning Log

Purpose: keep a persistent, project-local record of recurring agent mistakes and the guardrails that prevent repeats.

Update rule:
- Append a new entry whenever a mistake is found in implementation, testing, or delivery.
- Keep entries concrete and tied to an observable failure.
- Include the prevention rule that should be applied in future sessions.

Format:
- Date:
- Mistake:
- Root cause:
- Prevention checklist:
- Verification added:

## Entries

### 2026-02-09
- Date: 2026-02-09
- Mistake: Frontend registration accepted passwords that backend rejected.
- Root cause: Frontend password checklist drifted from backend validation policy.
- Prevention checklist: Mirror backend password constraints in frontend UI requirements and test assertions.
- Verification added: Updated auth E2E to assert special-character requirement visibility.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Draft generation depended on Celery/Redis in local runs and failed with service unavailable.
- Root cause: No synchronous fallback path for local/mock environments.
- Prevention checklist: For critical flows, add local synchronous fallback when broker is unavailable and mock mode/debug is active.
- Verification added: Backend tests for sync draft fallback and generation status behavior.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Analysis export used `rfp.id` where export endpoints require `proposal_id`.
- Root cause: Identifier mismatch across adjacent features.
- Prevention checklist: Verify endpoint identifier contracts before wiring UI actions; confirm by exercising flow in browser.
- Verification added: Live critical-path Playwright validation after patch.

### 2026-02-09
- Date: 2026-02-09
- Mistake: New Playwright E2E used brittle selectors and failed due to strict mode collisions.
- Root cause: Selector matched multiple controls with similar labels.
- Prevention checklist: Prefer scoped and exact role selectors in E2E tests; validate by rerunning full spec set.
- Verification added: Updated critical-path E2E selectors and re-ran auth + critical specs.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Compliance requirement approval endpoint returned 500 during live UI flow.
- Root cause: Async route accessed `matrix.rfp` lazy relationship, triggering `MissingGreenlet` in audit/webhook logging.
- Prevention checklist: In async routes, never depend on lazy relationship IO; query required IDs explicitly before logging/events.
- Verification added: Added regression in `backend/tests/test_analysis.py` with `db_session.expunge_all()` before update/delete.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Analysis page hid valid manually-added requirements for `new` RFPs after a UI-side optimization.
- Root cause: Frontend gated matrix fetch by RFP status instead of data availability.
- Prevention checklist: Base UI fetch guards on backend data contracts, not inferred status heuristics.
- Verification added: Backend `GET /analyze/{rfp_id}/matrix` now returns empty matrix shape when missing; live reload verified matrix visibility after manual add.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Local mock ingest/draft flows could hang when Redis was reachable but no Celery worker was connected.
- Root cause: Fallback checks only probed broker reachability, not active worker availability.
- Prevention checklist: For async task fallbacks, validate both broker and worker health before queuing in debug/mock mode.
- Verification added: Added ingest + draft regression tests for "worker unavailable" fallback and re-ran Playwright critical path.
