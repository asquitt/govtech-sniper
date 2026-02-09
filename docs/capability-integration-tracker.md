# Capability Integration Tracker

Purpose: make hidden/orphaned capabilities visible and track integration status across backend routes, frontend surfaces, tests, and live verification.

## Status Legend
- `Integrated`: wired in UI + API and verified in current workflows.
- `Partial`: implemented but not fully wired, discoverable, or validated end-to-end.
- `Hidden`: implemented but not visible in primary navigation or key workflows.
- `Orphaned`: code exists but currently lacks active integration path.
- `Planned`: identified target, implementation pending.

## Update Rules
- Update this file in every session where capabilities are tested or integrated.
- Add an entry when new hidden/orphaned code is discovered.
- Move items toward `Integrated` only after code + tests + live UI verification.
- Keep evidence concrete: route prefix, UI surface, test coverage, and date.

## Capability Matrix (Initial Baseline)
| Capability Domain | Frontend Surface | Backend Prefix/Module | Status | Evidence | Next Integration Task |
| --- | --- | --- | --- | --- | --- |
| Auth + Onboarding | `/login`, `/register`, onboarding widget | `/auth`, `/onboarding` | Integrated | Playwright auth specs passing; live register/login validated on 2026-02-09 | Add explicit rate-limit/worker health dashboard metrics for auth-heavy E2E runs |
| Opportunities Ingest | `/opportunities` | `/ingest`, `/rfps`, `/saved-searches` | Integrated | Live sync works; Playwright full suite passing; sync fallback fixed for missing worker on 2026-02-09 | Add ingest observability UI for task mode (`sync` vs `queued`) |
| Analysis + Matrix | `/analysis/[rfpId]` | `/analyze` | Integrated | Live add/generate flow validated; matrix empty-shape contract in place | Add explicit “No matrix yet” UX copy sourced from API status metadata |
| Draft Generation | `/proposals`, `/analysis/[rfpId]` generate controls | `/draft` | Integrated | Sync fallback fixed for missing worker; backend draft tests passing | Add UI indicator when generation falls back to synchronous mode |
| Export | Analysis/Proposals export actions | `/export` | Integrated | Live DOCX export validated; critical path exercised repeatedly | Add regression test asserting downloaded filename/content-type contract |
| Dash Assistant | `/dash` | `/dash` | Integrated | Dash E2E selectors updated to current UI; suite passing | Expand coverage for session/message persistence flows |
| Capture | `/capture` | `/capture`, `/capture/timeline`, `/budget-intel`, `/awards` | Partial | Routes + API clients + page exist; not fully covered in critical path | Add end-to-end capture flow test (plan -> gate review -> scorecard) |
| Teaming | `/teaming` | `/teaming` + `/capture/teaming` | Partial | UI page and APIs exist; not part of critical-path verification | Add live Playwright scenario for partner request/response lifecycle |
| Collaboration | `/collaboration` | `/collaboration` | Partial | Page + API client exist; no full E2E coverage yet | Add workspace create/invite/share E2E test |
| Contracts | `/contracts` | `/contracts/*` | Partial | Fixed proxy path normalization for `/api/contracts` on 2026-02-09; live API probe now returns 200 (no CORS redirect) | Add Playwright scenario that creates contract + deliverable + status report through UI |
| Revenue | `/revenue` | `/revenue` | Partial | Page/API exist, covered lightly by nav test only | Add data contract + chart rendering assertions |
| Forecasts | `/forecasts` | `/forecasts` | Partial | Page/API exist, nav-only coverage | Add alerts + match workflow tests |
| Analytics + Reporting | `/analytics`, `/reports` | `/analytics`, `/reports`, `/activity` | Partial | Fixed SQLite-incompatible analytics/reporting queries on 2026-02-09; `/api/analytics/win-rate`, `/api/analytics/proposal-turnaround`, `/api/reports` now live-verified 200 | Add report generation/export and analytics card integrity tests |
| Intelligence | `/intelligence` | `/intelligence`, `/kb-intelligence` | Partial | Fixed SQLite-incompatible budget intelligence query on 2026-02-09; `/api/intelligence/budget` now live-verified 200 | Add debrief and KPI end-to-end checks |
| Signals + Events + Reviews | `/signals`, `/events`, `/reviews` | `/signals`, `/events`, `/reviews` | Partial | Pages exist; nav coverage only | Add CRUD and notification-linked E2E scenarios |
| Admin + Org | `/admin` | `/admin`, `/audit`, `/teams` | Partial | Fixed `AsyncSession` misuse in admin routes on 2026-02-09; endpoints now return expected auth/role guard status (403 for users without org) instead of 500 | Add first-run org bootstrap flow from admin page and role-based guard E2E |
| Integrations | `/settings/integrations` + subpages | `/integrations`, `/sharepoint*`, `/salesforce`, `/data-sources`, `/email-ingest`, `/subscription`, `/workflows`, `/unanet` | Partial | Surfaces exist; integration reliability varies by environment | Add contract tests per provider and mock-provider E2E harness |
| Word Add-in | `/word-addin/*` companion APIs | `/word-addin`, `/graphics`, `/versions` | Hidden | `/word-addin` redirect and `/word-addin/taskpane` browser-safe runtime validated on 2026-02-09 (no mount warning, no Office telemetry host failure) | Add discoverability path from proposal editor and E2E sync tests |
| Template Marketplace | `/templates` page exists | `/templates` (marketplace + base templates) | Hidden | Backend marketplace routes exist; not exposed in main sidebar nav | Decide product placement and add nav entry or deprecate unused routes |
| SCIM + Webhooks + Secrets | No primary UI surface | `/scim/v2`, `/webhooks`, `/secrets` | Hidden | Backend enterprise endpoints present, minimal UI exposure | Add admin docs/UI entry points and operational runbooks |
| WebSocket Task Feed | Implicit in client utils | `/ws`, `/ws/task/*` | Hidden | Websocket route active, not explicitly surfaced in diagnostics UI | Add developer diagnostics page for websocket task status |

