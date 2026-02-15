# Full Feature Verification Runbook (Priority Ordered)

Purpose: single checklist to verify all shipped frontend and backend capabilities before release.

Scope:
- Product surfaces in `frontend/src/app`
- API surfaces in `backend/app/api/routes`
- Enterprise trust/compliance controls, exports, and CI gates

Release rule:
- `P0` must be 100% green before release.
- `P1` must be 100% green for production release.
- `P2` can ship only with explicit accepted risk and dated follow-up tickets.
- `P3` is quality hardening and expansion; do not block hotfixes unless regressions are found.

---

## P0 - Security, Trust, Compliance, and Data Integrity

### P0.1 Auth/RBAC + Org Admin Security Controls
- Frontend: `/login`, `/register`, `/admin`
- Backend: `/api/v1/auth/*`, `/api/v1/admin/*`, `backend/app/api/deps.py`
- Verify:
  - [ ] Owner/admin/member/viewer access boundaries are enforced on protected routes.
  - [ ] Org member invitation lifecycle works end-to-end (invite, resend, revoke, activate).
  - [ ] Admin org security toggles persist and apply: step-up for sensitive exports/shares.
  - [ ] Unauthorized users get deterministic `401/403` (no `500`).

### P0.2 Step-Up MFA Challenge (Modal UX)
- Frontend: `/collaboration`, step-up modal components
- Backend: collaboration share/export policy enforcement in `backend/app/api/routes/collaboration/sharing.py` and export policy in `backend/app/api/routes/export.py`
- Verify:
  - [ ] Sensitive share/export returns `X-Step-Up-Required` when code missing/invalid.
  - [ ] Modal challenge opens, retries action with code, closes on success.
  - [ ] Success/failure audit events emitted (`security.step_up.challenge_succeeded/failed`).

### P0.3 Compliance Readiness (Evidence-Driven + Static Fallback)
- Frontend: `/compliance`, `/compliance/evidence-registry`
- Backend: `/api/v1/compliance/readiness-checkpoints*`, `/api/v1/compliance-registry/*`, `backend/app/services/compliance_readiness_service.py`
- Verify:
  - [ ] Checkpoint list returns dynamic evidence/signoff overlay fields.
  - [ ] No-evidence orgs still receive static fallback behavior.
  - [ ] Evidence link CRUD and signoff read/upsert work with correct RBAC.

### P0.4 Trust Center Exports + Signatures
- Frontend: `/compliance` trust export controls
- Backend: `/api/v1/compliance/trust-center/evidence-export`, `/api/v1/compliance/three-pao-package`, `backend/app/services/export_signing.py`
- Verify:
  - [ ] `format=json|csv|pdf` contract works; content-type/filename correct.
  - [ ] `signed=true` returns signature header (`X-Trust-Export-Signature`).
  - [ ] JSON/CSV succeed; PDF path fails gracefully if renderer deps unavailable.
  - [ ] Audit events log success only after payload generation succeeds.

### P0.5 CUI Policy Actions and Export Controls
- Frontend: `/admin` org policy flags; `/proposals/[proposalId]` export surfaces
- Backend: `/api/v1/export/proposals/{id}/compliance-package/zip`, `/api/v1/admin/organization`
- Verify:
  - [ ] Watermark/redaction flags persist per org.
  - [ ] CUI bundle manifest includes `policy_actions` and artifact targets.
  - [ ] Redaction coverage includes source trace, sections, and review packet artifacts.

### P0.6 Compliance Registry Org Scope Isolation
- Frontend: `/compliance/evidence-registry`
- Backend: `/api/v1/compliance-registry/controls`, `/api/v1/compliance-registry/evidence`
- Verify:
  - [ ] `scope=organization|mine` returns correct records.
  - [ ] Cross-org data does not leak.
  - [ ] Org admin/owner org-shared link/update paths are authorized and functioning.

