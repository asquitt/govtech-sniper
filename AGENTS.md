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

## Live UI Validation
- Validate critical paths in a real browser with Playwright before closing work.
- For local development without external dependencies (Redis, third-party APIs), use deterministic mock data and synchronous fallbacks so ingest -> analyze -> draft -> export can still be exercised end-to-end.
- Capture and fix live UI/API failures immediately, then add/extend regression tests for each fix.

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

## Agent Learning Memory
- Persistent mistakes log location: `docs/agent-learning-log.md`
- When a mistake is discovered, append an entry to `docs/agent-learning-log.md` in the same work session.
- Before starting significant implementation, review the latest entries in `docs/agent-learning-log.md` and apply listed prevention checklists.

## Capability Integration Tracker
- Persistent capability tracker location: `docs/capability-integration-tracker.md`
- Keep `docs/capability-integration-tracker.md` updated as features are verified, integrated, or found orphaned.
- When hidden/orphaned capabilities are discovered, add concrete integration tasks and update status in the same work session.

## UX and Product Fit
- Optimize for enterprise workflows (Word, SharePoint, SSO).
- Every workflow must reduce time and increase compliance confidence.

## Definition of Done
- Feature works end-to-end in dev and staging.
- All tests pass locally and in CI.
- Docs updated.
- Changes committed and pushed.

## When In Doubt
- Favor reliability and data correctness.
- Ask only when blocked.
- Ship small, tested increments frequently.
