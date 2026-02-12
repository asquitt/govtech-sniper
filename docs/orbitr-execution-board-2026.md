# Orbitr Execution Board (2026)

Date: 2026-02-10
Companion strategy doc: `/Users/demarioasquitt/Desktop/Projects/Entrepreneurial/govtech-sniper/docs/orbitr-world-class-enhancement-plan-2026.md`
Planning horizon: 12 months
Execution cadence: 2-week sprints

## 1) How to Use This Board

This board translates strategy into an operator-ready system:
- `Epic` = multi-sprint outcome tied to business and trust KPIs.
- `Feature Slice` = shippable increment with end-to-end validation.
- `Gate` = required evidence to move to next stage.
- `Owner` = single accountable role (can delegate contributors).

Rules:
- Every slice ships with unit + integration + E2E coverage.
- Every trust-sensitive change includes audit log events and policy tests.
- Every release includes rollback criteria and metric instrumentation.
- No epic closes without KPI movement and customer evidence.

## 2) Program North Star

### 12-month measurable targets
- Reduce median proposal cycle time by >= 40%.
- Increase opportunities pursued per proposal FTE by >= 2x.
- Achieve >= 99.0% success on critical path `ingest -> analyze -> draft -> export`.
- Reach enterprise trust readiness milestones (CUI policy enforcement live, evidence registry live, continuous monitoring cadence live).
- Improve 90-day activation rate and 6-month expansion rate quarter-over-quarter.

## 2.1) World-Class Trust Blueprint (Externally Verified)

As of 2026-02-10, the trust track must explicitly align with the following external realities:
- DFARS CMMC clause updates are effective as of 2025-11-10 (`252.204-7021`, `252.204-7025`).
- DFARS CMMC phase-in includes milestone logic through 2028-11-09 (`204.7504`).
- NIST SP 800-171 Rev. 3 and SP 800-171A Rev. 3 (both final, May 2024) should drive control and assessment evidence models.
- NIST SP 800-218A (final, July 2024) should gate AI-related secure development tasks.
- FedRAMP 20x Phase 2 is active with collaborative process expectations and pilot timelines through 2026-03-31.

Execution implication:
- `E-TRUST-*` epics are not optional technical debt cleanup. They are direct go-to-market enablers for enterprise and defense procurement.

## 3) Team Topology and Owners

## Owner roles
- `EPM`: Program Owner / milestone governance.
- `SEC`: Security + Compliance Lead.
- `PLAT`: Platform/SRE Lead.
- `DATA`: Data Integrations Lead.
- `PROP`: Proposal Workflow Lead.
- `INTG`: Word/SharePoint Integrations Lead.
- `UX`: Product Design + Frontend Experience Lead.
- `CS`: Customer Success and Adoption Lead.
- `QA`: Test and quality gate owner.

## Squad mapping
- Squad A (Trust Platform): `SEC`, `PLAT`, `QA`
- Squad B (Proposal Intelligence): `PROP`, `UX`, `QA`
- Squad C (Data & Signals): `DATA`, `PLAT`, `QA`
- Squad D (Word/SharePoint): `INTG`, `UX`, `QA`
- Squad E (Adoption & Success): `CS`, `UX`, `EPM`

## 4) Epic Portfolio