## Orphan/Hiding Hotspots (Initial)
| Hotspot | Why It Looks Orphaned/Hidden | Action |
| --- | --- | --- |
| Enterprise endpoints (`/scim/v2`, `/webhooks`, `/secrets`) | Implemented server-side without clear in-app discoverability | Add admin information architecture and settings entry points |
| Word add-in support | API/client paths exist but no direct dashboard discoverability | Add explicit “Word Add-in” surface in proposals/settings |
| Template marketplace capabilities | Backend routes and API client exist; user path appears weak | Confirm product intent and either wire or remove dead surface |
| Duplicate analytics surfaces | `analytics.py` and `analytics_reporting.py` both under `/analytics` increase overlap risk | Audit endpoint ownership and consolidate route responsibilities |
| Word add-in runtime in plain browser | Previously emitted runtime noise outside Office host | Resolved on 2026-02-09 by Office-host-gated script loading + lifecycle guards; keep regression checks in Playwright sweep |

## Latest Live Validation (2026-02-09)
| Check | Result |
| --- | --- |
| `/api/contracts` | `200` via frontend proxy after rewrite fix |
| `/api/analytics/win-rate` | `200` |
| `/api/analytics/proposal-turnaround` | `200` |
| `/api/reports` | `200` |
| `/api/intelligence/budget` | `200` |
| `/api/admin/organization` | `403` (expected for user without org membership; no 500) |
| `/word-addin` route | Redirects to `/word-addin/taskpane` (no 404) |
| `/word-addin/taskpane` runtime | No React mount warnings after Office host gating update |
| `/api/templates/categories/list` | `200` (legacy alias retained) |
| `/api/notifications/deadlines` | `200` (route implemented for frontend contract) |

## Integration Backlog (Prioritized)
1. Add capability-level Playwright E2E for Capture, Teaming, Collaboration, Contracts, and Reviews.
2. Add discoverability surfaces for hidden enterprise capabilities (SCIM/webhooks/secrets/word-addin/templates).
3. Build a single “Capability Health” admin page showing route availability, worker status, and feature flags.
4. Run a route-to-UI ownership audit and remove or merge duplicate/unused endpoints.
