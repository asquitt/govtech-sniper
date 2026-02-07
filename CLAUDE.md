# AGENTS.md

## Mission
Build a GovTech proposal automation platform that is reliable, secure, and delightful for customers. Quality, correctness, and speed to value are non-negotiable.

## Agent Behavior
- Default to the best action without asking multiple questions.
- Ask for clarification only when blocked or when choices materially change outcomes.
- Prefer making progress over debate; document decisions and move forward.

## Quality Bar (Non-Negotiable)
- Every feature must ship with tests.
- No broken builds, no flaky tests.
- Prefer simple, correct, and maintainable solutions.
- Security and data integrity are first-class.

## Testing Requirements (Comprehensive)
Every feature must include:
- Unit tests for core logic.
- Integration tests for API endpoints and DB operations.
- E2E tests for critical user flows.

### Test Coverage Targets
- Unit + Integration: >= 85% for new/changed code.
- E2E: 100% coverage of critical paths (ingest -> analyze -> draft -> export).

### Test Principles
- Tests must be deterministic and isolated.
- No shared global state; reset DB between tests.
- Use realistic fixtures, not toy data.
- Prefer contract tests for external integrations.
- Add regression tests for every bug fixed.

## CI / CD Expectations
- CI runs on every push: lint, type check, unit, integration, and E2E.
- Failing CI means no merge.
- Add or update test scripts as needed.

## Git Hygiene (Regular Commits and Pushes)
- Commit after each coherent unit of work (feature slice, refactor, or fix).
- Use descriptive commit messages:
  - feat: add opportunity snapshot diffing
  - fix: prevent duplicate SAM.gov ingest
  - test: add integration coverage for proposals
- Push at least once per day or after every major milestone.
- Never rewrite history unless explicitly requested.

## Code Standards
- Prefer clarity and explicitness over cleverness.
- Avoid premature abstractions.
- Keep functions small and purposeful.
- Add concise comments only where logic is non-obvious.

## Security and Compliance
- Treat all data as sensitive (CUI-level handling).
- Enforce RBAC checks on all protected endpoints.
- Log security-relevant events (auth, access, data export).

## Documentation
- Update docs when behavior changes.
- For non-obvious design choices, add a short rationale in docs/ or ADRs.

## UX and Product Fit
- Optimize for enterprise workflows (Word, SharePoint, SSO).
- Every workflow must reduce time and increase compliance confidence.

## Mandatory Pre-Commit Testing (ENFORCED)

**No code ships without functional verification. This is non-negotiable.**

### Testing Sequence (before ANY commit)
1. **Type check**: `npx tsc --noEmit` (frontend) or `python -c "import ast; ast.parse(...)"` (backend)
2. **Build check**: `npx next build` must pass (frontend)
3. **Unit test new logic**: Write and run targeted tests for new functions (e.g., `_render_html_to_docx`)
4. **API verification**: `curl` new/changed endpoints with realistic payloads
5. **Docker health**: `docker compose up -d && docker compose ps` — all services healthy
6. **Fix failures before committing** — never commit broken code

### What Must Be Tested Per Change Type

| Change | Required Tests |
|--------|---------------|
| New API endpoint | curl with valid/invalid payloads, check response schema |
| New React component | Next.js build passes, component renders (no runtime errors) |
| DB model change | Create table, insert row, query back — verify schema |
| Export/generation | Run function with sample data, assert output structure |
| Frontend page split | Next.js build passes, page loads without errors |

### Test Commands
```bash
# Frontend
npx tsc --noEmit                    # Type check (excludes test files for build)
npx next build                      # Full build verification
node -e "..."                       # Quick function-level tests

# Backend
python -c "from app.module import func; func(test_data)"  # Direct function test
curl -s http://localhost:8000/api/v1/endpoint              # API test
docker compose exec api python -c "..."                    # In-container test

# Docker
docker compose up -d && docker compose ps                  # All services healthy
docker compose logs <service> --tail 20                    # Check for errors
```

### Never Do
- Commit code that only passes `tsc` without testing actual behavior
- Skip build verification ("it compiled so it works")
- Assume page splits don't break rendering
- Ship export changes without testing with sample HTML/plain-text content

## Definition of Done
- Feature works end-to-end in dev and staging.
- All tests pass locally and in CI.
- Functional verification completed (API curls, build checks, Docker health).
- Docs updated.
- Changes committed and pushed.

## Codebase Hygiene

### Rate Limiting
- All public/expensive endpoints must use `Depends(check_rate_limit)` from `app.api.deps`.
- Applies to: auth (login/register), AI endpoints (dash, rewrite), ingestion, search.

### Stub/Scaffold Code
- No stub code ships to production. If a feature isn't implemented, don't register it.
- If temporary scaffolding is needed during development, mark with `# TODO(stub): <reason>` and track in `docs/TECH_DEBT.md`.

### Secret Key Security
- Secret keys must never have usable defaults in production.
- `main.py` lifespan raises `RuntimeError` if `SECRET_KEY` or `AUDIT_EXPORT_SIGNING_KEY` are defaults in non-debug mode.

### Upload Size Enforcement
- `MaxUploadSizeMiddleware` in `main.py` rejects requests exceeding `max_upload_size_mb` from config.
- Config default: 50MB. Override via `MAX_UPLOAD_SIZE_MB` env var.

### CORS
- Production origins configured via `CORS_ORIGINS` env var (comma-separated).
- Default: localhost only. Must be set for deployment.

### AI Endpoints
- All AI-powered endpoints (Dash `/ask`, Word add-in `/ai/rewrite`) must use real Gemini calls.
- `settings.mock_ai` provides deterministic fallback for testing only.
- Use Flash model for latency-sensitive operations (rewrite), Pro for deep analysis.

## When In Doubt
- Favor reliability and data correctness.
- Ask only when blocked.
- Ship small, tested increments frequently.
