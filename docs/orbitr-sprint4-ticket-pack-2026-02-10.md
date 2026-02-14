# Orbitr Sprint 4 Ticket Pack

Date: 2026-02-10
Source board: `/Users/demarioasquitt/Desktop/Projects/Entrepreneurial/govtech-sniper/docs/orbitr-execution-board-2026.md`
Sprint window: Weeks 7-8

## S4-01: Evidence Ingestion and Control Linkage Workflows

- Type: Feature
- Epic: `E-TRUST-02`
- Slice: `E-TRUST-02-S2`
- Owner role: `SEC`
- Priority: P0

### User story
As a compliance manager, I need evidence ingestion and linkage workflows so control status reflects real implementation artifacts.

### Scope
- Implement ingestion paths for manual and automated evidence.
- Link artifacts to controls with metadata (owner, timestamp, scope).
- Add control status derivation based on linked evidence quality.

### Acceptance criteria
- Evidence can be created, linked, and queried by control.
- Missing/stale evidence states are visible.
- Audit records exist for evidence lifecycle changes.

### Tests
- Unit: evidence validation and linkage rules.
- Integration: control-evidence API contracts.
- E2E: admin evidence workflow.

### Rollback
- Keep control state read-only if linkage processor fails.

## S4-02: Freshness Scoring Service

- Type: Feature
- Epic: `E-DATA-02`
- Slice: `E-DATA-02-S1`
- Owner role: `DATA`
- Priority: P1

### User story
As a capture operator, I need freshness scores to quickly judge whether opportunity data is actionable.

### Scope
- Implement freshness scoring by provider/source class.
- Add freshness SLA thresholds and breach states.
- Expose scores in diagnostics and list surfaces.

### Acceptance criteria
- Freshness score computed for all ingested opportunities.
- SLA breaches trigger visible warnings.
- Scoring latency does not degrade ingest throughput.

### Tests
- Unit: scoring thresholds and edge cases.
- Integration: score persistence and API exposure.
- E2E: freshness indicators visible in UI.

### Rollback
- Fallback to last-known freshness values if scorer unavailable.

## S4-03: Dedupe Confidence and Merge Policy

- Type: Feature
- Epic: `E-DATA-02`
- Slice: `E-DATA-02-S2`
- Owner role: `DATA`
- Priority: P1

### User story
As a user, I need duplicate opportunities merged reliably so pipeline views are accurate.

### Scope
- Add dedupe confidence model and merge policy.
- Support manual override for ambiguous duplicates.
- Log merge decisions for audit and debugging.

### Acceptance criteria
- Duplicate rate reduction trend is measurable.
- Low-confidence merges are held for review.
- Merge provenance is inspectable.

### Tests
- Unit: dedupe scoring and merge decision logic.
- Integration: ingest dedupe scenarios with realistic fixtures.
- E2E: merged result and override workflow.

### Rollback
- Disable auto-merge and switch to mark-only mode.

## S4-04: Customer Health Model v1

- Type: Feature
- Epic: `E-CS-01`
- Slice: `E-CS-01-S2`
- Owner role: `CS`
- Priority: P1

### User story
As customer success, I need health scoring to proactively intervene before churn risk escalates.

### Scope
- Define health score dimensions: activation, workflow completion, reliability exposure, support load.
- Add risk alerts and owner assignments.
- Create intervention status tracking.

### Acceptance criteria
- Health score generated for active accounts.
- High-risk accounts trigger alerts with owners.
- Intervention outcomes can be tracked over time.

### Tests
- Unit: score calculation and threshold logic.
- Integration: alert creation and status transitions.
- E2E: risk queue visibility and updates.

### Rollback
- Alert-only mode without score weighting if calibration drifts.

## S4-05: Scorecard Threshold Calibration and Baselines

- Type: Feature
- Epic: `E-PROP-01`
- Slice: `E-PROP-01-S3`
- Owner role: `PROP`
- Priority: P1

### User story
As proposal leadership, I need calibrated quality thresholds so scorecards reflect practical reviewer standards.

### Scope
- Tune thresholds by proposal type and section class.
- Add baseline snapshots for quarterly quality trend comparisons.
- Provide reviewer feedback capture for calibration loop.

### Acceptance criteria
- Threshold profiles are configurable and versioned.
- Reviewer feedback links to score outcomes.
- Baseline report generated for sprint close.

### Tests
- Unit: threshold profile selection.
- Integration: calibration persistence and retrieval.
- E2E: reviewer feedback capture in workflow.

### Rollback
- Revert to global default threshold profile.

## S4-06: Stability Gate for Stateful and Selector-Dense E2E Flows

- Type: Quality
- Epic: `OPS-002`
- Owner role: `QA`
- Priority: P0

### User story
As QA, I need hardened E2E patterns so state and selector ambiguity do not create false failures.

### Scope
- Enforce scoped locator patterns in selector-dense views.
- Add state-aware waits for async persistence actions.
- Add helper guidelines for role-scoped assertions.

### Acceptance criteria
- Flake rate declines on targeted workflows.
- New E2E tests include scoped selectors and async wait patterns.
- No strict-mode selector ambiguity in sprint-touched specs.

### Tests
- E2E reruns on impacted suites with repeated execution.
- Regression pass criteria documented.

### Rollback
- Temporarily quarantine known-flaky non-critical tests with tracked follow-up tickets.

## Sprint 4 Exit Checklist

- All six tickets meet acceptance criteria.
- Freshness/dedupe metrics and evidence linkage are observable in dashboards.
- Final test evidence logged from:
  - `pytest -q`
  - `vitest run`
  - `playwright test`
- No unresolved P0 data integrity or policy gaps.
