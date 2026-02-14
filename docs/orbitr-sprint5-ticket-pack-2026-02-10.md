# Orbitr Sprint 5 Ticket Pack

Date: 2026-02-10
Source board: `/Users/demarioasquitt/Desktop/Projects/Entrepreneurial/govtech-sniper/docs/orbitr-execution-board-2026.md`
Sprint window: Weeks 9-10

## S5-01: CUI Export Controls (Watermark + Redaction Policies)

- Type: Feature
- Epic: `E-TRUST-01`
- Slice: `E-TRUST-01-S3`
- Owner role: `SEC`
- Priority: P0

### User story
As a compliance-sensitive user, I need CUI-aware export controls so sensitive data is protected during document distribution.

### Scope
- Apply policy-driven watermarking for CUI exports.
- Apply redaction profiles where required by policy.
- Block export when policy prerequisites are not met.

### Acceptance criteria
- CUI exports are transformed per policy.
- Non-compliant export attempts are denied with explicit reason.
- Export actions emit security-grade audit events.

### Tests
- Unit: redaction/watermark policy decisions.
- Integration: export route behavior by classification and role.
- E2E: end-to-end export scenarios for allowed/denied cases.

### Rollback
- Per-format fallback to block exports rather than allow insecure passthrough.

## S5-02: Compliance Package Export v1

- Type: Feature
- Epic: `E-PROP-02`
- Slice: `E-PROP-02-S1`
- Owner role: `PROP`
- Priority: P1

### User story
As a proposal team lead, I need a consolidated compliance package so reviews and submissions are traceable.

### Scope
- Generate bundle containing matrix, outline, requirement mapping, and section statuses.
- Include provenance metadata and generation timestamp.
- Provide download action in proposal workspace.

### Acceptance criteria
- Bundle generated for valid proposal contexts.
- Package content is deterministic and complete per contract.
- Missing dependency states are handled with actionable messages.

### Tests
- Unit: package assembly logic.
- Integration: export API contract and file manifest assertions.
- E2E: workspace package download flow.

### Rollback
- Hide package action if generator service unhealthy.

## S5-03: SharePoint Diagnostics Panel + Remediation Actions

- Type: Feature
- Epic: `E-WORK-02`
- Slice: `E-WORK-02-S2`
- Owner role: `INTG`
- Priority: P1

### User story
As an integration admin, I need diagnostics and guided remediation so sync failures can be resolved quickly.

### Scope
- Add diagnostics panel showing sync state, recent errors, and retry windows.
- Add one-click remediation actions for retriable failure classes.
- Add correlation IDs to sync events.

### Acceptance criteria
- Diagnostics reflect latest sync outcomes.
- Remediation actions are role-protected and audited.
- Correlation IDs allow trace across logs and UI.

### Tests
- Unit: diagnostics state mapper.
- Integration: diagnostics/remediation API contracts.
- E2E: failing sync -> remediation -> recovery path.

### Rollback
- Read-only diagnostics mode if remediation actions are unstable.

## S5-04: Live Connector Expansion Wave 2

- Type: Feature
- Epic: `E-DATA-01`
- Slice: `E-DATA-01-S3`
- Owner role: `DATA`
- Priority: P1

### User story
As capture teams scale, we need additional live sources to maintain discovery advantage.

### Scope
- Convert next high-priority sample provider to live integration.
- Add rate-limit handling, health checks, and freshness telemetry.
- Validate dedupe interactions with existing live sources.

### Acceptance criteria
- Provider operates in live mode in staging.
- Health/freshness metrics exposed and alertable.
- No critical ingest regressions from added source.

### Tests
- Unit: provider parser and normalizer.
- Integration: search/ingest/health contracts.
- E2E: discovery workflow includes new source results.

### Rollback
- Feature-toggle provider back to sample mode with explicit diagnostics state.

## S5-05: Passkey/WebAuthn Rollout (Phase 1)

- Type: Feature
- Epic: `E-TRUST-03`
- Slice: `E-TRUST-03-S3`
- Owner role: `SEC`
- Priority: P0

### User story
As a privileged user, I need phishing-resistant authentication to improve account security.

### Scope
- Add passkey registration and authentication flow for supported clients.
- Add account-level passkey management UI.
- Integrate with org security policy controls.

### Acceptance criteria
- Users can register and use passkeys on supported platforms.
- Auth fallback paths are explicit when passkeys unavailable.
- Passkey lifecycle events are audited.

### Tests
- Unit: challenge/response validation.
- Integration: passkey auth endpoints.
- E2E: browser-based passkey flow with deterministic mocks where required.

### Rollback
- Keep passkey feature behind org-level toggle.

## S5-06: Contract and Proxy Path Drift Test Expansion

- Type: Quality
- Epic: `OPS-002`
- Owner role: `QA`
- Priority: P0

### User story
As QA, I need stronger proxy-aware contract checks so route mismatches never silently ship.

### Scope
- Expand contract tests for frontend proxy paths and backend mounted paths.
- Add assertions for versioned/unversioned aliases where intentionally supported.
- Ensure Playwright network assertions match proxied URLs robustly.

### Acceptance criteria
- All sprint-touched endpoints have explicit proxy-aware checks.
- No unresolved route drift for touched modules.
- Contract test suite documents intended aliases.

### Tests
- Unit: route ownership audit checks.
- Integration: endpoint contract assertions.
- E2E: affected journeys rerun with network assertion checks.

### Rollback
- Temporarily allow legacy alias behavior with deprecation warning and expiry date.

## Sprint 5 Exit Checklist

- All six tickets meet acceptance criteria.
- Trust-critical export and auth flows validated in browser.
- Final evidence logged from:
  - `pytest -q`
  - `vitest run`
  - `playwright test`
- No unresolved P0 security/compliance blockers.
