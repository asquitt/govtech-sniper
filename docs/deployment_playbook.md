# Deployment Playbook

## Overview
This playbook describes the standard deployment process for the GovTech Sniper platform across staging and production.

## Preconditions
- CI green (lint, typecheck, unit, integration, E2E smoke).
- Database migrations generated and reviewed.
- Secrets configured in the secret vault or environment.

## Staging Deployment
1. Build and push container images for `api`, `worker`, `frontend`.
2. Run `alembic upgrade head` against the staging database.
3. Deploy containers with the updated image tags.
4. Run `scripts/e2e_smoke.py` against staging.
5. Validate dashboards: `/health/ready`, `/metrics`, `/api/v1/analytics/slo`.

## Production Deployment
1. Freeze writes if required for migration safety.
2. Run `alembic upgrade head` against production.
3. Deploy new containers with updated image tags.
4. Confirm readiness checks pass on all services.
5. Run `scripts/e2e_smoke.py` with production-safe settings.

## Post-Deploy Verification
- Check audit export and alerts endpoints.
- Verify background jobs are running (Celery beat + worker).
- Confirm ingest, analyze, draft, and export workflows succeed.
