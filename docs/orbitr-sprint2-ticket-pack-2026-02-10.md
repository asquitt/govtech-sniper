# Orbitr Sprint 2 Ticket Pack

Date: 2026-02-10
Source board: `/Users/demarioasquitt/Desktop/Projects/Entrepreneurial/govtech-sniper/docs/orbitr-execution-board-2026.md`
Sprint window: Weeks 3-4

## S2-01: Policy Decision Engine v1 (Export/Share/Download)

- Type: Feature
- Epic: `E-TRUST-01`
- Slice: `E-TRUST-01-S2`
- Owner role: `SEC`
- Priority: P0

### User story
As an enterprise admin, I need policy decisions enforced consistently for sensitive actions so access control is auditable and deterministic.

### Scope
- Implement policy rules for export/share/download with inputs: role, classification, organization policy.
- Add decision outputs: `allow`, `deny`, `step_up`.
- Enforce on selected high-risk routes.

### Acceptance criteria
- 100% of scoped actions call policy engine before execution.
- Denied actions return consistent error contract.
- Policy decision is logged in audit metadata.

### Tests
- Unit: policy matrix by role/classification/action.
- Integration: route enforcement and response contract.
- E2E: allowed, denied, and step-up flows.

### Rollback
- Route-level feature flag to temporarily disable strict enforcement for emergency rollback.

## S2-02: Provider Maturity Matrix in Admin Diagnostics

- Type: Feature
- Epic: `E-DATA-01`
- Slice: `E-DATA-01-S1`
- Owner role: `DATA`
- Priority: P1

### User story
As an operator, I need visibility into provider maturity state so we can prioritize productionization and communicate coverage risk.

### Scope
- Add maturity state for each source: `Live`, `Hybrid`, `Sample`.
- Surface maturity, freshness, and health in admin diagnostics.
- Add source-level metadata contract for UI consumption.

### Acceptance criteria
- All registered providers display maturity state.
- Freshness timestamp present for each provider.
- Diagnostics page renders without blocking core actions during source failures.

### Tests
- Unit: provider metadata schema validation.
- Integration: `/data-sources` + diagnostics API contracts.
- E2E: admin diagnostics view and filtering.

### Rollback
- Keep metadata additive; fallback to default `Unknown` maturity if provider metadata missing.

## S2-03: Proposal Quality Scorecard v1

- Type: Feature
- Epic: `E-PROP-01`
- Slice: `E-PROP-01-S1`
- Owner role: `PROP`
- Priority: P1

### User story
As a proposal manager, I need quality scoring on generated sections so review can focus on high-risk content first.

### Scope
- Implement v1 scoring dimensions: requirement coverage and citation confidence.
- Show score and reason metadata in proposal workspace.
- Persist score history for generated/re-generated sections.

### Acceptance criteria
- Every generated section has a score object.
- Low-confidence sections are clearly flagged.
- Scoring does not block draft generation path.

### Tests
- Unit: score calculation logic with deterministic fixtures.
- Integration: section generation + score persistence.
- E2E: workspace shows score badges and details.

### Rollback
- If scoring pipeline fails, generation still succeeds with `score_unavailable` fallback state.

## S2-04: Onboarding Checklist v1 + Activation Telemetry

- Type: Feature
- Epic: `E-CS-01`
- Slice: `E-CS-01-S1`
- Owner role: `CS`
- Priority: P1

### User story
As a new customer, I need a guided setup checklist so I can reach first proposal value quickly.

### Scope
- Define onboarding milestones for first value path.
- Track milestone completion timestamps.
- Expose activation metrics in reporting dashboards.

### Acceptance criteria
- Onboarding milestones are visible and actionable.
- Completion telemetry is emitted for each milestone.
- Onboarding UI remains resilient across optional field variations.

### Tests
- Unit: onboarding state transitions.
- Integration: onboarding progress endpoints and timestamp capture.
- E2E: guided flow completion for core milestones.

### Rollback
- Fallback to existing onboarding widget if milestone API errors occur.

## S2-05: Error Budget Calculation + Release Gate Prototype

- Type: Platform
- Epic: `E-REL-01`
- Slice: `E-REL-01-S2`
- Owner role: `PLAT`
- Priority: P0

### User story
As release owner, I need an error-budget gate so unstable releases do not ship.

### Scope
- Define burn-rate formulas for critical path SLOs.
- Implement CI release check that reads error budget state.
- Add manual override protocol with audit trail.

### Acceptance criteria
- Release check fails when burn threshold exceeds defined limit.
- Override path requires explicit reason and actor identity.
- Gate status visible in pipeline output.

### Tests
- Unit: burn-rate calculations.
- Integration: CI check behavior with seeded metric states.
- E2E: N/A.

### Rollback
- Switch gate to warning-only mode under emergency policy.

## S2-06: Contract Drift Guardrail for New/Changed APIs

- Type: Quality
- Epic: `OPS-002`
- Owner role: `QA`
- Priority: P0

### User story
As QA, I need route/client contract checks to prevent frontend/backend path drift.

### Scope
- Enforce contract assertions for all newly touched API paths.
- Add test utility to validate frontend call paths against mounted backend routes.
- Include proxy-aware URL matching for Playwright API intercept assertions.

### Acceptance criteria
- New/changed endpoints have explicit contract tests.
- Playwright response matchers use stable suffix/pattern strategy.
- No unresolved contract drift in sprint closeout.

### Tests
- Unit: route ownership/contract utility checks.
- Integration: endpoint path assertions.
- E2E: targeted flows for touched APIs.

### Rollback
- If contract utility fails unexpectedly, allow temporary per-suite suppressions with issue link and expiry.

## Sprint 2 Exit Checklist

- All six tickets meet acceptance criteria.
- Final evidence commands executed and logged:
  - `pytest -q`
  - `vitest run`
  - `playwright test` (impacted + milestone sweep)
- Tracker docs updated from final run counts.
- No unresolved P0 policy or reliability defects.
