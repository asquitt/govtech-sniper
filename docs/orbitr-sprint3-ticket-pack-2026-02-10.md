# Orbitr Sprint 3 Ticket Pack

Date: 2026-02-10
Source board: `/Users/demarioasquitt/Desktop/Projects/Entrepreneurial/govtech-sniper/docs/orbitr-execution-board-2026.md`
Sprint window: Weeks 5-6

## S3-01: Org MFA Policy Modes

- Type: Feature
- Epic: `E-TRUST-03`
- Slice: `E-TRUST-03-S1`
- Owner role: `SEC`
- Priority: P0

### User story
As an org admin, I need enforceable MFA policy modes so identity risk is controlled by tenant policy.

### Scope
- Add org-level MFA policy settings (`optional`, `required`, `required_for_privileged`).
- Enforce policy on login/session refresh paths.
- Surface policy status and compliance in admin UI.

### Acceptance criteria
- Users in enforced orgs cannot bypass policy.
- Policy evaluation respects organization scope (`users.organization_id`).
- Admin UI shows current policy and affected user counts.

### Tests
- Unit: policy resolver logic.
- Integration: auth routes under each policy mode.
- E2E: login behavior by role and policy.

### Rollback
- Emergency toggle to `optional` at org scope with audit record.

## S3-02: Step-Up Auth for Privileged Export Actions

- Type: Feature
- Epic: `E-TRUST-03`
- Slice: `E-TRUST-03-S2`
- Owner role: `SEC`
- Priority: P0

### User story
As a security owner, I need step-up auth for high-risk actions so compromised sessions have reduced blast radius.

### Scope
- Define privileged actions requiring step-up (proposal export, audit export, sensitive sharing).
- Add step-up token/challenge flow with short TTL.
- Add denial and expiry handling UX.

### Acceptance criteria
- Privileged actions require fresh step-up proof.
- Expired/invalid step-up state is denied with actionable UI.
- All privileged decisions are audit logged.

### Tests
- Unit: step-up token lifecycle.
- Integration: protected route enforcement.
- E2E: pass/fail step-up scenarios.

### Rollback
- Configurable action list to narrow scope temporarily.

## S3-03: Word Sync Conflict Detection Foundation

- Type: Feature
- Epic: `E-WORK-01`
- Slice: `E-WORK-01-S1`
- Owner role: `INTG`
- Priority: P1

### User story
As a proposal writer, I need conflict detection when multiple edits occur so content integrity is preserved.

### Scope
- Add deterministic conflict detection rules for push/pull operations.
- Persist conflict metadata and state transitions.
- Expose conflict flags in taskpane/workspace.

### Acceptance criteria
- Conflicts are detected consistently across host and browser fallback paths.
- Conflict state survives refresh and can be inspected.
- No silent overwrite on conflict.

### Tests
- Unit: conflict rule matrix.
- Integration: word-addin session + event contracts.
- E2E: office-host conflict scenario.

### Rollback
- Fall back to read-only mode when conflict engine unavailable.

## S3-04: SharePoint Retry-After + Backoff Compliance

- Type: Feature
- Epic: `E-WORK-02`
- Slice: `E-WORK-02-S1`
- Owner role: `INTG`
- Priority: P1

### User story
As an integration operator, I need standards-compliant throttling behavior so sync remains reliable under provider limits.

### Scope
- Parse and honor `Retry-After` semantics.
- Implement exponential backoff with jitter and bounded retries.
- Add telemetry for throttling events and retry outcomes.

### Acceptance criteria
- Throttled responses do not trigger tight retry loops.
- Retry windows are config-driven and observable.
- User-facing status surfaces actionable countdown/retry info.

### Tests
- Unit: backoff and retry-window logic.
- Integration: simulated throttling response handling.
- E2E: sync flow under throttling simulation.

### Rollback
- Backoff policy override to safe defaults via config.

## S3-05: Provider Conversion Wave 1 (Two High-Value Sources)

- Type: Feature
- Epic: `E-DATA-01`
- Slice: `E-DATA-01-S2`
- Owner role: `DATA`
- Priority: P1

### User story
As a capture lead, I need live opportunity feeds from top-value sources so discovery quality improves materially.

### Scope
- Promote two highest-priority sample sources to live ingestion.
- Add provider contract tests with realistic fixtures.
- Add health and freshness checks for each converted provider.

### Acceptance criteria
- Both providers return live data in dev/staging path.
- Ingest creates deduped opportunities with stable identifiers.
- Health endpoints report actionable status.

### Tests
- Unit: provider mapping/normalization.
- Integration: search/ingest/health contracts.
- E2E: settings data-source + opportunities ingestion workflow.

### Rollback
- Per-provider failover to sample mode with explicit status banner.

## S3-06: Rewrite Delta Scoring in Proposal Workspace

- Type: Feature
- Epic: `E-PROP-01`
- Slice: `E-PROP-01-S2`
- Owner role: `PROP`
- Priority: P1

### User story
As a reviewer, I need before/after quality deltas on rewrites so we can choose the best revision quickly.

### Scope
- Compute and display quality delta for rewritten sections.
- Highlight improvements/regressions by scoring dimension.
- Persist rewrite comparison metadata.

### Acceptance criteria
- Every rewrite shows delta summary.
- Regression deltas are clearly flagged.
- Comparison data remains accessible in history view.

### Tests
- Unit: delta computation logic.
- Integration: rewrite endpoint + score persistence.
- E2E: rewrite action and delta visibility.

### Rollback
- If delta engine fails, rewrite still completes with `delta_unavailable` fallback.

## Sprint 3 Exit Checklist

- All six tickets meet acceptance criteria.
- Critical auth and integration flows pass deterministic E2E stack validation.
- Final run evidence logged from:
  - `pytest -q`
  - `vitest run`
  - `playwright test` (targeted + milestone sweep)
- No unresolved P0 identity/security regressions.
