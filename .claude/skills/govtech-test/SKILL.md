---
name: govtech-test
description: GovTech Sniper Automated Security & Quality Testing - Systematically tests API endpoints for auth gaps, IDOR vulnerabilities, rate limiting, service correctness, and Celery task execution. Fixes issues found and writes regression tests.
---

# GovTech Sniper Automated Testing Workflow

Automates comprehensive security hardening and quality testing: scan endpoints, test auth, find IDOR bugs, verify rate limiting, test Celery tasks, write regression tests, fix issues found.

## Prerequisites

- Docker services running: `docker compose ps` (api, worker, db, redis healthy)
- API server at localhost:8000
- Frontend at localhost:3000 (for UI verification)

## Workflow Overview

```
[Phase 1: Security Audit]
    ↓
[Scan ALL endpoints for auth gaps]
    ↓
[Test IDOR on resource endpoints]
    ↓
[Verify rate limiting coverage]
    ↓
[Fix security issues found]
    ↓
[Phase 2: Service Tests]
    ↓
[Test each untested service]
    ↓
[Write unit tests for coverage]
    ↓
[Phase 3: Celery Task Tests]
    ↓
[Test each task module]
    ↓
[Verify task execution pipeline]
    ↓
[Phase 4: Integration Tests]
    ↓
[Test critical user flows]
    ↓
[Write regression tests]
    ↓
[Commit all fixes + tests]
```

## Phase 1: Security Audit

### 1a. Authenticate (get tokens for two different users)

```bash
# User 1 (primary)
TOKEN=$(curl -s 'http://localhost:8000/api/v1/auth/login' \
  -X POST -H 'Content-Type: application/json' \
  -d '{"email":"demario@gmail.com","password":"Wilson07"}' | jq -r '.access_token')

# User 2 (for IDOR testing) — create if needed
TOKEN2=$(curl -s 'http://localhost:8000/api/v1/auth/login' \
  -X POST -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"Wilson07"}' | jq -r '.access_token')
```

### 1b. Scan All Endpoints for Auth Gaps

For EVERY endpoint in `backend/app/api/routes/`, verify:

