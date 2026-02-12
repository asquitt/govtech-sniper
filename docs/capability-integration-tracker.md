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

## Capability Matrix
| Capability Domain | Frontend Surface | Backend Prefix/Module | Status | Evidence | Next Integration Task |
| --- | --- | --- | --- | --- | --- |
| Auth + Onboarding | `/login`, `/register`, onboarding widget + guided setup modal | `/auth`, `/onboarding` | Integrated | Expanded on 2026-02-10 with guided onboarding modal controls (`Guided Setup`, step progression, mark-complete) validated in frontend unit + Playwright (`onboarding-wizard-guided-flow.test.tsx`, `templates-reports-help-onboarding-workflow.spec.ts`) | Add account-based onboarding branching (owner/member persona presets) |
| Free Tier / PLG | `/free-tier`, `/settings/subscription`, `/login`, `/register` | `/subscription` + tier limiter in `api/deps.py` | Integrated | Added active upgrade nudges + public free-tier landing integration on 2026-02-10 (`subscription-upgrade-nudge.test.tsx`, `free-tier-page.test.tsx`, `search-plg-workflow.spec.ts`) | Add usage-triggered cross-route nudges when API limiter returns tier-limit errors |
| Opportunities Ingest | `/opportunities` | `/ingest`, `/rfps`, `/saved-searches` | Integrated | Real-key sweep on 2026-02-10 validated SAM `429` handling with inline retry messaging plus manual add fallback (new in-page Add RFP form) so flow stays unblocked when SAM is rate-limited | Add ingest observability UI for task mode (`sync` vs `queued`) |
| Analysis + Matrix | `/analysis/[rfpId]` | `/analyze` | Integrated | Real-key sweep on 2026-02-10 validated requirement add/generate path and Gemini `429` user-facing messaging (detail surfaced instead of generic failure) | Add explicit “No matrix yet” UX copy sourced from API status metadata |
| Draft Generation | `/proposals`, `/analysis/[rfpId]` generate controls | `/draft` | Integrated | Sync fallback fixed for missing worker; backend draft tests passing | Add UI indicator when generation falls back to synchronous mode |
| Export | Analysis/Proposals export actions | `/export` | Integrated | Real-key sweep on 2026-02-10 downloaded DOCX from analysis flow (`proposal_REAL-FLOW-1770744126240.docx`) after proposal creation | Add regression test asserting downloaded filename/content-type contract |
| Dash Assistant | `/dash` | `/dash` | Integrated | Expanded on 2026-02-10 with primary chat-input voice controls (speech-to-text + text-to-speech toggle) validated in `dash-chat-voice-controls.test.tsx` and Playwright `dash.spec.ts`; full suite passing (`58/58`) | Expand coverage for long-session persistence and multi-message voice command chaining |
| Global Semantic Search | Header search overlay (`Ctrl+K` + Search icon), `/opportunities` | `/search` | Integrated | Wired global search modal into dashboard shell on 2026-02-10 with faceted entity filters + header trigger (`global-search.test.tsx`, `header-search-trigger.test.tsx`, `search-plg-workflow.spec.ts`) | Add ranking personalization and proposal-section deep-link routing |
| Contact Intelligence | `/contacts`, opportunity detail contact card | `/contacts` | Integrated | Expanded on 2026-02-10 with extraction auto-linking to `linked_rfp_ids` + agency-directory primary-contact linkage, plus UI auto-link messaging and dual refresh integration (`test_contacts.py`, `contact-extract-button.test.tsx`, `contacts-workflow.spec.ts`) | Add agency/contact graph confidence scoring and duplicate-resolution tooling |
| Capture | `/capture` | `/capture`, `/capture/timeline`, `/budget-intel`, `/awards` | Integrated | Added Playwright workflow coverage on 2026-02-10 for capture plan + gate review + partner link + competitor; backend capture integration tests passing | Expand coverage for timeline and bid scorecard AI/human vote reconciliation |
| Teaming | `/teaming` | `/teaming` + `/capture/teaming` | Integrated | Expanded on 2026-02-10 with partner-level drilldowns + scheduled digest delivery (`/api/v1/teaming/requests/partner-trends`, `/api/v1/teaming/digest-schedule`, `/api/v1/teaming/digest-send`) on top of multi-user request lifecycle, fit trends, and audit export; validated in backend integration + unit + Playwright (`test_teaming_board.py`, `teaming-page-fit-analysis.test.tsx`, `teaming-workflow.spec.ts`) | Add partner cohort benchmarking by NAICS/set-aside |
| Collaboration | `/collaboration`, `/collaboration/accept`, `/collaboration/portal/[workspaceId]` | `/collaboration` | Integrated | Expanded on 2026-02-10 with governance anomaly alerts + scheduled compliance digests (`/api/v1/collaboration/workspaces/{id}/shared/governance-anomalies`, `/api/v1/collaboration/workspaces/{id}/compliance-digest-schedule`, `/api/v1/collaboration/workspaces/{id}/compliance-digest-preview`, `/api/v1/collaboration/workspaces/{id}/compliance-digest-send`) in addition to governed sharing, SLA trends, and audit export; validated in backend integration + unit + Playwright (`test_collaboration.py`, `collaboration-page-governance.test.tsx`, `collaboration-workflow.spec.ts`) | Add digest recipient routing by workspace role |
| Contracts | `/contracts` | `/contracts/*` | Integrated | Expanded on 2026-02-10 with hierarchical parent/child contract wiring plus modification + CLIN lifecycle coverage (`backend/tests/test_contracts.py`, `frontend/src/__tests__/contracts-page.test.tsx`, `frontend/e2e/tests/contracts-workflow.spec.ts`) | Add CLIN fulfillment-status automation and cross-contract roll-up metrics |
| Revenue | `/revenue` | `/revenue` | Integrated | Added backend integration coverage on 2026-02-10 for `/api/v1/revenue/pipeline-summary`, `/api/v1/revenue/timeline`, `/api/v1/revenue/by-agency` (`test_business_capabilities.py`) and Playwright workflow coverage in `revenue-forecasts-workflow.spec.ts` | Add chart-axis regression checks for long agency names |
| Forecasts | `/forecasts` | `/forecasts` | Integrated | Added backend integration coverage on 2026-02-10 for forecast create/match/alert dismiss contracts and Playwright workflow coverage for create + run matching + dismiss alert (`revenue-forecasts-workflow.spec.ts`) | Add forecast-to-RFP linking workflow assertions |
| Analytics + Reporting | `/analytics`, `/reports` | `/analytics`, `/reports`, `/activity` | Integrated | Expanded on 2026-02-10 with drag/drop field selection, shared report views (`/api/v1/reports/{id}/share`), and scheduled email delivery send-now (`/api/v1/reports/{id}/delivery/send`) validated in backend integration + frontend unit + Playwright (`test_marketplace_reports_support.py`, `reports-page-builder.test.tsx`, `analytics-reports-intelligence-workflow.spec.ts`) | Add background delivery worker telemetry and retry audit trail |
| Intelligence | `/intelligence` | `/intelligence`, `/kb-intelligence` | Integrated | Added backend integration coverage on 2026-02-10 for `/api/v1/intelligence/win-loss`, `/kpis`, `/pipeline-forecast`, `/resource-allocation`, and debrief creation; added Playwright intelligence dashboard workflow assertions (`analytics-reports-intelligence-workflow.spec.ts`) | Add multi-period forecast trend assertions |
| Reviews | `/reviews` | `/reviews` | Integrated | Added Playwright workflow coverage on 2026-02-10 with scheduled review setup + dashboard filtering; backend `test_reviews.py` validates schedule/checklist/comment/scoring/complete flow | Add reviewer assignment and inline-comment thread E2E scenario |
| Signals + Events | `/signals`, `/events` | `/signals`, `/events` | Integrated | Added backend integration coverage on 2026-02-10 for signal feed/read/subscription and events CRUD/upcoming contracts (`test_business_capabilities.py`) plus Playwright workflow coverage in `signals-events-workflow.spec.ts` | Add notification fan-out assertions for signal/event triggers |
| Admin + Org | `/admin` | `/admin`, `/audit`, `/teams` | Integrated | Added org-admin member-invite + activation lifecycle UI and backend contract coverage on 2026-02-10 (`/api/v1/admin/members/invite`, `/api/v1/admin/member-invitations`, `/api/v1/admin/member-invitations/{id}/activate`) with backend integration + frontend unit + Playwright validation (`test_admin_roles.py`, `admin-page-invitations.test.tsx`, `admin-org-workflow.spec.ts`) | Add invitation revocation + resend controls |
| Integrations | `/settings/integrations` + subpages | `/integrations`, `/sharepoint*`, `/salesforce`, `/data-sources`, `/email-ingest`, `/subscription`, `/workflows`, `/unanet` | Integrated | Expanded on 2026-02-10 with embedded SharePoint browser on `/settings/integrations`, proposal workspace SharePoint export action, and backend sharepoint export helper hardening (no hardcoded localhost callback); validated via `test_sharepoint.py`, `settings-integrations-page.test.tsx`, and Playwright (`settings-integrations-workflow.spec.ts`, `proposal-editor-workflow.spec.ts`) | Expand provider-specific negative-path assertions (missing fields/disabled states) |
| Data Source Providers | `/settings/data-sources` | `/data-sources`, `services/data_providers/*` | Integrated | Expanded on 2026-02-10 with SLED/DIBBS/GWAC provider breadth (`sled_bidnet`, `dibbs`, `gsa_mas`, `cio_sp3`, `ites`, `oasis`) plus inventory/search/ingest/health regression coverage in `test_data_sources.py` and Playwright settings checks | Expand source depth and refresh cadence toward Govly-scale coverage volume |
| Workflow Automation Rules | `/settings/workflows` | `/workflows`, `services/workflow_engine.py` | Integrated | Added executable workflow engine + `/api/v1/workflows/execute` with trigger wiring from capture-plan create/stage transitions and validated in `test_workflows_execution.py` + Playwright `workflows-workflow.spec.ts` | Add richer condition builder and approval-governance overlays |
| Autonomous Agents | `/agents` | `/agents` | Integrated | Added autonomous agent catalog + run actions (`research`, `capture-planning`, `proposal-prep`, `competitive-intel`) validated via `test_agents.py` and Playwright `agents-workflow.spec.ts` | Add cross-agent orchestration plans and run-history analytics |
| Proposal Graphics | `/proposals/[proposalId]` graphics panel | `/graphics`, `/export` | Integrated | Added template library + generated graphics + in-editor insertion + export rendering coverage (`test_graphics.py`, `test_export_graphics.py`, `proposal-editor-workflow.spec.ts`) | Add richer chart families and DOCX-native drawing transforms |
| Compliance Readiness | `/compliance` | `/compliance/readiness` | Integrated | Added certification/listing readiness surface for FedRAMP, CMMC, GovCloud, AppExchange, and AppSource validated in `test_compliance_dashboard.py` and Playwright `compliance-readiness.spec.ts` | Wire milestone evidence uploads and owner assignments per program |
| Notifications + Push | `/settings/notifications` | `/notifications`, `push_subscriptions` | Integrated | Added push subscription CRUD contracts + settings UI and validated in `test_notifications_push.py` and Playwright `settings-notifications-workflow.spec.ts` | Add web-push delivery telemetry and retry/audit drilldowns |
| Word Add-in | `/word-addin`, `/word-addin/taskpane` | `/word-addin`, `/graphics`, `/versions` | Integrated | Added Office-host-in-loop taskpane harness with injected Office/Word runtime validating pull/push flow beyond browser fallback (`word-addin-office-host.spec.ts`), plus existing backend word-addin integration coverage (`test_word_addin.py`) and proposal workspace session workflow (`proposal-editor-workflow.spec.ts`) | Add host-specific validation matrix (desktop/web Word variants) |
| Template Marketplace | `/templates` | `/templates` (marketplace + base templates) | Integrated | Expanded on 2026-02-10 with vertical proposal kits (IT services/construction/professional services), compliance-matrix templates (GSA MAS/OASIS+/8(a) STARS III), and community publish/rate/fork UX validated in backend integration + frontend unit + Playwright (`test_marketplace_reports_support.py`, `templates-page-marketplace.test.tsx`, `templates-reports-help-onboarding-workflow.spec.ts`) | Add explicit duplicate-template merge tooling for community submissions |
| Customer Success + Help Center | `/help` + in-app support chat widget | `/support` | Integrated | Added searchable help-center guides, interactive tutorials, and support-chat responder endpoints (`/api/v1/support/help-center/articles`, `/api/v1/support/tutorials`, `/api/v1/support/chat`) validated in backend integration + frontend unit + Playwright (`test_marketplace_reports_support.py`, `help-center-page.test.tsx`, `templates-reports-help-onboarding-workflow.spec.ts`) | Add handoff path from chatbot to human support SLA queue |
| SCIM + Webhooks + Secrets | `/admin` capability health card + `/settings/integrations` controls | `/scim/v2`, `/webhooks`, `/secrets` | Integrated | Added end-to-end enterprise validation on 2026-02-10: backend SCIM/webhook/secret integration suites passing (`test_scim.py`, `test_webhooks.py`, `test_secrets.py`), explicit secret delete endpoint, and Playwright UI workflow validating webhook/secret CRUD + rotation from `/settings/integrations` | Add SCIM provisioning activity stream in admin console |
| WebSocket Task Feed | `/diagnostics` + admin capability health runtime card | `/ws`, `/ws/task/*` | Integrated | Added runtime diagnostics telemetry endpoint (`/api/v1/ws/diagnostics`) with task-watch latency, reconnect counts, and inbound/outbound throughput metrics; surfaced in `/diagnostics` and validated by backend integration + Playwright (`test_websocket_diagnostics.py`, `diagnostics-workflow.spec.ts`) | Add long-window telemetry export + alert thresholds |