### P0.7 Trust Telemetry and Auditability
- Frontend: `/compliance` metrics cards
- Backend: `/api/v1/compliance/trust-metrics`, audit events
- Verify:
  - [ ] Metrics compute and render: evidence completeness, signoff completion, export success, step-up success.
  - [ ] Export failure telemetry is emitted on generation exceptions.

### P0.8 CI Trust Lane Gate
- Frontend/Backend: CI workflow + trust suite script
- Backend: `.github/workflows/ci.yml`, `scripts/run_trust_ci_suite.sh`
- Verify:
  - [ ] Trust lane runs backend integration suites + frontend unit + trust Playwright.
  - [ ] Required env keys are set in CI (`SECRET_KEY`, `AUDIT_EXPORT_SIGNING_KEY`).
  - [ ] Merge blocked when trust lane fails.

---

## P1 - Core GovTech Proposal Workflow (Revenue-Critical)

### P1.1 Opportunities Ingest + Manual Fallback + Amendments
- Frontend: `/opportunities`, `/opportunities/[rfpId]`
- Backend: `/api/v1/ingest/sam`, `/api/v1/rfps/*`, snapshots/amendment-impact endpoints
- Verify:
  - [ ] SAM ingest success/failure surfaces actionable UI.
  - [ ] Manual Add RFP flow works when SAM is unavailable/rate-limited.
  - [ ] Snapshot diff + amendment impact map and remediation flow are functional.

### P1.2 Analysis Flow
- Frontend: `/analysis`, `/analysis/[rfpId]`
- Backend: `/api/v1/analyze/*`
- Verify:
  - [ ] Requirement extraction and matrix rendering work.
  - [ ] Upstream AI rate-limit errors surface detailed user feedback.

### P1.3 Draft/Proposal Authoring + Versioning
- Frontend: `/proposals`, `/proposals/[proposalId]`, `/proposals/[proposalId]/versions`
- Backend: `/api/v1/draft/*`, `/api/v1/versions/*`, `/api/v1/word-addin/*`
- Verify:
  - [ ] Create/update/regenerate sections works.
  - [ ] Track-changes suggestions persist correctly after rewrites.
  - [ ] Version history and section locking work.

### P1.4 Export Core Paths
- Frontend: proposal workspace export controls
- Backend: `/api/v1/export/*`
- Verify:
  - [ ] DOCX/XLSX/PDF (if deps available) exports complete.
  - [ ] Compliance evidence bundle export contains expected artifact set.

### P1.5 Reviews and Gate Packageing
- Frontend: `/reviews`
- Backend: `/api/v1/reviews/*`
- Verify:
  - [ ] Review packet generation includes risk-ranked queue + exit criteria.
  - [ ] Review assignment/commenting/checklist workflows remain stable.

### P1.6 Capture + Bid Decision + Scenario Simulator
- Frontend: `/capture`
- Backend: `/api/v1/capture/*`, `/api/v1/capture/scorecards/*`
- Verify:
  - [ ] Capture plans/gates/partners/competitors lifecycle works.
  - [ ] Scenario simulator returns calibrated recommendation deltas and rationale.

### P1.7 Teaming + Collaboration + Partner Portal
- Frontend: `/teaming`, `/collaboration`, `/collaboration/accept`, `/collaboration/portal/[workspaceId]`
- Backend: `/api/v1/teaming/*`, `/api/v1/collaboration/*`
- Verify:
  - [ ] Invite/accept/member role changes work for multiple users.
  - [ ] Preset sharing + governed approvals + portal filtering behave correctly.
  - [ ] Digest schedule/send + audit export + anomaly/governance metrics work.

### P1.8 Contracts + Revenue + Forecasts
- Frontend: `/contracts`, `/revenue`, `/forecasts`
- Backend: `/api/v1/contracts/*`, `/api/v1/revenue/*`, `/api/v1/forecasts/*`
- Verify:
  - [ ] Parent/child contracts + modifications + CLIN + tasks + deliverables + CPARS flows work.
  - [ ] Revenue rollups and forecast alerts are accurate and stable.