| Epic ID | Epic | Priority | Owner | Start | Target Complete | Success Metric |
| --- | --- | --- | --- | --- | --- | --- |
| E-TRUST-01 | CUI Classification + Policy Enforcement | P0 | SEC | Sprint 1 | Sprint 6 | 100% sensitive actions policy-evaluated + audited |
| E-TRUST-02 | Control Evidence Registry + Compliance Bundles | P0 | SEC | Sprint 1 | Sprint 8 | Evidence completeness >= 95% for required controls |
| E-TRUST-03 | Identity Hardening (MFA policy + Passkey/WebAuthn) | P0 | SEC | Sprint 3 | Sprint 10 | High-assurance auth adoption >= 85% privileged users |
| E-TRUST-04 | Secure SDLC + AI Risk Gates | P0 | PLAT | Sprint 1 | Sprint 7 | 100% critical path PRs pass security gates |
| E-DATA-01 | Provider Maturity Upgrade (Sample -> Live) | P1 | DATA | Sprint 2 | Sprint 12 | >= 90% high-priority providers in Live mode |
| E-DATA-02 | Freshness, Dedupe, Confidence Scoring | P1 | DATA | Sprint 4 | Sprint 10 | Duplicate rate reduced >= 60% |
| E-PROP-01 | Proposal Quality Scorecard v1->v2 | P1 | PROP | Sprint 2 | Sprint 9 | Scorecard coverage 100% generated sections |
| E-PROP-02 | Compliance Package Export + Evaluator Lens | P1 | PROP | Sprint 5 | Sprint 12 | Package adoption >= 60% submissions |
| E-WORK-01 | Word Reliability + Sync Conflict Recovery | P1 | INTG | Sprint 3 | Sprint 11 | Sync success >= 99.0% |
| E-WORK-02 | SharePoint Deep Reliability + Diagnostics | P1 | INTG | Sprint 3 | Sprint 10 | MTTR < 5 min for retriable sync failures |
| E-CS-01 | Structured Onboarding Program + Health Model | P1 | CS | Sprint 2 | Sprint 8 | Median time-to-first-proposal <= 14 days |
| E-CS-02 | ROI Proof System (Case studies + telemetry) | P1 | CS | Sprint 6 | Sprint 12 | 3-5 validated outcome stories published |
| E-REL-01 | SLO/Error Budget Governance | P0 | PLAT | Sprint 1 | Sprint 6 | Critical journey success >= 99.0% |

## 5) First 90 Days Detailed Sprint Plan (Run Now)

## Sprint 1 (Weeks 1-2)

### Objectives
- Establish trust foundation and governance scaffolding.

### Committed slices
- `E-TRUST-01-S1`: Add data classification model (`public`, `internal`, `fci`, `cui`) at document/proposal/workspace entities.
- `E-TRUST-02-S1`: Create control-evidence registry schema and API skeleton.
- `E-TRUST-04-S1`: Add secure-SDLC policy checks in CI (dependency, secrets, SAST baseline).
- `E-REL-01-S1`: Define SLOs for `ingest`, `analyze`, `draft`, `export`; implement dashboard stubs.
- `EPM-OPS-S1`: Program governance rituals, risk register, and KPI baseline dashboard.

### Done when
- DB migration and API contracts merged with tests.
- Playwright smoke path includes policy-aware access for at least one sensitive action.
- CI gates fail closed for critical issues.

## Sprint 2 (Weeks 3-4)

### Objectives
- Begin visible trust UX and data maturity transparency.

### Committed slices
- `E-TRUST-01-S2`: Policy decision engine v1 for export/share/download based on classification + role.
- `E-DATA-01-S1`: Provider maturity matrix (Live/Hybrid/Sample) in admin diagnostics.
- `E-PROP-01-S1`: Proposal quality scorecard v1 (coverage + citation confidence).
- `E-CS-01-S1`: Structured onboarding checklist v1 and activation telemetry.
- `E-REL-01-S2`: Error budget calculation and release gate prototype.

### Done when
- Policy denials + audit events verified by integration tests.
- Admin sees provider maturity state and freshness timestamp.
- Scorecard displayed in proposal workspace for generated sections.

## Sprint 3 (Weeks 5-6)

### Objectives
- Identity hardening and integration reliability begin.

### Committed slices
- `E-TRUST-03-S1`: Org-level MFA policy controls and step-up auth for privileged exports.
- `E-WORK-01-S1`: Word sync conflict detection and deterministic resolution UX.
- `E-WORK-02-S1`: SharePoint retry/backoff + `Retry-After` honoring.
- `E-DATA-01-S2`: Convert first two high-value Sample providers to Live feeds.
- `E-PROP-01-S2`: Section-level quality deltas (before/after rewrite).

### Done when
- Privileged action flow requires step-up in E2E.
- Word and SharePoint retriable failure scenarios have passing regression tests.

## Sprint 4 (Weeks 7-8)

### Objectives
- Compliance evidence workflows and source quality controls.