1. **Read the route file** — check if `Depends(get_current_user)` is present
2. **Test without auth** — curl without Bearer token, expect 401/403:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/ENDPOINT"
   ```
3. **If 200 without auth** → this is a **SECURITY BUG**. Fix immediately by adding `Depends(get_current_user)`.

**Endpoints that SHOULD be unauthenticated (whitelist):**
- `GET /health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/verify-email`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `POST /api/v1/webhook/*` (if using webhook secrets)

**Everything else MUST return 401 without a valid token.**

### 1c. IDOR Testing (Resource Ownership)

For every endpoint that takes a resource ID (rfp_id, proposal_id, etc.):

1. **Create a resource as User 1** (or use existing)
2. **Try to access it as User 2** — should get 403 or 404:
   ```bash
   # User 1's resource
   curl -s -w "\n%{http_code}" "http://localhost:8000/api/v1/rfps/$RFP_ID" \
     -H "Authorization: Bearer $TOKEN2"
   ```
3. **If User 2 can read/modify User 1's resource** → **IDOR BUG**. Fix by adding ownership check.

**Priority IDOR targets (most sensitive data):**

| Endpoint | Resource | Risk |
|----------|----------|------|
| `GET /api/v1/rfps/{id}` | RFP documents | HIGH — contains solicitation data |
| `GET /api/v1/draft/proposals/{id}` | Proposals | CRITICAL — contains bid strategy |
| `GET /api/v1/draft/proposals/{id}/sections` | Proposal sections | CRITICAL — proposal content |
| `POST /api/v1/draft/proposals/{id}/generate` | Generation trigger | CRITICAL — costs AI credits |
| `GET /api/v1/capture/plans/{id}` | Bid plans | HIGH — win strategy |
| `GET /api/v1/contracts/{id}` | Contracts | HIGH — contract details |
| `GET /api/v1/collaboration/workspaces/{id}` | Workspaces | HIGH — team data |
| `POST /api/v1/analyze/{id}` | Analysis trigger | HIGH — costs AI credits |
| `GET /api/v1/kb-intelligence/*` | Knowledge base | MEDIUM — company knowledge |
| `POST /api/v1/word-addin/ai/rewrite` | AI rewrite | MEDIUM — costs AI credits |

### 1d. Rate Limiting Verification

All AI/expensive endpoints MUST have `Depends(check_rate_limit)`:

```bash
# Rapid-fire test (10 requests in 2 seconds)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/v1/ENDPOINT" \
    -H "Authorization: Bearer $TOKEN" &
done
wait
```

**Endpoints that MUST be rate-limited:**
- `POST /api/v1/auth/login` (brute force prevention)
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/dash/ask` (AI — Gemini credits)
- `POST /api/v1/word-addin/ai/rewrite` (AI)
- `POST /api/v1/draft/proposals/*/generate` (AI — heavy)
- `POST /api/v1/analyze/*` (AI)
- `POST /api/v1/ingest/*` (compute-heavy)
- `GET /api/v1/search/*` (DB-heavy)
- `POST /api/v1/reports/*` (compute-heavy)
- `POST /api/v1/compliance-dashboard/*` (compute-heavy)

### 1e. Security Fix Protocol

When a security issue is found:

1. **Fix the code** — add `Depends(get_current_user)`, ownership check, or rate limit
2. **Write a regression test** in `backend/tests/` that verifies:
   - Unauthenticated access returns 401
   - Wrong-user access returns 403/404
   - Rate limit returns 429 after threshold
3. **Verify the fix** — curl to confirm
4. **Commit** — `fix(security): add auth guard to [endpoint]`

## Phase 2: Service Layer Testing

### Target: Untested Services

Write unit tests for each untested service. Priority order:

1. **auth_service.py** — JWT creation, validation, password hashing
2. **gemini_service/** — AI prompt construction, response parsing, error handling
3. **ingest_service.py** — RFP parsing, deduplication, validation
4. **compliance_checker.py** — Compliance rule evaluation
5. **workflow_engine.py** — Workflow state machine logic
6. **export_signing.py** — Audit trail integrity
7. **bid_decision_service.py** — Go/no-go scoring logic
8. **past_performance_matcher.py** — Win rate matching
9. **forecast_matcher.py** — Opportunity scoring
10. **policy_engine.py** — Policy rule evaluation

### Test Writing Protocol

For each service:

1. **Read the service file** — understand public methods and dependencies
2. **Identify edge cases**:
   - Null/empty inputs
   - Invalid data types
   - Missing required fields
   - Concurrent access
   - External service failures (mock these)
3. **Write test file** at `backend/tests/test_[service_name].py`:
   ```python
   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch
   from app.services.service_name import ServiceName

   class TestServiceName:
       """Tests for ServiceName."""

       @pytest.fixture
       def service(self):
           """Create service instance with mocked dependencies."""
           ...

       async def test_[method]_[scenario]_[expected](self, service):
           """Given [precondition], when [action], then [expected]."""
           ...
   ```
4. **Run the test**: `cd backend && python -m pytest tests/test_[service_name].py -v`
5. **Fix any failures**, then commit

### Test Quality Bar

- Each service gets at minimum:
  - 1 happy-path test per public method
  - 1 error/edge-case test per public method
  - Mock all external dependencies (DB, Redis, Gemini, etc.)
- Tests must pass independently (no shared state)
- Use `pytest.mark.asyncio` for async tests

## Phase 3: Celery Task Testing

### Target: All 8 Task Modules

Test each Celery task module:

| Module | Tasks to Test | Priority |
|--------|---------------|----------|
| `ingest_tasks.py` | SAM.gov scan, multi-source, daily digest | HIGH |
| `analysis_tasks.py` | RFP parsing, compliance analysis | HIGH |
| `generation_tasks.py` | Proposal section generation | CRITICAL |
| `document_tasks.py` | DOCX/PDF export | HIGH |
| `email_ingest_tasks.py` | Email parsing | MEDIUM |
| `signal_tasks.py` | Market signal processing | MEDIUM |
| `sharepoint_sync_tasks.py` | SharePoint push | MEDIUM |
| `maintenance_tasks.py` | Cache cleanup, audit purge | LOW |

### Task Test Protocol

For each task:

1. **Read the task code** — understand inputs, outputs, side effects
2. **Write test** with mocked Celery worker:
   ```python
   from unittest.mock import patch, MagicMock

   @patch("app.services.gemini_service.GeminiService")
   @patch("app.core.database.get_session")
   def test_task_name(mock_session, mock_gemini):
       from app.tasks.module import task_function
       result = task_function("test_id")
       assert result["status"] == "completed"
   ```
3. **Verify error handling** — what happens when the task fails?
4. **Verify idempotency** — running twice shouldn't corrupt data

## Phase 4: Critical Flow Integration Tests

### Flow 1: Ingest → Analyze → Draft → Export

The core proposal pipeline must work end-to-end:

```bash
# 1. Upload/ingest an RFP
curl -s -X POST "http://localhost:8000/api/v1/ingest/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_rfp.pdf" \
  -F "site_id=$SITE_ID"

# 2. Trigger analysis
curl -s -X POST "http://localhost:8000/api/v1/analyze/$RFP_ID" \
  -H "Authorization: Bearer $TOKEN"

# 3. Create proposal from analyzed RFP
curl -s -X POST "http://localhost:8000/api/v1/draft/proposals" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rfp_id": "'$RFP_ID'", "site_id": "'$SITE_ID'", "title": "Test Proposal"}'

# 4. Generate a section
curl -s -X POST "http://localhost:8000/api/v1/draft/proposals/$PROP_ID/sections/$SECTION_ID/generate" \
  -H "Authorization: Bearer $TOKEN"

# 5. Export to DOCX
curl -s -X POST "http://localhost:8000/api/v1/draft/proposals/$PROP_ID/export/docx" \
  -H "Authorization: Bearer $TOKEN" -o test_output.docx
```

### Flow 2: Auth Lifecycle

```bash
# Register → Login → Refresh → Protected endpoint → Logout
# Verify each step and that logout invalidates tokens
```

### Flow 3: Collaboration

```bash
# Create workspace → Invite member → Member accepts → Both access shared resource
# Verify access control at each step
```

## Execution Rules

### ONE Issue at a Time
Process issues sequentially:
1. Find issue
2. Fix issue
3. Write regression test
4. Verify fix
5. Commit
6. Next issue

### Fix Code, Not Symptoms
- Don't add workarounds — fix root causes
- Don't suppress errors — handle them properly
- Don't skip auth — add it

### Commit Protocol
After each fix batch (group related fixes):
```bash
# Stage specific files
git add backend/app/api/routes/fixed_file.py backend/tests/test_fixed.py

# Commit with conventional format
git commit -m "fix(security): add auth guards to analyze and draft endpoints

- Add Depends(get_current_user) to /analyze endpoints
- Add ownership check to GET /rfps/{id}
- Add rate limiting to /draft/generate
- Write regression tests for all fixes"
```

### Progress Tracking
After each phase, log progress:
```
Phase 1 Security: X/Y endpoints audited, Z issues fixed
Phase 2 Services: X/Y services tested, Z tests written
Phase 3 Celery: X/Y task modules tested
Phase 4 Integration: X/Y flows verified
```

## When Issues Are Found

### Security Issue
1. **Severity**: CRITICAL (fix immediately, no batching)
2. **Fix**: Add auth/ownership/rate-limit guard
3. **Test**: Write regression test proving unauthorized access fails
4. **Verify**: curl to confirm 401/403/429

### Service Bug
1. **Severity**: HIGH (fix before moving to next service)
2. **Fix**: Correct the logic
3. **Test**: Write test covering the bug scenario
4. **Verify**: Run test, confirm pass

### Missing Test Coverage
1. **Severity**: MEDIUM (batch write tests)
2. **Action**: Write tests for the uncovered code
3. **Verify**: Run tests, confirm pass

## Final Phase: Commit All Fixes

### 1. Run Full Verification
```bash
cd backend && ruff check app/
cd frontend && npx tsc --noEmit
docker compose ps  # all healthy
```

### 2. Review All Changes
```bash
git status
git diff --stat
```

### 3. Stage and Commit
Group by category:
- `fix(security): ...` for auth/IDOR/rate-limit fixes
- `test: ...` for new test files
- `refactor: ...` for code cleanup found along the way

### 4. Push Once
```bash
git push origin main
```

## Key Principles

1. **Security first** — Auth gaps are the highest priority. Fix before writing tests.
2. **Fix immediately** — Don't log issues for later. Fix them now.
3. **Regression tests for every fix** — No fix ships without a test proving it works.
4. **Verify everything** — curl endpoints, run tests, check logs. Never assume.
5. **One issue at a time** — Sequential processing prevents sloppy fixes.
6. **Commit frequently** — Small, focused commits with clear messages.
7. **Push once** — Batch all commits, push at session end (saves Render pipeline minutes).