### P1.9 Knowledge Base + Contacts + Semantic Search
- Frontend: `/knowledge-base`, `/knowledge-base/past-performance`, `/contacts`, global search
- Backend: `/api/v1/documents/*`, `/api/v1/contacts/*`, `/api/v1/search/*`
- Verify:
  - [ ] Document ingest and past-performance flows work.
  - [ ] Contact extraction links to agencies/opportunities correctly.
  - [ ] Semantic search is tenant scoped and returns relevant results.

---

## P2 - Enterprise Integrations, Operations, and Analytics

### P2.1 Integrations Hub (SharePoint, Salesforce, Unanet, Webhooks, Secrets)
- Frontend: `/settings/integrations`, `/settings/integrations/word`
- Backend: `/api/v1/sharepoint*`, `/api/v1/salesforce/*`, `/api/v1/unanet/*`, `/api/v1/webhooks/*`, `/api/v1/secrets/*`
- Verify:
  - [ ] Provider config, sync, status, and secret rotation/deletion flows work.
  - [ ] Webhook CRUD/test delivery and secret lifecycle are deterministic.

### P2.2 Email Ingest + Routing + Sync Now
- Frontend: `/settings/email-ingest`, `/collaboration/inbox`
- Backend: `/api/v1/email-ingest/*`
- Verify:
  - [ ] Config create/update/list works with workspace routing.
  - [ ] Sync-now runs and updates history with confidence + attachment metadata.

### P2.3 Signals, Events, Intelligence
- Frontend: `/signals`, `/events`, `/intelligence`
- Backend: `/api/v1/signals/*`, `/api/v1/events/*`, `/api/v1/intelligence/*`, `/api/v1/kb-intelligence/*`
- Verify:
  - [ ] Ingest/rescore/digest and calendar/alerts flows work.
  - [ ] Intelligence KPIs and forecast views load correctly.

### P2.4 Analytics and Reports
- Frontend: `/analytics`, `/reports`
- Backend: `/api/v1/analytics/*`, `/api/v1/reports/*`, `/api/v1/activity/*`
- Verify:
  - [ ] Report builder, shared view, delivery schedule/send-now succeed.
  - [ ] Analytics ownership/route drift tests remain green.

### P2.5 Diagnostics + WebSocket Task Feed
- Frontend: `/diagnostics`
- Backend: `/api/v1/ws/*`
- Verify:
  - [ ] WebSocket connects and task feed updates in UI.
  - [ ] Diagnostics metrics (latency/reconnect/throughput) return and render.

### P2.6 Workflow Automation + Agents
- Frontend: `/settings/workflows`, `/agents`
- Backend: `/api/v1/workflows/*`, `/api/v1/agents/*`
- Verify:
  - [ ] Workflow rule execution triggers on expected events.
  - [ ] Agent catalog run actions execute and status is visible.

### P2.7 Notifications and Push
- Frontend: `/settings/notifications`
- Backend: `/api/v1/notifications/*`
- Verify:
  - [ ] Push subscription add/remove/list is functional.
  - [ ] Deadline/unread counters remain consistent.

---

## P3 - Surface Completeness, UX, and Adoption Features

### P3.1 Dash Assistant and Voice Controls
- Frontend: `/dash`
- Backend: `/api/v1/dash/*`
- Verify:
  - [ ] Chat, voice input, and speech toggle paths are stable.

### P3.2 Templates Marketplace + Help Center
- Frontend: `/templates`, `/help`
- Backend: `/api/v1/templates/*`, `/api/v1/support/*`
- Verify:
  - [ ] Template publish/rate/fork lifecycle works.
  - [ ] Help articles/tutorial/chat flows work.

### P3.3 Free-Tier and Subscription UX
- Frontend: `/free-tier`, `/settings/subscription`
- Backend: `/api/v1/subscription/*`
- Verify:
  - [ ] Limits and upgrade prompts are accurate and actionable.

