# Tech Debt Tracker

Last updated: 2026-02-13

## Oversized Files (>800 lines)

### Backend (Python)
| File | Lines | Status |
|------|-------|--------|
| `api/routes/collaboration.py` | 1,503 | Tracked |
| `api/routes/admin.py` | 1,037 | Tracked |
| `services/gemini_service.py` | 987 | Tracked |
| `api/routes/teaming_board.py` | 971 | Tracked |
| `api/routes/templates.py` | 868 | Tracked |
| `api/routes/integrations.py` | 784 | Warning |
| `api/routes/notifications.py` | 779 | Warning |
| `api/routes/intelligence.py` | 706 | Warning |
| `api/routes/draft/generation.py` | 705 | Warning |

### Frontend (TypeScript/React)
| File | Lines | Status |
|------|-------|--------|
| `collaboration/page.tsx` | 1,258 | Tracked |
| `contracts/page.tsx` | 1,094 | Tracked |
| `capture/page.tsx` | 1,059 | Tracked |
| `opportunities/[rfpId]/page.tsx` | 1,050 | Tracked |
| `analysis/[rfpId]/page.tsx` | 1,031 | Tracked |
| `opportunities/page.tsx` | 913 | Tracked |
| `teaming/page.tsx` | 844 | Tracked |
| `lib/api/misc.ts` | 656 | Warning |
| `settings/page.tsx` | 672 | Warning |
| `reports/page.tsx` | 624 | Warning |

## Architectural Debt

| Issue | Severity | Status | Notes |
|-------|----------|--------|-------|
| Frontend state explosion (42-49 hooks per page) | Medium | Open | collaboration, contracts, capture pages need useReducer |
| Frontend pages use raw useEffect instead of React Query | Medium | Open | Hooks exist (use-rfps.ts) but most pages don't use them |
| All dashboard pages are "use client" — no SSR | Low | Open | Would benefit from server components for initial data |
| Pyright has 494 pre-existing errors at basic mode | Low | Open | Warn-only, not blocking |

## Resolved Items

| Issue | Resolution Date | Notes |
|-------|----------------|-------|
| Missing security headers | 2026-02-13 | Added SecurityHeadersMiddleware |
| In-memory rate limiter | 2026-02-13 | Replaced with Redis-backed RedisRateLimiter |
| Docker Redis no healthcheck | 2026-02-13 | Added healthcheck to docker-compose.yml |
| Celery depends_on wrong services | 2026-02-13 | Fixed to depend on postgres+redis with health conditions |
| Secret key fallback in docker-compose | 2026-02-13 | Removed default fallback |
| No correlation ID in Celery tasks | 2026-02-13 | Added signal-based propagation |
| CI bandit scan non-blocking | 2026-02-13 | Made blocking at medium+ severity |
| API contract mismatches (FE/BE) | 2026-02-13 | Synced proposal.ts, rfp.ts types |
| No error boundaries | 2026-02-13 | Added error.tsx + loading.tsx |
