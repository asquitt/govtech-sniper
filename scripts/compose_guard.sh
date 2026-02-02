#!/usr/bin/env bash
set -euo pipefail

project="${COMPOSE_PROJECT_NAME:-govtech-sniper}"
export COMPOSE_PROJECT_NAME="${project}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; skipping compose guard" >&2
  exit 0
fi

projects="$(docker ps --format '{{.Label "com.docker.compose.project"}}' | sort -u | sed '/^$/d')"
if [[ -n "${projects}" ]]; then
  others="$(printf '%s\n' "${projects}" | grep -v "^${project}$" || true)"
  if [[ -n "${others}" ]]; then
    echo "Note: other compose projects are running: ${others}" >&2
    echo "Commands are scoped to COMPOSE_PROJECT_NAME=${project}" >&2
  fi
fi
