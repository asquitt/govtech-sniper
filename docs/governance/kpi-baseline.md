# KPI Baseline

## Overview
This document establishes baseline metrics and targets for GovTech Sniper platform health across four categories: Product, Trust, Reliability, and Adoption.

## Baseline Date
**Day 0**: 2026-02-12 (Sprint 1 completion)

## Product KPIs

### Time to First Draft
- **Definition**: Median time from RFP upload to first generated proposal section
- **Baseline (Day 0)**: TBD (instrumentation in progress)
- **Target (3 months)**: < 15 minutes for 90th percentile
- **Target (6 months)**: < 10 minutes for 90th percentile
- **Measurement**: SLO tracking in `slo_service.py` (INGEST + ANALYZE + DRAFT flows)
- **Owner**: Product Team

### Proposal Win Rate (Customer-Reported)
- **Definition**: % of proposals using GovTech Sniper that result in contract award
- **Baseline (Day 0)**: TBD (requires customer survey data)
- **Target (6 months)**: Establish baseline from first 10 customers
- **Target (12 months)**: 10% improvement over baseline
- **Measurement**: Quarterly customer survey + optional self-reporting in platform
- **Owner**: Customer Success

### Feature Adoption Rate
- **Definition**: % of active users who have used each major feature (Ingest, Analyze, Draft, Export, Collaboration) in past 30 days
- **Baseline (Day 0)**: TBD (analytics instrumentation pending)
- **Target (3 months)**:
  - Ingest: 100% (core workflow)
  - Analyze: 80%
  - Draft: 70%
  - Export: 90%
  - Collaboration: 40%
- **Measurement**: Mixpanel/PostHog event tracking
- **Owner**: Product Analytics

## Trust KPIs

### Security Incident Response Time
- **Definition**: Mean time to acknowledge (MTTA) and mean time to resolve (MTTR) for security incidents
- **Baseline (Day 0)**: TBD (no incidents yet)
- **Target (Ongoing)**:
  - MTTA: < 1 hour for critical, < 4 hours for high
  - MTTR: < 24 hours for critical, < 72 hours for high
- **Measurement**: PagerDuty or incident management system
- **Owner**: Security Team

### Compliance Audit Pass Rate
- **Definition**: % of internal compliance audits (SOC 2 Type II controls, FedRAMP readiness) passed without findings
- **Baseline (Day 0)**: 0% (no audits completed)
- **Target (6 months)**: 90% pass rate on internal readiness audit
- **Target (12 months)**: SOC 2 Type II certification achieved
- **Measurement**: Quarterly internal audits, external certification timeline
- **Owner**: Compliance Team

### Data Classification Coverage
- **Definition**: % of database tables and API endpoints with explicit `DataClassification` metadata
- **Baseline (Day 0)**: TBD (requires codebase audit)
- **Target (1 month)**: 100% of new tables/endpoints classified
- **Target (3 months)**: 100% of existing tables/endpoints classified
- **Measurement**: Automated linting in CI (custom ruff rule or pre-commit hook)
- **Owner**: Security Team

## Reliability KPIs

### SLO Compliance Rate
- **Definition**: % of time critical flows meet their SLO targets (99%+ success rate, p95 latency < target)
- **Baseline (Day 0)**: TBD (SLO instrumentation deployed in S1-05)
- **Target (1 month)**: 95% compliance (allowing for tuning period)
- **Target (3 months)**: 99% compliance
- **SLO Targets**:
  - Ingest: 99.5% success, p95 < 30s
  - Analyze: 99% success, p95 < 60s
  - Draft: 99% success, p95 < 120s
  - Export: 99.5% success, p95 < 15s
- **Measurement**: `slo_service.py` weekly reports
- **Owner**: SRE Team

### Mean Time to Recovery (MTTR)
- **Definition**: Average time from incident detection to service restoration
- **Baseline (Day 0)**: TBD (no production incidents yet)
- **Target (Ongoing)**: < 1 hour for P0, < 4 hours for P1, < 24 hours for P2
- **Measurement**: Incident postmortems, PagerDuty metrics
- **Owner**: SRE Team

### Error Rate
- **Definition**: % of API requests resulting in 5xx errors
- **Baseline (Day 0)**: TBD (production monitoring pending)
- **Target (Ongoing)**: < 0.1% (99.9% success rate)
- **Measurement**: API gateway logs, Sentry error tracking
- **Owner**: Platform Team

## Adoption KPIs

### Monthly Active Users (MAU)
- **Definition**: Unique users who log in and perform at least 1 action (upload, generate, export) in past 30 days
- **Baseline (Day 0)**: 0 (pre-launch)
- **Target (3 months)**: 50 MAU (pilot customers)
- **Target (6 months)**: 200 MAU (general availability)
- **Target (12 months)**: 1,000 MAU
- **Measurement**: Analytics platform (Mixpanel/PostHog)
- **Owner**: Growth Team

### Customer Retention Rate
- **Definition**: % of customers who renew subscription after initial contract period (typically 12 months)
- **Baseline (Day 0)**: TBD (requires first cohort to reach renewal)
- **Target (12 months)**: 80% gross retention
- **Target (24 months)**: 90% gross retention, 110% net retention (expansion)
- **Measurement**: Stripe/CRM data
- **Owner**: Customer Success

### Net Promoter Score (NPS)
- **Definition**: Customer satisfaction metric from quarterly surveys
- **Baseline (Day 0)**: TBD (requires first customer survey)
- **Target (6 months)**: NPS ≥ 30 (industry average for B2B SaaS)
- **Target (12 months)**: NPS ≥ 50 (excellent)
- **Measurement**: Quarterly NPS survey (Delighted or similar)
- **Owner**: Customer Success

---

## Review Cadence

### Weekly
- SLO compliance rate
- Error rate
- Feature adoption (high-level)

### Monthly
- MAU
- Time to first draft (p90)
- Data classification coverage progress

### Quarterly
- NPS survey
- Compliance audit progress
- Win rate (customer-reported)
- KPI review and target adjustments

### Annually
- Customer retention rate
- Security incident trends
- MTTR benchmarking

---

## Instrumentation Roadmap

### Sprint 1 (Current)
- [x] SLO service implementation (`slo_service.py`)
- [x] Security gate baseline (CI integration)

### Sprint 2
- [ ] Analytics event tracking (Mixpanel/PostHog setup)
- [ ] SLO dashboard (Grafana or built-in admin panel)
- [ ] Error rate monitoring (Sentry integration)

### Sprint 3
- [ ] Data classification audit tooling
- [ ] NPS survey integration
- [ ] Customer win rate reporting (optional self-report)

### Sprint 4
- [ ] Compliance audit tracking system
- [ ] MTTR/MTTA incident reporting
- [ ] Retention cohort analysis

---

## References
- [SLO Definitions](../../backend/app/services/slo_service.py)
- [Risk Register](./risk-register.md)
- [Decision Log](./decision-log.md)
