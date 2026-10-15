#!/usr/bin/env bash
# run_regressions.sh — prove the smoke checks DETECT breakage.
#
# Injects a deliberately broken served-metadata variant (strip-columns
# protection disabled — the shape a silently-failing deploy would produce)
# and asserts the smoke run FAILS with the expected failing checks.
# The regression run must exit 0 only when the smoke caught the break.
#
# Usage: tests/smoke-stack/run_regressions.sh DATASETTE_IMAGE FRONTEND_IMAGE

set -Eeuo pipefail

DS_IMAGE="${1:?usage: run_regressions.sh DATASETTE_IMAGE FRONTEND_IMAGE}"
FE_IMAGE="${2:?usage: run_regressions.sh DATASETTE_IMAGE FRONTEND_IMAGE}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

SMOKE_DATA_DIR="$(mktemp -d /tmp/smoke-regression.XXXXXX)"
SMOKE_DATASETTE_IMAGE="$DS_IMAGE"
SMOKE_FRONTEND_IMAGE="$FE_IMAGE"
export SMOKE_DATA_DIR SMOKE_DATASETTE_IMAGE SMOKE_FRONTEND_IMAGE

COMPOSE_ARGS=(-p smoke-stack -f docker-compose.yml -f tests/smoke-stack/docker-compose.smoke.yml)

cleanup() {
  local rc=$?
  docker compose "${COMPOSE_ARGS[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$SMOKE_DATA_DIR"
  exit "$rc"
}
trap cleanup EXIT INT TERM

# Fixtures, then REPLACE the served metadata with the broken variant.
uv run --locked python tests/smoke-stack/synthetic_fixtures.py "$SMOKE_DATA_DIR" >/dev/null
cp tests/smoke-stack/fixtures/broken-metadata.json "$SMOKE_DATA_DIR/metadata.json"

# Bring the stack up healthy with the broken metadata in place.
docker compose "${COMPOSE_ARGS[@]}" up -d --wait >/dev/null

set +e
SMOKE_BASE_URL="http://127.0.0.1:8891" uv run --locked python tests/smoke-stack/smoke_checks.py > /tmp/smoke-regression-output.log 2>&1
SMOKE_RC=$?
set -e

echo "smoke exit under broken config: $SMOKE_RC"

fail() { echo "REGRESSION-FAILED: $1"; tail -25 /tmp/smoke-regression-output.log; exit 1; }

# The smoke must have FAILED...
[ "$SMOKE_RC" -ne 0 ] || fail "smoke unexpectedly PASSED with protection disabled"

# ...with the specific expected failing checks
grep -q "FAIL protected values absent (rows)" /tmp/smoke-regression-output.log \
  || fail "expected 'protected values absent (rows)' to fail"
grep -q "FAIL CSV blocked on protected table" /tmp/smoke-regression-output.log \
  || fail "expected the CSV-403 check to fail"

echo "REGRESSIONS-PASSED: smoke correctly caught the broken protection"