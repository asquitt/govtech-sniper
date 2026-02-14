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

### 2026-02-09
- Date: 2026-02-09
- Mistake: Admin and reports endpoints returned 500 because route handlers used `session.exec(...)` with `AsyncSession`.
- Root cause: Mixed SQLModel session API assumptions with SQLAlchemy `AsyncSession` in runtime dependencies.
- Prevention checklist: In async API routes, always use `session.execute(...)` and map results with `.scalar*()`/`.scalars()`; add endpoint-level tests for new admin/report routes.
- Verification added: Added regression coverage in `backend/tests/test_capability_integrations.py` and validated `/api/v1/reports` plus `/api/v1/admin/*` behavior.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Analytics and intelligence pages failed in local SQLite runs because queries used Postgres-only SQL functions (`to_char`, `extract`).
- Root cause: Dialect-specific expressions were shipped without SQLite compatibility fallback for local/mock environments.
- Prevention checklist: For date/time aggregation, implement dialect-aware helpers (`strftime`/`julianday` for SQLite, `to_char`/`extract` for Postgres) before wiring UI.
- Verification added: Added and passed regression tests for `/api/v1/analytics/win-rate`, `/api/v1/analytics/proposal-turnaround`, and `/api/v1/intelligence/budget`.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Contracts page attempted cross-origin fetches after a proxy rewrite chain (`/api/contracts` -> backend 307 redirect) leaked backend URL to browser.
- Root cause: Trailing-slash mismatch between Next rewrite and FastAPI root route produced redirect responses instead of proxied 200 responses.
- Prevention checklist: For proxied root endpoints, validate both slash and non-slash paths and add explicit rewrite exceptions when backend normalizes paths.
- Verification added: Added `/api/contracts` explicit rewrite and verified live Playwright/API status 200 without CORS failure.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Initial Playwright run produced a full false-negative failure set because it targeted the wrong base URL (`localhost:3000` instead of active `localhost:3100`).
- Root cause: Test harness default base URL differed from the live dev server used in this session.
- Prevention checklist: Before interpreting E2E failures, confirm target base URL and backend pair (`E2E_BASE_URL` + API origin) match active servers.
- Verification added: Re-ran full Playwright suite with `E2E_BASE_URL=http://localhost:3100` and confirmed 27/27 passing.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Frontend API contracts drifted from backend routes (`/templates/categories/list` and `/notifications/deadlines`), leaving latent 404 paths.
- Root cause: Client helper methods persisted older endpoint shapes without a contract validation sweep.
- Prevention checklist: Run method-aware frontend API path scans against live proxy and close every 404 mismatch with route updates or compatibility aliases.
- Verification added: Updated templates client path, added templates legacy alias route, implemented notifications deadlines route, and added backend regression tests.

### 2026-02-09
- Date: 2026-02-09
- Mistake: Word add-in taskpane loaded Office runtime unconditionally in plain browser mode, causing runtime warnings and failed external telemetry calls.
- Root cause: No host-awareness gate around Office.js loading for non-Office environments.
- Prevention checklist: Gate Office runtime script loading to likely Office hosts and keep browser-safe fallback path tested.
- Verification added: Added Office host detection + gated loader, validated no mount warning/telemetry failures in Playwright taskpane check, and added frontend unit tests.