### P3.4 Word Add-In Host Mode
- Frontend: `/word-addin`, `/word-addin/taskpane`
- Backend: `/api/v1/word-addin/*`
- Verify:
  - [ ] Browser-safe fallback works.
  - [ ] Office host pull/push workflow works in harness.

---

## Backend Capability Inventory (Record of Built API Domains)

Use this as a completion checklist; each line should have at least one integration test and one surfaced UI or explicit justification.

- [ ] auth (`backend/app/api/routes/auth.py`)
- [ ] onboarding (`backend/app/api/routes/onboarding.py`)
- [ ] admin (`backend/app/api/routes/admin/*`)
- [ ] agents (`backend/app/api/routes/agents.py`)
- [ ] analytics (`backend/app/api/routes/analytics.py`)
- [ ] analytics reporting (`backend/app/api/routes/analytics_reporting.py`)
- [ ] analyze (`backend/app/api/routes/analyze.py`)
- [ ] audit (`backend/app/api/routes/audit.py`)
- [ ] awards (`backend/app/api/routes/awards.py`)
- [ ] benchmark (`backend/app/api/routes/benchmark.py`)
- [ ] budget intel (`backend/app/api/routes/budget_intel.py`)
- [ ] capture core (`backend/app/api/routes/capture/*`)
- [ ] capture timeline (`backend/app/api/routes/capture_timeline.py`)
- [ ] collaboration core (`backend/app/api/routes/collaboration/*`)
- [ ] compliance dashboard (`backend/app/api/routes/compliance_dashboard.py`)
- [ ] compliance registry (`backend/app/api/routes/compliance_registry.py`)
- [ ] contacts (`backend/app/api/routes/contacts.py`)
- [ ] contracts (`backend/app/api/routes/contracts/*`)
- [ ] dash (`backend/app/api/routes/dash.py`)
- [ ] data sources (`backend/app/api/routes/data_sources.py`)
- [ ] documents (`backend/app/api/routes/documents.py`)
- [ ] draft generation (`backend/app/api/routes/draft/*`)
- [ ] email ingest (`backend/app/api/routes/email_ingest.py`)
- [ ] events (`backend/app/api/routes/events.py`)
- [ ] export (`backend/app/api/routes/export.py`)
- [ ] forecasts (`backend/app/api/routes/forecasts.py`)
- [ ] graphics (`backend/app/api/routes/graphics.py`)
- [ ] inbox (`backend/app/api/routes/inbox.py`)
- [ ] ingest (`backend/app/api/routes/ingest.py`)
- [ ] integrations (`backend/app/api/routes/integrations.py`)
- [ ] intelligence (`backend/app/api/routes/intelligence.py`)
- [ ] kb intelligence (`backend/app/api/routes/kb_intelligence.py`)
- [ ] notifications (`backend/app/api/routes/notifications.py`)
- [ ] reports (`backend/app/api/routes/reports.py`)
- [ ] revenue (`backend/app/api/routes/revenue.py`)
- [ ] reviews (`backend/app/api/routes/reviews.py`)
- [ ] rfps (`backend/app/api/routes/rfps.py`)
- [ ] salesforce (`backend/app/api/routes/salesforce.py`)
- [ ] saved searches (`backend/app/api/routes/saved_searches.py`)
- [ ] scim (`backend/app/api/routes/scim.py`)
- [ ] search (`backend/app/api/routes/search.py`)
- [ ] secrets (`backend/app/api/routes/secrets.py`)
- [ ] sharepoint (`backend/app/api/routes/sharepoint.py`)
- [ ] sharepoint sync (`backend/app/api/routes/sharepoint_sync.py`)
- [ ] signals (`backend/app/api/routes/signals.py`)
- [ ] subscription (`backend/app/api/routes/subscription.py`)
- [ ] support (`backend/app/api/routes/support.py`)
- [ ] teaming board (`backend/app/api/routes/teaming_board/*`)
- [ ] teams (`backend/app/api/routes/teams.py`)
- [ ] templates (`backend/app/api/routes/templates/*`)
- [ ] templates marketplace (`backend/app/api/routes/templates_marketplace.py`)
- [ ] unanet (`backend/app/api/routes/unanet.py`)
- [ ] versions (`backend/app/api/routes/versions.py`)
- [ ] webhooks (`backend/app/api/routes/webhooks.py`)
- [ ] websocket (`backend/app/api/routes/websocket.py`)
- [ ] word add-in (`backend/app/api/routes/word_addin.py`)
- [ ] workflows (`backend/app/api/routes/workflows.py`)

