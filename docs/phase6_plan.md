# Phase 6 Plan - Production Hardening

## Goals
- Make the platform production-ready with enterprise security, reliability, and operational controls.

## Deliverables
1. Identity & Access
   - OIDC/OAuth SSO production flows (Okta, Microsoft Entra ID) with token exchange.
   - SCIM user provisioning and group->role mapping.
   - MFA support for password-based accounts.

2. Security & Compliance
   - Field-level encryption for secrets and sensitive data.
   - Secrets management (encrypted vault with KMS-ready keying).
   - Audit export (CSV + signed JSON) and retention policies.

3. Data & Infrastructure
   - Alembic migrations for schema evolution.
   - Background jobs for ingest/sync/alerting (queue + scheduler).
   - Caching for hot reads (redis/memory) with TTL policies.

4. Observability & Reliability
   - SLO dashboards (latency, error rate, job failures).
   - Structured tracing with correlation IDs in logs.
   - Alerting rules for failed syncs, webhook failures, and auth anomalies.

5. QA & Release
   - E2E test suite for critical flows.
   - Load tests for ingest + search.
   - Deployment playbook and rollback plan.

## Status
- Complete.
- SSO token exchange wired with mockable flows for tests.
- SCIM endpoints provision users and map groups to roles.
- MFA enrollment/verification and login enforcement live.
- Secrets vault + integration config encryption shipped.
- Audit export + retention task scheduled.
- Alembic config scaffolded for schema migrations.
- Cache layer for hot reads (memory/redis).
- SLO + alerting endpoints and scheduled checks in place.
- E2E smoke script expanded to include Word add-in + graphics.
- Load test script added for ingest/search.
- Tests run: backend `pytest -q`, frontend `npm run test:run` (February 5, 2026).
