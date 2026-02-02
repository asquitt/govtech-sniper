#!/usr/bin/env bash
set -euo pipefail

export MOCK_SAM_GOV="${MOCK_SAM_GOV:-true}"
export RFP_SKIP_SAM_INGEST="${RFP_SKIP_SAM_INGEST:-false}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-govtech-sniper}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/compose_guard.sh"

docker compose -p "${COMPOSE_PROJECT_NAME}" exec -T api /bin/sh -c \
  "MOCK_SAM_GOV=${MOCK_SAM_GOV} RFP_SKIP_SAM_INGEST=${RFP_SKIP_SAM_INGEST} python /app/scripts/e2e_smoke.py"