### Committed slices
- `E-TRUST-02-S2`: Evidence object ingestion (manual + automated) and linkage to controls.
- `E-DATA-02-S1`: Dedupe scoring service + freshness scoring service.
- `E-CS-01-S2`: Customer health model v1 (adoption, risk, and workflow completion signals).
- `E-PROP-01-S3`: Scorecard weighting calibration and baseline thresholds.

### Done when
- Evidence bundle generation produces complete artifact list for pilot control set.
- Dedupe/freshness metrics exposed in reports and alerting.

## Sprint 5 (Weeks 9-10)

### Objectives
- Trust workflows become customer-facing value.

### Committed slices
- `E-TRUST-01-S3`: CUI export controls (watermark/redaction policy actions).
- `E-PROP-02-S1`: Compliance package export v1.
- `E-WORK-02-S2`: SharePoint diagnostics panel with actionable remediation guidance.
- `E-DATA-01-S3`: Live connector expansion (next top-priority source).

### Done when
- CUI-marked artifacts cannot bypass policy routes in backend + UI tests.
- Compliance package downloaded with matrix+traceability bundle.

## Sprint 6 (Weeks 11-12)

### Objectives
- First quarter closeout and enterprise proof baseline.

### Committed slices
- `E-TRUST-02-S3`: Quarterly trust report generator (control coverage + remediations).
- `E-TRUST-04-S2`: AI secure-dev checklist and release gate for AI-impacting changes.
- `E-CS-02-S1`: ROI dashboard v1 (hours saved, cycle-time deltas, proposal throughput).
- `E-REL-01-S3`: Incident runbooks + postmortem template enforcement.

### Done when
- First trust report generated from production telemetry.
- ROI dashboard active for pilot accounts.
- All Sev1/Sev2 incidents use standard RCA template.

## 6) Quarter-by-Quarter Roadmap (After Day 90)

## Q2 (Sprints 7-12)
- Full CUI policy coverage across collaboration and external sharing.
- Identity policy expansion (passkey/WebAuthn rollout and admin policy enforcement).
- Provider Live-mode expansion for top-demand source clusters.
- Compliance package v2 with reviewer decisions and trace matrix enhancements.
- SharePoint and Word reliability to >= 99.0% with improved diagnostics.

## Q3 (Sprints 13-18)
- Advanced evaluator-lens simulations and proposal quality optimization loops.
- Continuous monitoring cadence hardened (quarterly report + remediation SLAs).
- Adoption and health interventions reduce time-to-value variance by segment.
- Publish first wave of externally usable customer outcome stories.

## Q4 (Sprints 19-26)
- Complete trust milestones and enterprise packaging.
- Optimize growth engine (activation -> expansion).
- Ship year-end reliability and trust summary for sales/procurement enablement.
- Lock next-year roadmap from KPI-driven gap analysis.

## 7) Backlog by Epic (Atomic, Shippable Slices)

## E-TRUST-01 CUI Classification + Policy Enforcement

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-TRUST-01-S1 | Entity classification fields + migrations | SEC | None | Unit + migration + API integration |
| E-TRUST-01-S2 | Policy decision service (`allow`, `deny`, `step_up`) | SEC | S1 | Unit + endpoint auth tests |
| E-TRUST-01-S3 | CUI export redaction and watermarking | SEC | S2 | Export integration + E2E download checks |
| E-TRUST-01-S4 | Collaboration sharing policy overlays for CUI | SEC | S2 | Collaboration E2E + role matrix tests |
| E-TRUST-01-S5 | Admin policy console + audit trail search | SEC | S2 | UI tests + audit event integration |

## E-TRUST-02 Control Evidence Registry

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-TRUST-02-S1 | Control/evidence schema and APIs | SEC | None | Unit + integration |
| E-TRUST-02-S2 | Evidence collection workflows and linkage | SEC | S1 | Integration + E2E admin flow |
| E-TRUST-02-S3 | Report and bundle generation | SEC | S2 | Snapshot/regression export tests |
| E-TRUST-02-S4 | Quarterly report automation | SEC | S3 | Scheduled job + report contract tests |

