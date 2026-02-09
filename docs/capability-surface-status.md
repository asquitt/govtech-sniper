# Capability Surface Status

Purpose: maintain a route-level, live-verified status map of surfaced and hidden capabilities, with explicit evidence from Playwright and API contract scans.

## Status Legend
- `Healthy`: Route is reachable in live UI and no unexpected API/runtime errors were observed.
- `Guarded`: Route is reachable but returns expected authorization guards for current test identity.
- `Drift`: Contract mismatch or runtime issue found; fix in progress.

## Latest Comprehensive Sweep
- Date: 2026-02-09
- Method: authenticated Playwright route sweep (`/tmp/gts-comprehensive-ui-sweep-final.json`) + frontend static API contract scan (`/tmp/frontend-static-api-method-scan.json`)
- Routes checked: 30
- Result: 29 `Healthy`, 1 `Guarded` (`/admin` for non-org user)
- Static API contract check: 146 frontend API call signatures scanned via proxy; 0 redirect/404 contract failures after fixes

## Route Status (Live UI)
| Route | Status | Evidence |
| --- | --- | --- |
| `/opportunities` | Healthy | Loads with no unexpected API failures |
| `/analysis` | Healthy | Loads with no unexpected API failures |
| `/proposals` | Healthy | Loads with no unexpected API failures |
| `/knowledge-base` | Healthy | Loads with no unexpected API failures |
| `/reviews` | Healthy | Loads with no unexpected API failures |
| `/dash` | Healthy | Loads with no unexpected API failures |
| `/capture` | Healthy | Loads with no unexpected API failures |
| `/teaming` | Healthy | Loads with no unexpected API failures |
| `/collaboration` | Healthy | Loads with no unexpected API failures |
| `/contacts` | Healthy | Loads with no unexpected API failures |
| `/contracts` | Healthy | Root proxy rewrite validated (`/api/contracts` 200) |
| `/revenue` | Healthy | Loads with no unexpected API failures |
| `/pipeline` | Healthy | Loads with no unexpected API failures |
| `/forecasts` | Healthy | Loads with no unexpected API failures |
| `/analytics` | Healthy | Loads with no unexpected API failures |
| `/intelligence` | Healthy | Loads with no unexpected API failures |
| `/events` | Healthy | Loads with no unexpected API failures |
| `/signals` | Healthy | Loads with no unexpected API failures |
| `/compliance` | Healthy | Loads with no unexpected API failures |
| `/reports` | Healthy | Loads with no unexpected API failures |
| `/settings` | Healthy | `/api/teams` root rewrite fix verified |
| `/settings/integrations` | Healthy | Loads with no unexpected API failures |
| `/settings/data-sources` | Healthy | Loads with no unexpected API failures |
| `/settings/email-ingest` | Healthy | Loads with no unexpected API failures |
| `/settings/subscription` | Healthy | Loads with no unexpected API failures |
| `/settings/workflows` | Healthy | Loads with no unexpected API failures |
| `/templates` | Healthy | Marketplace page reachable; template categories contract fixed |
| `/word-addin` | Healthy | Redirects to taskpane; browser-safe script loading in place |
| `/word-addin/taskpane` | Healthy | No React mount warning; no Office telemetry host failure in browser mode |
| `/admin` | Guarded | Expected `403` for non-admin/non-org user, no `500` |

## Contract Drift Fixes (This Session)
| Item | Previous State | Current State |
| --- | --- | --- |
| `GET /templates/categories/list` | Frontend call path existed but returned `404` | Frontend now uses `/templates/categories`; backend alias `/templates/categories/list` added for backward compatibility |
| `GET /notifications/deadlines` | Frontend client method existed but backend route missing (`404`) | Backend route implemented with user-scoped deadline filtering and tests |
| Word add-in runtime in plain browser | React mount warning + Office telemetry DNS failure | Office.js loading gated to likely Office hosts; browser fallback remains functional without runtime noise |

## Orphaned/Hidden Capability Notes
- Enterprise APIs (`/scim/v2`, `/webhooks`, `/secrets`) remain backend-capable but lack primary dashboard discoverability.
- Template and word-addin capabilities are now reachable without runtime failures in browser mode; discoverability/product placement still needs explicit UX decision.
