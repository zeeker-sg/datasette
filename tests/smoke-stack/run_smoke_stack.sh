#!/usr/bin/env bash
# run_smoke_stack.sh — disposable, production-shaped smoke stack runner.
#
# Spins up the real compose stack (datasette + frontend + caddy) with
# synthetic fixture DBs and a temp data dir, runs smoke_checks.py against the
# caddy loopback port, and tears everything down — always, even on failure.
# Never touches prod: separate compose project (-p smoke-stack), own network,
# loopback-only port, temp data dir, blanked S3/AWS env, throwaway owner
# token, restart=no.
#
# Usage:
#   tests/smoke-stack/run_smoke_stack.sh DATASETTE_IMAGE FRONTEND_IMAGE \
#       [BASEURL] [KEEP]
#   KEEP=1 keeps the stack up for debugging (teardown manually via
#   `docker compose -p smoke-stack -f docker-compose.yml \
#   -f tests/smoke-stack/docker-compose.smoke.yml down -v`).
#
# Exit codes: 0 smoke green · 1 smoke checks failed · 2 setup/usage error.

set -Eeuo pipefail

DS_IMAGE="${1:?usage: run_smoke_stack.sh DATASETTE_IMAGE FRONTEND_IMAGE [BASEURL] [KEEP]}"
FE_IMAGE="${2:?usage: run_smoke_stack.sh DATASETTE_IMAGE FRONTEND_IMAGE [BASEURL] [KEEP]}"
BASEURL="${3:-http://127.0.0.1:8891}"
KEEP="${4:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

SMOKE_DATASETTE_IMAGE="$DS_IMAGE"
SMOKE_FRONTEND_IMAGE="$FE_IMAGE"
SMOKE_DATA_DIR="$(mktemp -d /tmp/smoke-stack-data.XXXXXX)"
export SMOKE_DATASETTE_IMAGE SMOKE_FRONTEND_IMAGE SMOKE_DATA_DIR

COMPOSE_ARGS=(-p smoke-stack -f docker-compose.yml -f tests/smoke-stack/docker-compose.smoke.yml)

cleanup() {
  local rc=$?
  # Runtime provenance BEFORE the stack disappears (only when asked for).
  if [ -n "${SMOKE_RUNTIME_FILE:-}" ]; then
    {
      echo "## Smoke stack runtime provenance (captured before teardown)"
      echo "datasette image ref: $SMOKE_DATASETTE_IMAGE"
      echo "frontend image ref : $SMOKE_FRONTEND_IMAGE"
      docker ps --filter "name=smoke-stack" --format '{{.Names}} | {{.Image}} | {{.Status}}'
    } > "$SMOKE_RUNTIME_FILE" 2>/dev/null || true
  fi
  if [ "$KEEP" != "1" ]; then
    docker compose "${COMPOSE_ARGS[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    rm -rf "$SMOKE_DATA_DIR"
  else
    echo "KEEP=1: stack left up (data dir: $SMOKE_DATA_DIR); tear down manually:"
    echo "  docker compose -p smoke-stack -f docker-compose.yml -f tests/smoke-stack/docker-compose.smoke.yml down -v"
  fi
  exit $rc
}
trap cleanup EXIT INT TERM

# 1 — synthetic fixtures into the temp dir (safe markers only)
uv run --locked python tests/smoke-stack/synthetic_fixtures.py "$SMOKE_DATA_DIR" >/dev/null

# 2 — bring the stack up *healthy*: depends_on service_healthy gates the
#     frontend on the real compose healthcheck, --wait polls until all green
docker compose "${COMPOSE_ARGS[@]}" up -d --wait

# 3 — run the end-to-end checks through the caddy entry
SMOKE_BASE_URL="$BASEURL" uv run --locked python tests/smoke-stack/smoke_checks.py