## Orphan/Hiding Hotspots (Initial)
| Hotspot | Why It Looks Orphaned/Hidden | Action |
| --- | --- | --- |
| Enterprise endpoints (`/scim/v2`, `/webhooks`, `/secrets`) | Previously implemented server-side without clear in-app discoverability | Resolved on 2026-02-10 with admin capability-health visibility + enterprise API workflow validation in backend and Playwright |
| Word add-in support | Previously lacked direct dashboard discoverability | Resolved on 2026-02-09 by adding sidebar route + Playwright nav regression coverage |
| Template marketplace capabilities | Previously weak primary navigation discoverability | Resolved on 2026-02-09 by adding sidebar route + Playwright nav regression coverage |
| Duplicate analytics surfaces | `analytics.py` and `analytics_reporting.py` both under `/analytics` increase overlap risk | Resolved on 2026-02-10 with ownership audit guard in `backend/tests/test_route_ownership_audit.py` validating method/path uniqueness and expected module ownership for frontend-used analytics contracts |
| Word add-in runtime in plain browser | Previously emitted runtime noise outside Office host | Resolved on 2026-02-09 by Office-host-gated script loading + lifecycle guards; keep regression checks in Playwright sweep |
| WebSocket task feed discoverability | Previously hidden in client utils without direct UI surface | Resolved on 2026-02-10 by adding `/diagnostics` route + sidebar entry + Playwright workflow validation |

