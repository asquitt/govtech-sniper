# Risk Register

## Overview
This document tracks identified risks to the GovTech Sniper platform, including technical, operational, and business risks. Each risk is assessed for likelihood and impact, with documented mitigation strategies.

## Risk Assessment Scale

### Likelihood
- **High (H)**: >50% probability in next 6 months
- **Medium (M)**: 20-50% probability in next 6 months
- **Low (L)**: <20% probability in next 6 months

### Impact
- **Critical (C)**: Service outage, data loss, security breach, or customer churn
- **High (H)**: Significant feature degradation or customer satisfaction impact
- **Medium (M)**: Minor feature issues or temporary workarounds needed
- **Low (L)**: Minimal customer impact

## Active Risks

| Risk ID | Risk Description | Category | Likelihood | Impact | Status | Last Reviewed | Mitigation Owner | Mitigation Strategy |
|---------|-----------------|----------|------------|--------|--------|---------------|------------------|---------------------|
| R-01 | **Data Classification Gaps**: Insufficient CUI/FCI tagging leading to unauthorized data exposure | Security | High | Critical | Active | 2026-02-12 | Security Team | Implement DataClassification enum across all models; policy engine enforces access controls; audit logging for sensitive data access |
| R-02 | **AI Hallucination**: Generated proposal content includes fabricated citations or non-compliant statements | Product Quality | High | High | Active | 2026-02-12 | AI/ML Team | Citation verification against source documents; compliance check layer; human-in-the-loop review workflow; SLO tracking for draft accuracy |
| R-03 | **Performance Degradation**: P95 latency exceeds SLO targets (30s ingest, 60s analyze, 120s draft, 15s export) | Reliability | Medium | High | Active | 2026-02-12 | Platform Team | SLO instrumentation in critical flows; performance budgets in CI; Gemini context caching; async job queuing for long operations |
| R-04 | **Dependency Vulnerabilities**: Critical CVEs in Python/Node dependencies causing security incidents | Security | Medium | High | Active | 2026-02-12 | DevSecOps | pip-audit in CI (warn-only for 30 days); bandit SAST scanning; automated dependency update PRs; security gate policy enforcement |
| R-05 | **Third-Party API Failures**: SAM.gov or Gemini API downtime causing service disruption | Operational | Medium | High | Active | 2026-02-12 | SRE Team | Circuit breaker pattern for external calls; graceful degradation (queue for retry); SLA monitoring; multi-region failover for critical APIs |
| R-06 | **Inadequate Access Controls**: Role-based permissions not enforced on sensitive operations (export, collaboration, admin) | Security | Medium | Critical | Active | 2026-02-12 | Backend Team | Role-based rule matrix in policy engine; audit trail for admin actions; integration tests for RBAC; penetration testing of auth flows |

## Retired Risks

| Risk ID | Risk Description | Retirement Date | Reason |
|---------|-----------------|-----------------|--------|
| (None yet) | | | |

## Risk Review Process

### Frequency
- **Critical/High Impact Risks**: Reviewed weekly in sprint planning
- **Medium Impact Risks**: Reviewed bi-weekly
- **Low Impact Risks**: Reviewed monthly

### Escalation
- New Critical risks must be reported to VP Engineering within 24 hours
- Risk status changes (likelihood/impact increase) trigger immediate review
- Mitigation failures escalate to incident response process

## Adding New Risks

To add a new risk:
1. Assign next sequential Risk ID (R-07, R-08, etc.)
2. Document in table with all required fields
3. Assign mitigation owner
4. Set initial review date within 7 days
5. Add to weekly governance meeting agenda

## References
- [Security Gate Policy](../security-gate-policy.md)
- [SLO Definitions](../../backend/app/services/slo_service.py)
- [Decision Log](./decision-log.md)
