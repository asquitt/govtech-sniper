#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export SECRET_KEY="${SECRET_KEY:-ci-secret-key}"
export AUDIT_EXPORT_SIGNING_KEY="${AUDIT_EXPORT_SIGNING_KEY:-ci-audit-signing-key}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./test.db}"
export MOCK_AI="${MOCK_AI:-true}"
export MOCK_SAM_GOV="${MOCK_SAM_GOV:-true}"
export RFP_SKIP_SAM_INGEST="${RFP_SKIP_SAM_INGEST:-true}"
export DEBUG="${DEBUG:-true}"

echo "[trust-ci] Running backend trust/compliance suites"
(
  cd "${ROOT_DIR}/backend"
  pytest -q \
    tests/test_compliance_dashboard.py \
    tests/test_compliance_registry.py \
    tests/test_policy_enforcement.py \
    tests/test_admin_roles.py \
    tests/test_collaboration.py
)

echo "[trust-ci] Running frontend trust/compliance unit suites"
(
  cd "${ROOT_DIR}/frontend"
  npx vitest run \
    src/__tests__/compliance-page.test.tsx \
    src/__tests__/compliance-evidence-registry-page.test.tsx \
    src/__tests__/collaboration-page-governance.test.tsx \
    src/__tests__/admin-page-invitations.test.tsx
)

if [[ "${RUN_TRUST_PLAYWRIGHT:-false}" == "true" ]]; then
  echo "[trust-ci] Running Playwright trust flows"
  (
    cd "${ROOT_DIR}/frontend"
    export E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:3000}"
    npx playwright test \
      e2e/tests/compliance-readiness.spec.ts \
      e2e/tests/collaboration-workflow.spec.ts \
      --project=chromium
  )
else
  echo "[trust-ci] Skipping Playwright trust flows (set RUN_TRUST_PLAYWRIGHT=true to enable)"
fi