## Latest Live Validation (2026-02-10)
| Check | Result |
| --- | --- |
| `/api/contracts` | `200` via frontend proxy after rewrite fix |
| `/api/analytics/win-rate` | `200` |
| `/api/analytics/proposal-turnaround` | `200` |
| `/api/reports` | `200` |
| `/api/v1/reports/{id}/share` + `/api/v1/reports/{id}/delivery/send` | `200`; shared-view + scheduled email-delivery send-now lifecycle validated in backend integration (`test_marketplace_reports_support.py`) and exercised in Playwright reports workflow |
| `/api/intelligence/budget` | `200` |
| `/api/admin/organization` | `403` (expected for user without org membership; no 500) |
| `/api/admin/capability-health` | `403` for non-org user + `200` for org admin context (verified by backend integration tests) |
| `/api/v1/admin/members/invite` + `/api/v1/admin/member-invitations` + `/api/v1/admin/member-invitations/{id}/activate` | `200`; invitation create/list/activate lifecycle validated in backend integration, frontend unit, and Playwright (`test_admin_roles.py`, `admin-page-invitations.test.tsx`, `admin-org-workflow.spec.ts`) |
| `/api/revenue/pipeline-summary` | `200` with seeded capture + contract data (`test_business_capabilities.py`) |
| `/api/revenue/timeline?granularity=quarterly` | `200` with weighted + won buckets (`test_business_capabilities.py`) |
| `/api/revenue/by-agency` | `200` with agency-level aggregation (`test_business_capabilities.py`) |
| `/api/forecasts/match` + `/api/forecasts/alerts` | `200` with alert creation + dismiss lifecycle (`test_business_capabilities.py` + `revenue-forecasts-workflow.spec.ts`) |
| `/api/signals/feed` + `/api/signals/subscription` | `200` with read/subscription lifecycle (`test_business_capabilities.py` + `signals-events-workflow.spec.ts`) |
| `/api/events/upcoming` | `200` with create/delete lifecycle (`test_business_capabilities.py` + `signals-events-workflow.spec.ts`) |
| `/api/reports/{id}/generate` + `/api/reports/{id}/export` | `200`; `reports.py` ownership bug (`user.user_id`) fixed to `user.id` on 2026-02-10 and covered by regression tests |
| `/api/intelligence/win-loss`, `/kpis`, `/pipeline-forecast`, `/resource-allocation` | `200` with seeded capture/proposal data (`test_business_capabilities.py`) |
| `/diagnostics` route | Live websocket probe validated (`connected` + `task_status` events) in Playwright |
| `/diagnostics` collaborative telemetry controls | Presence/lock/cursor probe controls + event filtering validated in Playwright (`diagnostics-workflow.spec.ts`) |
| `/api/v1/ws/diagnostics` | `200`; telemetry payload includes task-watch latency avg/p95, reconnect counters, and inbound/outbound throughput validated in backend integration + Playwright (`test_websocket_diagnostics.py`, `diagnostics-workflow.spec.ts`) |
| `/api/admin/capability-health` websocket runtime | Returns websocket endpoint + active connection/task watcher/document/lock/cursor counts and discoverability entry for WebSocket Task Feed |
| `/settings/integrations` enterprise controls | UI-driven webhook + secret CRUD/rotation validated in Playwright (`settings-integrations-workflow.spec.ts`) |
| `/settings/integrations` SharePoint browser surface | Embedded SharePoint browser card rendered and validated in Playwright (`settings-integrations-workflow.spec.ts`) + frontend unit (`settings-integrations-page.test.tsx`) |
| `/api/v1/sharepoint/status` + `/browse` + `/export` | `200` with mocked SharePoint service and export-helper upload contract coverage in `test_sharepoint.py`; proposal workspace SharePoint export dialog path validated in Playwright (`proposal-editor-workflow.spec.ts`) |
| `/api/v1/secrets/{key}` delete | `200` delete + `404` after delete validated in `test_secrets.py` |
| `/api/v1/collaboration/workspaces/{id}/members/{member_id}/role` | `200` owner/admin role update path validated with second-user invitation acceptance and guard checks (`test_collaboration.py`) |
| `/api/v1/collaboration/invitations/accept?token=...` | `200` for matching invited email, `403` for mismatched email (`test_collaboration.py`) |
| `/api/v1/collaboration/contract-feeds/catalog` | `200` feed catalog returned; used by collaboration sharing UI and validated in `test_collaboration.py` |
| `/api/v1/collaboration/contract-feeds/presets` + `/api/v1/collaboration/workspaces/{id}/share/preset` | `200`; preset listing + idempotent preset apply validated in `test_collaboration.py` |
| `/api/v1/collaboration/workspaces/{id}/shared/governance-trends` | `200`; SLA trendline payload and overdue pending calculations validated in `test_collaboration.py` and rendered in collaboration governance card |
| `/api/v1/collaboration/workspaces/{id}/shared/governance-anomalies` | `200`; anomaly detection payload validated in `test_collaboration.py` and rendered in collaboration anomaly alerts |
| `/api/v1/collaboration/workspaces/{id}/compliance-digest-schedule` + `/compliance-digest-preview` + `/compliance-digest-send` | `200`; schedule update + preview + send-now lifecycle validated in backend integration and Playwright collaboration workflow |
| `/api/v1/collaboration/workspaces/{id}/shared/audit-export` | `200` CSV export for admins (`403` for non-admin member) validated in `test_collaboration.py` and exercised by collaboration workflow export action in Playwright |
| `/api/v1/teaming/requests/fit-trends` | `200`; request outcome trend payload validated in `test_teaming_board.py` and rendered in teaming trend card |
| `/api/v1/teaming/requests/partner-trends` + `/digest-schedule` + `/digest-send` | `200`; partner drilldown analytics + digest schedule/send lifecycle validated in `test_teaming_board.py` and `/teaming` Playwright workflow |
| `/api/v1/teaming/requests/audit-export` | `200` CSV export (audit timeline) validated in `test_teaming_board.py` and exercised in Playwright (`teaming-workflow.spec.ts`) |
| `/collaboration/portal/[workspaceId]` switch workspace UX | Portal switch selector navigates between accessible workspaces and renders selected workspace data (`collaboration-workflow.spec.ts` + `collaboration-portal-page.test.tsx`) |
| `/api/v1/admin/members/{user_id}/role` owner guard | Non-owner admin blocked from promoting admins (`403`), owner promotion succeeds (`200`) in `test_admin_roles.py` |
| `/api/v1/analytics/*` ownership audit | Method/path uniqueness + module ownership guard validated in `test_route_ownership_audit.py` |
| `/api/v1/analytics/*` frontend-unused ownership audit | Retirement-candidate guard validates unused contracts (`/documents`, `/slo`, `/alerts`) in `test_route_ownership_audit.py` |
| `/proposals/[proposalId]` deep workflow | Word session create/sync/history + section lock + inline review comment visibility validated in Playwright (`proposal-editor-workflow.spec.ts`) |
| `/dash` voice controls | `Voice`/`Sound` controls rendered in primary chat input and validated via frontend unit (`dash-chat-voice-controls.test.tsx`) + Playwright (`dash.spec.ts`) |
| `/word-addin` route | Redirects to `/word-addin/taskpane` (no 404) |
| `/word-addin/taskpane` runtime | No React mount warnings after Office host gating update |
| `/word-addin/taskpane` Office-host harness | Injected Office/Word runtime validates pull/push sync flow in Playwright (`word-addin-office-host.spec.ts`) |
| `/templates` route | Reachable from primary sidebar navigation; Playwright navigation test passing |
| `/help` route | Knowledge base, interactive tutorials, and chat support surface validated in Playwright (`templates-reports-help-onboarding-workflow.spec.ts`) |
| `/api/v1/support/help-center/articles` + `/api/v1/support/tutorials` + `/api/v1/support/chat` | `200`; support help/tour/chat contracts validated in backend integration + frontend unit + Playwright (`test_marketplace_reports_support.py`, `help-center-page.test.tsx`) |
| `/api/v1/templates` + `/api/v1/templates/marketplace` | `200`; vertical proposal/compliance templates + community publish/rate/fork flow validated in backend integration + Playwright (`test_marketplace_reports_support.py`, `templates-reports-help-onboarding-workflow.spec.ts`) |
| `/api/templates/categories/list` | `200` (legacy alias retained) |
| `/api/notifications/deadlines` | `200` (route implemented for frontend contract) |
| `/api/v1/ingest/sam` (real key) | `429` with retry window; UI now keeps opportunities surface usable and shows actionable message instead of hard lockout |
| `/opportunities` manual add fallback | Live browser validation created `SLED-REAL-2026-001` via new in-page Add RFP form; record appeared immediately in table |
| `/api/v1/draft/REQ-001` (real key) | `429` with Gemini quota/rate-limit detail; analysis UI now surfaces actionable message (`Gemini API rate limit reached...`) |
| Analysis export with real stack | DOCX download succeeded in browser (`proposal_REAL-FLOW-1770744126240.docx`) after proposal bootstrap from analysis page |
| `/api/v1/data-sources` + provider contracts | `200`; provider list/search/ingest/health contracts validated for `gsa_ebuy`, `fpds`, `usaspending`, `sled_bidnet`, `dibbs`, `gsa_mas`, `cio_sp3`, `ites`, and `oasis` via `test_data_sources.py` |
| `/api/v1/agents/catalog` + run endpoints | `200`; autonomous agent catalog + run actions validated in backend integration (`test_agents.py`) and Playwright (`agents-workflow.spec.ts`) |
| `/api/v1/workflows/execute` + trigger execution records | `200`; workflow execution persistence validated through capture stage-change triggers in backend integration + Playwright (`test_workflows_execution.py`, `workflows-workflow.spec.ts`) |
| `/api/v1/compliance/readiness` | `200`; readiness payload for FedRAMP/CMMC/GovCloud/AppExchange/AppSource validated in backend + Playwright (`test_compliance_dashboard.py`, `compliance-readiness.spec.ts`) |
| `/api/v1/notifications/push-subscriptions` | `200`; push-subscription list/create/delete lifecycle validated in backend + Playwright (`test_notifications_push.py`, `settings-notifications-workflow.spec.ts`) |
| `/api/v1/contacts/extract/{rfp_id}` + `/api/v1/contacts/search` + `/api/v1/contacts/agencies` | `200`; extraction fallback to `description`, auto-link to `linked_rfp_ids`, and agency-directory primary-contact linkage validated in `test_contacts.py` + Playwright `contacts-workflow.spec.ts` |
| `/api/v1/documents/past-performances/list` + match/narrative routes | `200`; canonical past-performance list/match/narrative paths validated in `test_documents.py` and aligned with frontend `pastPerformanceApi` |
| `/free-tier` route + auth/subscription links | Public PLG landing validated in Playwright (`search-plg-workflow.spec.ts`) and unit tests (`free-tier-page.test.tsx`) |
| Global search overlay (`Ctrl+K` / header icon) | Faceted semantic search modal validated in unit + Playwright (`global-search.test.tsx`, `header-search-trigger.test.tsx`, `search-plg-workflow.spec.ts`) |
| Capture workflow (`/capture`) | Playwright flow passed: create plan, add gate review, add/link partner, add competitor |
| Teaming workflow (`/teaming`) | Playwright flow passed: public partner discovery + request send/accept lifecycle + fit trend metrics + request-audit export (`teaming-workflow.spec.ts`) |
| Collaboration workflow (`/collaboration`) | Playwright flow passed: multi-workspace create + preset apply + invite handoff + second-user acceptance + governance approval + SLA/overdue metric visibility + audit-export request + portal workspace switching (`collaboration-workflow.spec.ts`) |
| Contracts workflow (`/contracts`) | Playwright flow passed: hierarchical contract create/select + modification + CLIN edit + deliverable + task + CPARS + status report |
| Reviews workflow (`/reviews`) | Playwright flow passed: scheduled review appears in dashboard and filter views |
| Backend integration suites | `169/169` passing on 2026-02-10 full backend pytest sweep (includes agents, workflow execution, push notifications, compliance readiness, data sources, sharepoint, and collaboration suites) |
| Frontend unit suites | `32/32` passing on 2026-02-10 (`vitest run`) including new dash voice and settings sharepoint integration assertions |
| Playwright suite | `58/58` passing on 2026-02-10 against deterministic local stack (`E2E_BASE_URL=http://localhost:3100`, backend `:8010`, `DEBUG=true`, `MOCK_AI=true`) |

## Integration Backlog (Prioritized)
1. Add invitation revocation/resend actions and invitation-aging SLAs in `/admin`.
2. Add role-targeted recipient routing for collaboration compliance digests.
3. Add NAICS/set-aside cohort drilldowns on teaming partner trends.
4. Add websocket telemetry threshold alerts + export for operational audits.