### 2026-02-10
- Date: 2026-02-10
- Mistake: New Playwright workflow specs initially failed due strict-mode selector collisions on duplicated labels/text (`Title`, `RED Team`, `Search`, partner names in option + list rows).
- Root cause: Selectors were not scoped to the relevant card/element type before assertions and actions.
- Prevention checklist: Scope E2E selectors to container cards/sections and use `exact` role/name matching when shared UI labels exist.
- Verification added: Updated selectors across capture/contracts/teaming/reviews workflow specs; reran targeted workflow specs and full Playwright suite (`34/34` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Reports generate/export endpoints returned `500` due incorrect auth attribute access (`UserAuth.user_id`).
- Root cause: Route ownership helper used a non-existent `UserAuth` field instead of canonical `id`.
- Prevention checklist: For every auth-dependent route helper, validate `UserAuth` field usage (`id`, `email`, `tier`) and add endpoint-level contract tests for non-list actions (`generate`, `export`, etc.).
- Verification added: Fixed `backend/app/api/routes/reports.py` to use `user.id`, added regression coverage in `backend/tests/test_business_capabilities.py`, and validated via Playwright reports workflow + full suite (`42/42` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Admin bootstrap E2E and several dashboard assertions intermittently failed due premature visibility checks and ambiguous text matches in dense cards.
- Root cause: Tests assumed a single visible state immediately after navigation and used text selectors that matched UI labels, legends, and options simultaneously.
- Prevention checklist: In stateful pages, wait for either expected state branch before branching assertions; prefer scoped locator chains and exact matches for labels reused in charts/forms.
- Verification added: Updated admin/revenue/analytics/settings/capture workflow specs with state-aware waits and strict selectors; reran targeted workflows and full Playwright regression (`42/42` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Full Playwright regression still failed once on capture workflow after adding more seeded data because `Plan Active` assertion matched multiple cards.
- Root cause: Selector update was applied to new workflows but not consistently backported to all existing specs that share repeated badge text.
- Prevention checklist: After adding new seeded-flow coverage, rerun and harden all pre-existing specs that rely on shared labels by using scoped `.first()` or exact role/name selectors.
- Verification added: Updated `capture-workflow.spec.ts` selector scope and reran full Playwright suite (`44/44` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: New diagnostics Playwright step failed because `Lock Section` selector also matched `Unlock Section` under strict mode.
- Root cause: Test used non-exact role-name matching on two similarly named controls in the same probe card.
- Prevention checklist: For button labels that are substrings of other labels, enforce `exact: true` and/or scope locators to a specific container.
- Verification added: Updated diagnostics spec to exact lock selector and reran targeted + full Playwright suites (`46/46` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Proposal workspace E2E surfaced a runtime error from TipTap SSR hydration handling.
- Root cause: `RichTextEditor` initialized TipTap without `immediatelyRender: false`, triggering client-side runtime errors in dynamic workspace rendering.
- Prevention checklist: For TipTap in Next.js client components, set `immediatelyRender: false` and include at least one dynamic-route browser validation for editor-mounted pages.
- Verification added: Patched `rich-text-editor.tsx`, added proposal-editor deep workflow coverage, and reran full Playwright suite (`46/46` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Auth and Dash E2E checks failed after introducing `next`-query redirects and context-dependent quick-action prompts.
- Root cause: Tests asserted exact `/login` URLs and fixed quick-action labels instead of validating behavior across supported state variants.
- Prevention checklist: When adding redirect parameters or context-aware UI content, update E2E assertions to allow query-bearing URLs and verify structural outcomes (route pattern + control count) instead of brittle literal text.
- Verification added: Updated `auth.spec.ts` URL matchers and `dash.spec.ts` prompt-card assertions; reran targeted specs and full Playwright regression (`46/46` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Contract hierarchy/modification/CLIN capabilities existed in pieces but remained marked open in roadmap/docs and lacked explicit lifecycle regression coverage.
- Root cause: Capability rollout was not closed with synchronized documentation updates plus backend/UI/E2E assertions for the same feature slice.
- Prevention checklist: For each closed roadmap item, require same-session updates to roadmap status + capability trackers + backend integration test + frontend unit assertion + Playwright workflow evidence.
- Verification added: Expanded `test_contracts.py`, added hierarchy assertions in `contracts-page.test.tsx`, updated `contracts-workflow.spec.ts`, and updated roadmap/tracker/surface documents.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Collaboration contract-feed E2E assertion failed under Playwright strict mode because feed text matched both dropdown options and helper description copy.
- Root cause: Assertion targeted global text instead of a scoped shared-item container in a view with repeated labels.
- Prevention checklist: For list workflows, add stable row-level `data-testid` hooks and assert within scoped containers instead of global `getByText` when option labels repeat in form controls.
- Verification added: Added `data-testid` to shared-data rows, updated `collaboration-workflow.spec.ts` to assert on scoped shared-item rows, and reran targeted collaboration Playwright workflow (passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Multi-context collaboration E2E initially asserted partner-portal content in a context/state branch that occasionally remained on the workspace dashboard, producing a false failure.
- Root cause: Assertion depended on collaborator context navigation sequencing instead of validating the portal-switch behavior in a deterministic portal context.
- Prevention checklist: For multi-user workflows, keep context-sensitive assertions scoped to the actor/session that deterministically owns the route state; validate shared outcomes with explicit route checks before content checks.
- Verification added: Updated collaboration E2E to validate portal switching from the owner portal context after invite acceptance flow completion; reran targeted collaboration + contracts Playwright specs (passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Collaboration share-policy rollout produced a live `500` during Playwright because partner-membership validation used `scalar_one_or_none()` and crashed when duplicate membership rows existed.
- Root cause: Membership checks assumed uniqueness at query-time but the table lacks a DB-level uniqueness guarantee, so duplicate rows surfaced as an unhandled ORM exception path.
- Prevention checklist: For membership/lookup guards on mutable relationship tables, avoid `scalar_one_or_none()` unless a DB unique constraint is guaranteed; use duplicate-safe lookups and add regression coverage for duplicate-row tolerance.
- Verification added: Updated collaboration route membership lookups to `scalars().first()`, added duplicate-membership regression in `backend/tests/test_collaboration.py`, and reran targeted Playwright collaboration + contracts workflows (passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Teaming gap-analysis endpoint failed with `500` during new multi-user integration coverage.
- Root cause: Capability-gap service referenced `RFP.raw_text`, but the active model exposes `full_text`/`description` fields, causing an attribute error at runtime.
- Prevention checklist: Before service-layer field access, verify model field names against current SQLModel definitions and add endpoint regression tests that execute the real route path.
- Verification added: Updated `capability_gap_service.py` to use `full_text`/`description`/`title` fallback chain, expanded `test_teaming_board.py` for multi-user request acceptance + gap analysis, and validated in Playwright (`teaming-workflow.spec.ts`).

### 2026-02-10
- Date: 2026-02-10
- Mistake: New teaming E2E fit-analysis step initially failed with a locator timeout because the test tried to interact with search-tab controls while still on the sent-requests tab.
- Root cause: Workflow-state transition was implicit in the test and not re-anchored to the correct tab before interacting with tab-specific controls.
- Prevention checklist: For multi-tab UI workflows, always navigate back to the expected tab/state immediately before interacting with tab-scoped controls, and keep selectors scoped to visible tab content.
- Verification added: Updated `teaming-workflow.spec.ts` to explicitly return to `Partner Search` before invoking fit analysis; reran targeted Playwright collaboration/teaming/contracts workflows (passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Collaboration Playwright validation initially failed with a backend `500` when loading governance trends in local dev mode.
- Root cause: Local SQLite file (`dev.db`) predated collaboration-governance schema fields (`requires_approval`, etc.), so route queries referenced columns missing from that stale database file.
- Prevention checklist: For deterministic SQLite Playwright runs after schema evolution, use a fresh DB path (or run migrations) before treating UI failures as product regressions.
- Verification added: Re-ran stack with fresh SQLite database (`dev_e2e.db`) plus `DEBUG=true` and `MOCK_AI=true`, then reran `collaboration-workflow.spec.ts` and confirmed pass with governance trend + audit export checks.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Collaboration E2E helper intermittently failed right after workspace creation by asserting detail-pane heading visibility before workspace selection stabilized.
- Root cause: Test helper assumed newly created workspace would always auto-select immediately, but UI state could briefly show the workspace only in sidebar list first.
- Prevention checklist: After create actions in list/detail UIs, explicitly select the created row before asserting detail-pane content; avoid implicit selection assumptions.
- Verification added: Updated `collaboration-workflow.spec.ts` helper to click the created workspace row before heading assertion; reran targeted Playwright collaboration workflow successfully.

### 2026-02-10
- Date: 2026-02-10
- Mistake: New global-search Playwright workflow failed to close the command palette on `Escape`.
- Root cause: Escape handling existed only in the input key handler, so route-level keyboard events did not consistently dismiss the modal.
- Prevention checklist: For command palettes/modals, implement `Escape` handling on a global key listener (not only focused input handlers) and include a browser test that verifies close behavior.
- Verification added: Added global `Escape` handler in `global-search.tsx` and validated with Playwright `search-plg-workflow.spec.ts` plus `global-search.test.tsx`.

### 2026-02-14
- Date: 2026-02-14
- Mistake: Email-ingest duplicate detection keyed only on `message_id`, which caused cross-config/cross-user collisions and dropped valid messages.
- Root cause: Deduplication and DB uniqueness were implemented globally rather than tenant/config scoped.
- Prevention checklist: For ingestion dedupe, enforce uniqueness at the correct tenancy boundary (config/user scope) in both app logic and DB constraints; add regression coverage for same external IDs across users.
- Verification added: Updated ingest dedupe query + model/migration to `config_id + message_id` and added regression in `backend/tests/test_email_ingest.py`.

### 2026-02-14
- Date: 2026-02-14
- Mistake: Updated signals/events Playwright flow failed due strict-mode selector collisions after adding new automation/calendar controls (`Budget` matched `Analyze Budget Docs`; event titles appeared in alerts + calendar + list rows).
- Root cause: Assertions/actions used broad text/role selectors in views with intentionally repeated labels.
- Prevention checklist: For multi-surface pages (alerts + calendars + list cards), add stable `data-testid` hooks per container/row and use scoped or `exact: true` selectors in Playwright before adding new similarly named controls.
- Verification added: Added `event-list-row` and `event-alert-row` test IDs, hardened exact/scoped locators in `signals-events-workflow.spec.ts`, and reran targeted Playwright workflow (`2/2` passing).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Playwright auth fixture failed during targeted email-ingest validation because requests were sent to `/api/v1/api/v1/*`.
- Root cause: Local frontend startup used `NEXT_PUBLIC_API_URL` with an already-versioned path (`.../api/v1`), while Next rewrites also append `/api/v1`, causing a double-prefix contract miss.
- Prevention checklist: For local E2E stacks, keep `NEXT_PUBLIC_API_URL` at backend origin only (no version path) and verify first auth request paths before debugging feature code.
- Verification added: Restarted frontend with corrected `NEXT_PUBLIC_API_URL=http://127.0.0.1:8010`, reran Playwright `email-ingest-workflow.spec.ts`, and confirmed pass.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Opportunities view hard-locked into a retry-only screen after SAM sync failures, hiding primary actions.
- Root cause: Error handling used an early-return full-page state for all errors, including transient ingest failures.
- Prevention checklist: Keep recoverable upstream errors non-blocking in list surfaces; preserve core user actions (manual create, search, navigation) under degraded external dependencies.
- Verification added: Replaced blocking error state with inline banner + refresh/dismiss controls and added frontend regression (`keeps primary actions available when SAM sync fails`).

### 2026-02-10
- Date: 2026-02-10
- Mistake: `Add RFP` CTA existed but performed no action, leaving users blocked when SAM was rate-limited.
- Root cause: UI control was rendered without any handler or linked create surface.
- Prevention checklist: Every primary CTA must be wired to a concrete flow and covered by a click-through test that verifies the expected side effect.
- Verification added: Implemented in-page manual Add RFP form wired to `rfpApi.create`, added unit coverage (`allows manually creating an RFP from the opportunities page`), and validated live browser creation.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Analysis generation UI showed a generic error even when backend returned actionable Gemini quota/rate-limit detail.
- Root cause: Frontend catch path ignored structured API error payloads (`response.data.detail`).
- Prevention checklist: Parse and surface backend error detail for external dependency failures (rate limits/quota/auth) rather than replacing with generic fallback text.
- Verification added: Added shared API error parser (`frontend/src/lib/api/error.ts`) with tests and wired analysis/opportunities handlers; live browser now displays `Gemini API rate limit reached...` detail.

### 2026-02-10
- Date: 2026-02-10
- Mistake: SAM sync retried too frequently despite long upstream `Retry-After`, causing repetitive 429 loops and noisy user experience.
- Root cause: A hardcoded `60s` cap in SAM HTTP-429 handling overrode circuit-breaker settings and upstream retry windows.
- Prevention checklist: Avoid duplicate hardcoded retry caps in service paths; route all retry-window limits through shared config-aware logic and cover with regression tests.
- Verification added: Removed the hardcoded SAM 60s cap, honored long retry windows end-to-end, added ingest regression coverage, and validated live browser countdown (`Sync in 370:19`).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Draft generation repeatedly failed on primary Gemini model quota limits without automatic model fallback.
- Root cause: Generation paths used a single model (`pro`) and retried user requests instead of attempting configured lower-tier models or opening a local quota cooldown circuit.
- Prevention checklist: For external AI generation, implement ordered model fallback and local quota-circuit behavior before returning user-visible rate-limit errors.
- Verification added: Added fallback/circuit logic in `gemini_service.py`, added service regression tests, and validated live generation success on fallback model (`models/gemini-2.5-flash`) in `/analysis/3`.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Diagnostics telemetry endpoint worked at `/ws/diagnostics` but frontend contract expected `/api/v1/ws/diagnostics`, causing drift until router mounting was aligned.
- Root cause: WebSocket router was mounted without the API version prefix while frontend proxy/API clients were standardized on `/api/v1/*`.
- Prevention checklist: For every newly added route family, validate mounted prefixes against frontend API client paths and include at least one direct endpoint integration test on the exact proxied path.
- Verification added: Mounted websocket router under `/api/v1`, added backend diagnostics endpoint integration coverage (`test_websocket_diagnostics.py`), and validated `/diagnostics` telemetry cards in Playwright.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Office-host Playwright harness initially failed because `Office.onReady` mock did not execute callback-based usage pattern.
- Root cause: Mock implemented Promise return only, while UI hook also relied on callback invocation semantics used by Office.js host flows.
- Prevention checklist: When mocking Office runtime, support both callback and Promise styles for `Office.onReady` and validate with at least one host-in-loop sync scenario.
- Verification added: Updated Office mock in `word-addin-office-host.spec.ts` to invoke callback and return Promise; reran host-in-loop taskpane sync test (passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Auth-based E2E setup intermittently failed on registration when company and cookie consent UI assumptions differed between environments.
- Root cause: Fixture enforced required interactions for optional/conditionally rendered controls.
- Prevention checklist: For shared auth fixtures, model optional controls (`company`, cookie banner actions) as conditional interactions and keep registration helper resilient across env toggles.
- Verification added: Updated `frontend/e2e/fixtures/auth.ts` and workflow registration helpers to optionalize company/cookie interactions; reran admin/collaboration/teaming Playwright flows.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Initial Playwright rerun for new dash/sharepoint coverage targeted the wrong local stack and produced authentication-fixture false negatives.
- Root cause: Tests defaulted to `localhost:3000` while feature validation required deterministic app/backend pair (`3100`/`8010`) with explicit mock/debug settings.
- Prevention checklist: Before any full Playwright sweep, start an explicit deterministic stack and export `E2E_BASE_URL` to the active frontend port; verify both frontend and backend health endpoints before interpreting failures.
- Verification added: Re-ran targeted and full Playwright suites on `E2E_BASE_URL=http://localhost:3100` with backend `:8010`, `DEBUG=true`, and `MOCK_AI=true` (`51/51` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: New proposal-workspace E2E assertions failed under strict mode because labels (`Export to SharePoint`, `sync`) matched multiple controls/content nodes.
- Root cause: Assertions used broad text locators in a dense UI where headings, action buttons, and event rows reuse the same strings.
- Prevention checklist: In workflow specs, scope assertions by semantic role/container (`heading`, card-local text) and avoid raw text matchers when button/event labels can overlap.
- Verification added: Updated `proposal-editor-workflow.spec.ts` to role-scoped heading and deterministic event-count assertions; reran targeted specs and full Playwright suite (`51/51` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Past-performance API contracts drifted from frontend calls due duplicated backend route segments (`/documents/documents/*`).
- Root cause: Route decorators were added with nested `/documents/*` paths under a router that already used `/documents` prefix, and no contract test covered the frontend path.
- Prevention checklist: For prefixed routers, validate final resolved paths with endpoint-level tests and include at least one frontend client contract assertion for each new route family.
- Verification added: Added canonical past-performance routes + legacy aliases in `documents.py`, aligned frontend list endpoint to `/documents/past-performances/list`, and added regression in `backend/tests/test_documents.py`.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Contact extraction returned `400` for manually created RFPs that had text in `description` but not `full_text`.
- Root cause: Extraction route assumed `full_text` was always populated and did not include a fallback for pre-extraction/manual records.
- Prevention checklist: For AI extraction endpoints, use a deterministic fallback chain across available text fields (`full_text` -> `description` -> explicit error) and cover both record shapes in integration tests.
- Verification added: Updated `contacts.py` extraction fallback and added regression coverage in `backend/tests/test_contacts.py`.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Contacts extraction auto-link persisted agency linkage in backend, but `/contacts` UI did not refresh agency-directory state after extraction, causing stale parity behavior.
- Root cause: Extraction callback only refreshed contacts list (`fetchContacts`) and skipped agency refresh (`fetchAgencies`) after backend writes.
- Prevention checklist: When introducing backend side effects that update multiple UI datasets, ensure post-action callbacks refresh every affected dataset and cover the end-to-end path in Playwright.
- Verification added: Updated `/contacts` page extraction callback to refresh contacts + agencies, added `Close extraction modal` accessibility control, and validated via `contact-extract-button.test.tsx` + `contacts-workflow.spec.ts`.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Capability docs retained stale regression counters (`51/51` Playwright, `153/153` backend) after adding six new end-to-end scenarios and twelve backend tests.
- Root cause: Documentation updates were done before the final full-suite rerun and were not reconciled after the expanded validation set landed.
- Prevention checklist: After adding/removing tests, run full backend/frontend/Playwright sweeps and update all status/roadmap docs in one final pass using exact suite counts from command output.
- Verification added: Re-ran `pytest -q` (`165/165`), `vitest --run` (`31/31`), and `playwright test` (`57/57`); updated `competitive-analysis-and-roadmap.md`, `capability-integration-tracker.md`, and `capability-surface-status.md` with refreshed evidence.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Full Playwright sweep surfaced intermittent failure in signals workflow where read-state was asserted before backend propagation completed.
- Root cause: E2E test clicked signal rows and immediately queried API without waiting for asynchronous `markRead` completion.
- Prevention checklist: For UI actions that trigger async persistence, assert local UI transition and use `expect.poll` against backend state before final truth assertions.
- Verification added: Hardened `signals-events-workflow.spec.ts` with row-level unread-indicator wait plus backend poll; reran targeted signals spec and full Playwright suite (`58/58` passing).

### 2026-02-10
- Date: 2026-02-10
- Mistake: Validation counters in docs drifted again after additional suite expansion (new Playwright and backend coverage landed post-refresh).
- Root cause: Counts were updated from an intermediate run instead of the final regression pass.
- Prevention checklist: Always perform a final single-source-of-truth sweep (`pytest -q`, `vitest run`, `playwright test`) immediately before closing and update docs from those exact outputs.
- Verification added: Re-ran `pytest -q` (`169/169`), `vitest run` (`32/32`), and `playwright test` (`58/58`); refreshed all capability/roadmap status docs to match final counts.

### 2026-02-10
- Date: 2026-02-10
- Mistake: Template-system synchronization introduced a live `500` during Playwright on `/templates`.
- Root cause: `_ensure_system_templates` used `scalar_one_or_none()` on system-template names; legacy duplicate rows triggered `MultipleResultsFound` and broke request handling.
- Prevention checklist: For seed/sync paths that can encounter historical duplicates, always use duplicate-tolerant fetches (`scalars().first()`) unless a DB uniqueness constraint is guaranteed.
- Verification added: Updated `templates.py` synchronization lookup to `scalars().first()`, reran backend template/report/support integration tests, and revalidated affected Playwright workflows (`analytics-reports-intelligence-workflow.spec.ts`, `templates-reports-help-onboarding-workflow.spec.ts`).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Admin Playwright workflow timed out waiting for resend/revoke responses despite UI interactions succeeding.
- Root cause: Response matcher assumed backend direct paths (`/api/v1/...`) while browser traffic uses frontend proxy paths (`/api/...`), so the matcher never observed the request.
- Prevention checklist: In Playwright, match API responses by stable suffix/patterns (for example `"/member-invitations/" + "/resend"`) instead of hardcoding backend-prefixed URLs when a proxy rewrite layer is present.
- Verification added: Updated `admin-org-workflow.spec.ts` response predicates to proxy-aware URL matching and reran targeted admin workflow successfully.

### 2026-02-14
- Date: 2026-02-14
- Mistake: Activation assertion in admin workflow was flaky because it depended on post-refresh row text timing.
- Root cause: Assertion waited for UI text mutation (`activated`) after multiple async calls (`activate` then full admin refetch), which drifted under dev-mode latency.
- Prevention checklist: For mutation steps in E2E, assert the mutation response contract first (HTTP `200` + payload status) and keep UI text checks secondary/optional when they depend on slower aggregate refreshes.
- Verification added: Updated `admin-org-workflow.spec.ts` to assert `/activate` response payload status and reran the targeted admin Playwright workflow (`1/1` passing).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Collaboration digest recipient counts over-reported viewers in live Playwright even when only one invited partner existed.
- Root cause: `workspace_members` can contain duplicate rows for the same user in dev-mode invitation-accept flows, and recipient counting for `viewer`/`contributor` used raw row counts instead of unique user IDs.
- Prevention checklist: Treat membership-derived metrics as user-unique aggregates (`distinct user_id`) and add regression coverage for duplicate membership rows on role-scoped counts.
- Verification added: Updated digest recipient counting to dedupe by `user_id` for viewer/contributor roles, added duplicate-row regression in `test_collaboration.py`, and reran targeted collaboration Playwright workflow (`1/1` passing).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Initial targeted Playwright rerun produced false workflow failures (workspace create timing + teaming API assertions) because local SQLite schema was stale.
- Root cause: Backend was started against an existing dev SQLite file that predated newer columns (for example onboarding `step_timestamps`), causing intermittent `500` responses and misleading UI-level test symptoms.
- Prevention checklist: For deterministic local Playwright validation on SQLite, always start with a fresh DB file (or run migrations) and verify no schema-drift errors in backend logs before interpreting UI failures.
- Verification added: Re-ran targeted Playwright workflows on a fresh SQLite DB (`DATABASE_URL=sqlite+aiosqlite:///./e2e_fresh.db`) with `DEBUG=true` and `MOCK_AI=true`; collaboration/diagnostics/teaming workflows passed.

### 2026-02-14
- Date: 2026-02-14
- Mistake: Policy-based step-up disable test initially failed because the test helper created organization membership rows but did not set `users.organization_id`, so org security settings were ignored by policy lookup.
- Root cause: Security policy resolution reads organization settings from `user.organization_id`; membership-only setup left users in default-policy path.
- Prevention checklist: In multi-tenant tests, always set both `organization_members` and `users.organization_id` whenever org-scoped policy behavior is under test.
- Verification added: Updated policy test helper to sync `user.organization_id`, then re-ran targeted backend suites (`test_policy_enforcement.py`, `test_admin_roles.py`, `test_capability_integrations.py`, `test_collaboration.py`) with `27/27` passing.

### 2026-02-14
- Date: 2026-02-14
- Mistake: Capture bid-vote endpoint raised `500` when creating human scorecards in the new stress-test workflow.
- Root cause: `submit_human_vote` referenced `current_user.user_id` even though `UserAuth` exposes `id`; the path was under-tested and slipped through until scenario-simulator integration.
- Prevention checklist: For every auth-bearing route, add regression coverage that executes the endpoint under authenticated context and validates principal field usage (`id` vs legacy aliases).
- Verification added: Fixed scorer attribution to `current_user.id` in `capture/bid_decision.py` and validated via backend integration (`test_capture.py`, `test_capability_integrations.py`).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Initial Playwright assertion for capture stress-test results failed with strict-mode locator ambiguity on duplicated scenario names.
- Root cause: E2E checks used global text matchers while scenario labels intentionally appear in both config controls and results cards.
- Prevention checklist: In high-density pages, scope text assertions to the target container (`card`/`panel`) and semantic element type (`p.font-medium`, heading role) before adding new assertions.
- Verification added: Scoped capture workflow assertions to the `Scenario Results` card and reran targeted Playwright (`capture-workflow.spec.ts`, passing).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Reviews Playwright workflow failed after packet-builder UI expansion due ambiguous proposal-title text assertions.
- Root cause: Proposal title appeared in both packet selector options and review-card links, and global `getByText` assertions violated strict mode.
- Prevention checklist: For list+selector pages, anchor assertions to semantic roles (`link`, `combobox`, scoped container) instead of global text selectors when labels are intentionally reused.
- Verification added: Updated `reviews-workflow.spec.ts` to assert proposal visibility via link role and reran targeted Playwright (`capture-workflow.spec.ts`, `reviews-workflow.spec.ts`, `2/2` passing).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Initial detached startup commands for deterministic Playwright validation returned process IDs but no live backend/frontend services.
- Root cause: Background launch was treated as successful without immediate liveness checks (`lsof`/health), so dead-on-start processes were not detected before test execution.
- Prevention checklist: After detached service start, always validate listener ports and explicit health endpoints before running Playwright; if either check fails, relaunch in foreground sessions and capture startup output.
- Verification added: Relaunched deterministic stack with explicit health checks and completed `export-validation.spec.ts` (`4/5` passing, PDF dependency skip expected).

### 2026-02-14
- Date: 2026-02-14
- Mistake: New opportunities E2E for amendment autopilot failed with `Cannot read properties of undefined (reading 'length')`.
- Root cause: A broad Playwright route mock (`/snapshots**`) intercepted both `/snapshots/diff` and `/snapshots/amendment-impact`, returning the wrong payload shape to the diff/impact handlers.
- Prevention checklist: In Playwright API mocking, use exact/regex route patterns for list endpoints and register generic routes so they cannot shadow more specific subpaths.
- Verification added: Replaced snapshot list matcher with exact regex (`/snapshots(?:\\?.*)?$`) and reran `opportunities.spec.ts` (`4/4` passing).

### 2026-02-14
- Date: 2026-02-14
- Mistake: Proposal rewrite track-changes state appeared and then disappeared, causing `AI Suggestions` workflow checks to fail.
- Root cause: Proposal workspace hydrated editor content from section updates on every `sections` refresh; rewrite responses updated `generated_content` but left `final_content`, so hydration overwrote suggestion-marked editor content with stale final text.
- Prevention checklist: For editor surfaces, only hydrate content on explicit section selection changes (or hard reset actions), not on every metadata refresh; add regression tests for rewrite/expand flows where backend returns generated text while final text remains unchanged.
- Verification added: Added section-selection-scoped hydration guard in proposal workspace, introduced stable suggestion-toolbar test id, added regression test for rewrite persistence, and revalidated via unit tests plus live Playwright MCP rewrite flow.

### 2026-02-14
- Date: 2026-02-14
- Mistake: Semantic search used global embeddings without explicit tenant scoping and depended on pgvector-only cosine SQL operators.
- Root cause: `document_embeddings` lacked `user_id`, and search executed `<=>` distance in all environments; on SQLite this causes SQL syntax failure and on shared stores it risks cross-tenant result leakage.
- Prevention checklist: Treat vector stores as tenant-scoped data by schema (`user_id` + filter in every query), and always provide a deterministic non-pgvector search path for SQLite/local test stacks used in CI and dev.
- Verification added: Added `user_id` to embeddings with migration backfill, implemented SQLite cosine fallback in `embedding_service.search`, wired auto-index hooks across core entities, and added regression coverage in `test_semantic_search.py`.

### 2026-02-14
- Date: 2026-02-14
- Mistake: Targeted backend suites intermittently failed with `sqlite3.OperationalError: database is locked` and teardown table-drop errors.
- Root cause: Test harness hardcoded `sqlite+aiosqlite:///./test.db`, which collided with concurrently running local processes using the same file.
- Prevention checklist: Use an isolated per-run SQLite file for backend tests (or explicit `TEST_DB_PATH`) and clean DB artifacts on session teardown to avoid cross-process lock contention.
- Verification added: Updated `backend/tests/conftest.py` to allocate a unique temp DB path and cleanup `-journal/-wal/-shm` artifacts; reran targeted backend suites (`test_rfps.py`, `test_saved_searches.py`, `test_data_sources.py`, `test_semantic_search.py`) successfully.