---

## Frontend Surface Inventory (Record of Built Routes)

- [ ] `/`
- [ ] `/free-tier`
- [ ] `/privacy`
- [ ] `/trust-center`
- [ ] `/word-addin`
- [ ] `/word-addin/taskpane`
- [ ] `/login`
- [ ] `/register`
- [ ] `/settings`
- [ ] `/settings/workflows`
- [ ] `/settings/email-ingest`
- [ ] `/settings/subscription`
- [ ] `/settings/integrations`
- [ ] `/settings/integrations/word`
- [ ] `/settings/data-sources`
- [ ] `/settings/notifications`
- [ ] `/collaboration`
- [ ] `/collaboration/accept`
- [ ] `/collaboration/inbox`
- [ ] `/collaboration/portal/[workspaceId]`
- [ ] `/pipeline`
- [ ] `/capture`
- [ ] `/opportunities`
- [ ] `/opportunities/[rfpId]`
- [ ] `/privacy/ai-data`
- [ ] `/analysis`
- [ ] `/analysis/[rfpId]`
- [ ] `/intelligence`
- [ ] `/contracts`
- [ ] `/contacts`
- [ ] `/signals`
- [ ] `/admin`
- [ ] `/agents`
- [ ] `/compliance`
- [ ] `/compliance/evidence-registry`
- [ ] `/compliance/timeline`
- [ ] `/teaming`
- [ ] `/knowledge-base`
- [ ] `/knowledge-base/past-performance`
- [ ] `/diagnostics`
- [ ] `/templates`
- [ ] `/dash`
- [ ] `/forecasts`
- [ ] `/events`
- [ ] `/revenue`
- [ ] `/onboarding`
- [ ] `/help`
- [ ] `/proposals`
- [ ] `/proposals/[proposalId]`
- [ ] `/proposals/[proposalId]/versions`
- [ ] `/analytics`
- [ ] `/reports`
- [ ] `/reviews`

---

## Final Production Sweep Commands

Run in this order, stop and fix on first failure.

1. Backend quality and tests
```bash
cd backend
ruff check .
ruff format --check .
pytest -q
```

2. Frontend quality and tests
```bash
cd frontend
npm run lint
npx vitest run
npm run build
```

3. Trust lane (must pass before merge)
```bash
cd /Users/demarioasquitt/Desktop/Projects/Entrepreneurial/govtech-sniper
RUN_TRUST_PLAYWRIGHT=true E2E_BASE_URL=http://127.0.0.1:3100 ./scripts/run_trust_ci_suite.sh
```

4. Optional full Playwright sweep
```bash
cd frontend
E2E_BASE_URL=http://127.0.0.1:3100 npx playwright test
```

---

## Latest Execution Evidence (2026-02-15)

- Backend regression: `295/295` passed (`cd backend && pytest -q`)
- Frontend lint: passed with warnings only (`cd frontend && npm run lint`)
- Frontend unit: `64/64` passed (`cd frontend && npx vitest run`)
- Frontend production build: passed (`cd frontend && npm run build`)
- Full Playwright sweep: `74/75` passed, `1` skipped optional path (`cd frontend && E2E_BASE_URL=http://127.0.0.1:3100 npx playwright test`)
- Trust lane: backend `42/42`, frontend trust unit `9/9`, trust Playwright `2/2` passed (`RUN_TRUST_PLAYWRIGHT=true E2E_BASE_URL=http://127.0.0.1:3100 ./scripts/run_trust_ci_suite.sh`)
