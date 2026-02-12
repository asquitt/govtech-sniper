# Orbitr Sprint 1 Ticket Pack

Date: 2026-02-10
Source board: `/Users/demarioasquitt/Desktop/Projects/Entrepreneurial/govtech-sniper/docs/orbitr-execution-board-2026.md`
Sprint window: Weeks 1-2

## S1-01: Add Classification Model to Core Entities

- Type: Feature
- Epic: `E-TRUST-01`
- Owner role: `SEC`
- Priority: P0

### User story
As an enterprise admin, I need every sensitive object to carry a classification label so policy enforcement is deterministic.

### Scope
- Add classification enum (`public`, `internal`, `fci`, `cui`) to target entities.
- Add migration and defaults for existing records.
- Expose classification in API read/write contracts where appropriate.

### Acceptance criteria
- Migration applies cleanly to existing data.
- New and existing objects return valid classification state.
- Classification cannot be set to invalid values.

### Tests
- Unit: enum and model validation.
- Integration: CRUD contracts for classified entities.
- E2E: create/edit/read classified object path.

### Rollback
- Reversible migration and fallback default behavior documented.

## S1-02: Policy Decision Engine Skeleton

- Type: Feature
- Epic: `E-TRUST-01`
- Owner role: `SEC`
- Priority: P0

### User story
As a platform operator, I need a single decision point for sensitive actions so access outcomes are consistent.

### Scope
- Build policy service returning `allow`, `deny`, `step_up`.
- Initial action set: export, share, download.
- Wire policy service in API middleware/dependency layer for selected routes.

### Acceptance criteria
- Policy engine invoked on all scoped actions.
- Policy result is enforced and machine-loggable.
- No direct bypass path remains for scoped routes.

### Tests
- Unit: rule evaluation matrix.
- Integration: route-level allow/deny coverage.
- E2E: blocked and allowed action flows.

### Rollback
- Feature flag for engine enforcement scope.

## S1-03: Control-Evidence Registry Schema v1

- Type: Feature
- Epic: `E-TRUST-02`
- Owner role: `SEC`
- Priority: P0

### User story
As a compliance lead, I need a structured evidence registry so trust claims are auditable.

### Scope
- Add models for controls, evidence artifacts, and mappings.
- Create baseline API for creating/listing evidence and links.
- Add audit events for evidence actions.

### Acceptance criteria
- Control and evidence records persist with required metadata.
- Evidence can be linked to controls.
- Audit entries generated for create/update/link operations.

### Tests
- Unit: mapping and required fields validation.
- Integration: create/list/link contracts.
- E2E: basic registry workflow in admin surface.

### Rollback
- Migration rollback path and data retention notes included.

## S1-04: Secure SDLC CI Gate Baseline

- Type: Platform
- Epic: `E-TRUST-04`
- Owner role: `PLAT`
- Priority: P0

### User story
As engineering leadership, we need mandatory baseline security gates in CI to prevent unsafe releases.

### Scope
- Add dependency scanning gate.
- Add secret scanning gate.
- Add static security scan baseline.
- Define fail conditions and waiver protocol.

### Acceptance criteria
- CI fails on configured severity thresholds.
- Waiver mechanism documented and auditable.
- Gate status visible in PR checks.

### Tests
- CI integration checks in staging branch.
- Seeded failing cases demonstrate gate behavior.

### Rollback
- Temporary bypass only via emergency change policy.

## S1-05: Critical Path SLO Definitions + Metrics Stubs

- Type: Platform
- Epic: `E-REL-01`
- Owner role: `PLAT`
- Priority: P0

### User story
As operators, we need SLOs and instrumentation for critical flows to control reliability.

### Scope
- Define SLO targets for ingest/analyze/draft/export.
- Add metric emitters and dashboard stubs.
- Add alert thresholds and ownership.

### Acceptance criteria
- SLO definitions approved and published.
- Metrics visible in dashboard for all four flows.
- Alerting rules created for error budget burn.

### Tests
- Integration tests validating metric emission.
- Alert rule dry-run in staging.

### Rollback
- Alert-only mode if dashboard pipeline has issues.

## S1-06: Program Governance Kickoff

- Type: Ops
- Epic: `OPS-001`
- Owner role: `EPM`
- Priority: P0

### User story
As program leadership, we need governance cadence and decision logs to avoid delivery drift.

### Scope
- Weekly milestone review cadence.
- Biweekly architecture/security review.
- Risk register and decision log template.
- KPI baseline report from current telemetry.

### Acceptance criteria
- All recurring ceremonies scheduled.
- Risk register initialized with owners.
- KPI baseline report published and reviewed.

### Tests
- N/A (process deliverable), but completion requires artifacts in repo/docs.

### Rollback
- N/A

## Sprint 1 Exit Checklist

- All six tickets meet acceptance criteria.
- Final test evidence recorded from exact commands:
  - `pytest -q`
  - `vitest run`
  - `playwright test` (impacted workflows minimum, full sweep for milestone close)
- Capability docs updated with any newly surfaced routes/capabilities.
- No unresolved P0 defects.