## E-TRUST-03 Identity Hardening

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-TRUST-03-S1 | Org MFA policy modes | SEC | None | Auth integration + admin UI tests |
| E-TRUST-03-S2 | Step-up auth for privileged actions | SEC | S1 | End-to-end privileged action tests |
| E-TRUST-03-S3 | Passkey/WebAuthn registration/login | SEC | S1 | Auth E2E cross-browser matrix |
| E-TRUST-03-S4 | Access review exports and policy compliance checks | SEC | S2 | Integration + export assertions |

## E-DATA-01 Provider Maturity Upgrade

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-DATA-01-S1 | Provider maturity inventory + dashboard | DATA | None | Unit + admin E2E |
| E-DATA-01-S2 | Top source conversion #1 | DATA | S1 | Provider contract tests + ingest E2E |
| E-DATA-01-S3 | Top source conversion #2 | DATA | S1 | Same as above |
| E-DATA-01-S4 | Top source conversion #3 | DATA | S1 | Same as above |
| E-DATA-01-S5 | Source SLA monitoring and alerts | DATA | S2-S4 | Observability + alert tests |

## E-DATA-02 Quality Scoring

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-DATA-02-S1 | Freshness scoring service | DATA | None | Unit + integration |
| E-DATA-02-S2 | Dedupe confidence and merge policy | DATA | S1 | Regression fixtures + integration |
| E-DATA-02-S3 | Parse completeness scoring | DATA | S1 | Ingest tests |
| E-DATA-02-S4 | User-facing confidence indicators | DATA | S1-S3 | UI + E2E |

## E-PROP-01 Proposal Quality Scorecard

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-PROP-01-S1 | Coverage + citation confidence scoring | PROP | None | Unit + proposal integration |
| E-PROP-01-S2 | Rewrite delta scoring | PROP | S1 | Workspace E2E |
| E-PROP-01-S3 | Threshold tuning + reviewer feedback loop | PROP | S1-S2 | Analytics + review workflow tests |

## E-PROP-02 Compliance Package + Evaluator Lens

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-PROP-02-S1 | Package export v1 | PROP | E-PROP-01-S1 | Export contract + E2E download |
| E-PROP-02-S2 | Reviewer decision trace integration | PROP | S1 | Review integration tests |
| E-PROP-02-S3 | Evaluator lens simulation v1 | PROP | S1-S2 | Deterministic scenario tests |

## E-WORK-01 Word Reliability

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-WORK-01-S1 | Conflict detection model | INTG | None | Unit + host-loop E2E |
| E-WORK-01-S2 | Deterministic conflict resolution UX | INTG | S1 | Office-host tests + Playwright |
| E-WORK-01-S3 | Recovery and retry diagnostics | INTG | S1-S2 | Telemetry + regression tests |

## E-WORK-02 SharePoint Reliability

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-WORK-02-S1 | Retry-After/backoff compliance | INTG | None | Integration tests |
| E-WORK-02-S2 | Diagnostics and operator actions | INTG | S1 | UI + E2E |
| E-WORK-02-S3 | Sync health SLO tracking | INTG | S1 | Observability assertions |

## E-CS-01 Onboarding and Health Model

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-CS-01-S1 | Guided onboarding milestones + telemetry | CS | None | Unit + E2E onboarding flow |
| E-CS-01-S2 | Health scoring and risk alerts | CS | S1 | Analytics + alert contract tests |
| E-CS-01-S3 | CSM intervention workflows | CS | S2 | Operational pilot outcomes |

## E-CS-02 ROI Proof Engine

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-CS-02-S1 | ROI dashboard with baseline/delta | CS | E-CS-01-S1 | Analytics tests |
| E-CS-02-S2 | Report templates for customer outcomes | CS | S1 | Export/report tests |
| E-CS-02-S3 | Evidence packaging for case studies | CS | S1-S2 | Data QA + review signoff |

## E-REL-01 Reliability Governance

