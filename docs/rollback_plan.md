# Rollback Plan

## Trigger Conditions
- Elevated error rate or failed health checks.
- Data integrity issues detected in QA or production.
- Failed migrations or critical workflow regressions.

## Rollback Steps
1. Scale down or pause traffic to the affected services.
2. Roll back application containers to the last known-good image.
3. If migrations were applied, evaluate if a downgrade is required:
   - Prefer forward-fix migrations when possible.
   - If necessary, run `alembic downgrade <revision>`.
4. Validate `/health/ready` and `/api/v1/analytics/slo`.
5. Run `scripts/e2e_smoke.py` to confirm critical workflows.

## Communication
- Notify stakeholders of rollback status and expected timeline.
- Document incident details and follow-up remediation tasks.