| Slice ID | Description | Owner | Dependencies | Validation |
| --- | --- | --- | --- | --- |
| E-REL-01-S1 | SLO definition + instrumentation | PLAT | None | Metrics integration tests |
| E-REL-01-S2 | Error budget release gates | PLAT | S1 | CI checks + release rehearsal |
| E-REL-01-S3 | Incident command + RCA workflow | PLAT | S1 | Drill exercises + template usage |

## 8) Quality Gates (Non-Negotiable)

Gate 1: Contract Gate
- API contracts updated and covered by integration tests.
- Frontend client path checks for modified/new endpoints.

Gate 2: Deterministic Test Gate
- Unit + integration pass for changed modules.
- E2E pass on deterministic stack (`DEBUG=true`, `MOCK_AI=true`) for impacted journeys.

Gate 3: UX Failure Mode Gate
- Recoverable external errors remain non-blocking for core actions.
- Empty/loading/error states are actionable and tested.

Gate 4: Trust Gate
- Protected actions require policy decision and audit event.
- Role/permission matrix tests pass.

Gate 5: Documentation Gate
- Capability trackers and counts updated from final suite run outputs.
- Runbooks and rollback notes updated.

## 9) KPI Dashboard Spec

## Product outcome KPIs
- `proposal_cycle_median_days`
- `opportunities_pursued_per_user_month`
- `generated_section_acceptance_rate`
- `review_turnaround_hours`

## Trust KPIs
- `policy_enforced_action_rate`
- `sensitive_action_audit_coverage`
- `control_evidence_completeness`
- `high_assurance_auth_adoption`

## Reliability KPIs
- `critical_flow_success_rate`
- `p95_ingest_latency`, `p95_analyze_latency`, `p95_draft_latency`, `p95_export_latency`
- `change_failure_rate`
- `mttr_minutes`

## Adoption KPIs
- `time_to_first_complete_proposal_days`
- `onboarding_step_completion_rate`
- `90_day_logo_retention`
- `expansion_rate_6_month`

## 10) Risk Register (Active)

| Risk ID | Risk | Likelihood | Impact | Owner | Mitigation |
| --- | --- | --- | --- | --- | --- |
| R-01 | Compliance scope expands faster than delivery capacity | Medium | High | EPM | Time-box per milestone, strict phase gates |
| R-02 | Source expansion increases duplicates/noise | High | High | DATA | Dedupe scoring + freshness gates before rollout |
| R-03 | Policy controls degrade UX | Medium | High | UX | Progressive disclosure, role-focused defaults |
| R-04 | Integration reliability blocks adoption | Medium | High | INTG | Reliability SLOs + diagnostics first |
| R-05 | Metrics do not prove ROI | Medium | High | CS | Baseline instrumentation before feature rollout |
| R-06 | Regression drift with rapid parallel delivery | Medium | High | QA | Mandatory deterministic E2E gate + final full-suite reconciliation |

## 11) Governance Cadence

- Daily: squad standups with blocker escalation.
- Weekly: program review (milestones, KPIs, risks, dependencies).
- Biweekly: architecture + security review.
- Monthly: exec review, roadmap reallocation by KPI movement.
- Quarterly: trust report and reliability report publication.

## 12) Immediate Assignment Checklist (This Week)

1. Assign named owners to each epic ID and lock sprint 1 capacity.
2. Create tracker tickets using `Epic ID` + `Slice ID` naming.
3. Stand up KPI baseline dashboards before starting Sprint 1 dev.
4. Schedule quality gate reviews on calendar now.
5. Select pilot customer cohort for trust + ROI validation.

## 13) Change Control Protocol

When priorities shift:
- Do not drop P0 trust slices without explicit executive decision.
- Replace scope only with equal or greater KPI impact.
- Update board, risk register, and sprint commitments in the same session.

## 14) Traceability to Standards (Trust Pillar)

Primary standards and guidance this board maps to:
- FAR 52.204-21
- DFARS 252.204-7012, 252.204-7021, 252.204-7025
- NIST SP 800-171 Rev.3
- NIST SP 800-218 / 800-218A
- FedRAMP 20x process and continuous monitoring

This traceability is implemented through `E-TRUST-*` slices and acceptance gates, not as separate paper artifacts.
