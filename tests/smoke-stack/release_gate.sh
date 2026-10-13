#!/usr/bin/env bash
# release_gate.sh — release-artifact verification (CI + local).
#
# Pulls EXACT image references, digest-verifies them (when expectations are
# supplied), checks the in-image Datasette version against the EXPECTED
# version (never hardcoded — provided or derived), then runs the IDENTICAL
# disposable smoke stack + negative control against those exact refs, and
# writes a durable evidence record. Nothing here touches production or
# zeeker stats surfaces.
#
# Source of truth defaults (derivations, NOT hardcoded versions):
#   DATASETTE_REF / FRONTEND_REF  default → the compose pin in
#                 docker-compose.yml (the production-intended release)
#   EXPECTED_DATASETTE_VERSION    default → the datasette== pin in
#                 pyproject.toml (the repo's dependency state)
#   EXPECTED_DS_DIGEST / EXPECTED_FE_DIGEST optional ("" = record observed,
#                 flag "no expectation supplied")
#
# NOTE (designed behaviour): when the compose pin LAGS the pyproject pin
# (e.g. dependency bump merged, image pin-bump not yet), the derived-default
# run FAILS the version check — that mismatch is exactly what a
# pre-deployment gate must surface. Pass explicit refs+version to gate a
# specific intended release.
#
# Usage:
#   tests/smoke-stack/release_gate.sh [DATASETTE_REF] [FRONTEND_REF] \
#       [EXPECTED_DATASETTE_VERSION] [EXPECTED_DS_DIGEST] [EXPECTED_FE_DIGEST] \
#       [MODE: defer|strict]
# Env: PROVENANCE_NOTE (free text), SMOKE_RUNTIME_FILE passthrough.
# Exit: 0 green (full verification) or deferred-with-evidence ·
#       1 a material check failed (strict mode) or smoke failed ·
#       2 setup/usage error.
#
# MODE semantics:
#   strict (used on master pushes / explicit gate runs): any mismatch —
#     refs not pullable, digest or version expectation violated — FAILS.
#     This is the pre-deployment blocker.
#   defer (default, used on PRs): when the intended release CANNOT be
#     verified yet (compose pin lags the pyproject pin during the normal
#     bump-merge → pin-bump-merge window, or refs not in the registry yet),
#     the gate writes evidence recording exactly what was observed and why
#     it is deferred, and exits 0 so unrelated PRs are not blocked. The
#     strict master-push run enforces the real gate. An INTENDED release
#     whose refs exist and satisfy expectations is always fully verified,
#     also on PRs.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

DS_REF="${1:-$(grep -E 'image: .*zeeker-datasette:' docker-compose.yml | awk '{print $2}')}"
FE_REF="${2:-$(grep -E 'image: .*zeeker-frontend:' docker-compose.yml | awk '{print $2}')}"
EXPECTED_VERSION="${3:-$(grep -oE 'datasette==[0-9abrc.dev]+' pyproject.toml | head -1 | cut -d= -f3)}"
EXPECTED_DS_DIGEST="${4:-}"
EXPECTED_FE_DIGEST="${5:-}"
MODE="${6:-defer}"
EVIDENCE_FILE="${RELEASE_EVIDENCE_FILE:-/tmp/release-gate-evidence.txt}"

[ -n "$DS_REF" ] && [ -n "$FE_REF" ] || { echo "usage: release_gate.sh [DS_REF] [FE_REF] [EXPECTED_VER] [DS_DIGEST?] [FE_DIGEST?] [defer|strict]"; exit 2; }
[ -n "$EXPECTED_VERSION" ] || { echo "no expected datasette version (pass arg3 or fix pyproject derivation)"; exit 2; }
case "$MODE" in defer|strict) ;; *) echo "MODE must be defer or strict (got: $MODE)"; exit 2;; esac

COMPOSE_ARGS=(-p smoke-stack -f docker-compose.yml -f tests/smoke-stack/docker-compose.smoke.yml)
HEAD_SHA="$(git rev-parse HEAD 2>/dev/null || echo 'no-git')"
PROVENANCE_NOTE="${PROVENANCE_NOTE:-}"

cleanup() {
  docker compose "${COMPOSE_ARGS[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

fail_recorded() {
  echo "RELEASE-GATE-FAILED: $1"
  exit 1
}

# defer-mode deferral: record the observed state + reason, exit 0 (do NOT run
# the smoke against refs that violate the intended-release expectations).
defer_recorded() {
  local reason="$1"
  {
    echo "# Smoke release-gate evidence (DEFERRED)"
    echo "generated            : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "commit               : $HEAD_SHA (checked-out tree this gate ran from)"
    [ -n "$PROVENANCE_NOTE" ] && echo "provenance-note      : $PROVENANCE_NOTE"
    echo "mode                 : defer"
    echo "deferred             : YES — $reason"
    echo "intended refs (compose pin): $DS_REF / $FE_REF"
    echo "expected version (pyproject): $EXPECTED_VERSION"
    echo
    echo "A strict run (master push, or explicit refs+version) enforces the real"
    echo "gate once the compose pin and the published images carry the bump."
    echo "Nothing was represented as tested that was not."
  } | tee "$EVIDENCE_FILE"
  exit 0
}

echo "== release gate (mode: $MODE) =="
echo "datasette ref        : $DS_REF"
echo "frontend ref         : $FE_REF"
echo "expected datasette   : $EXPECTED_VERSION"
echo "digest expectations  : $([ -n "$EXPECTED_DS_DIGEST" ] && echo "ds=$EXPECTED_DS_DIGEST" || echo "ds=(none)") $([ -n "$EXPECTED_FE_DIGEST" ] && echo "fe=$EXPECTED_FE_DIGEST" || echo "fe=(none)")"
echo ""

# 1 — pull exact refs + capture registry digests
if ! docker pull -q "$DS_REF"; then
  [ "$MODE" = "defer" ] && defer_recorded "intended datasette ref not pullable yet: $DS_REF (not published at this commit's state)"
  fail_recorded "could not pull datasette release ref: $DS_REF"
fi
if ! docker pull -q "$FE_REF"; then
  [ "$MODE" = "defer" ] && defer_recorded "intended frontend ref not pullable yet: $FE_REF (not published at this commit's state)"
  fail_recorded "could not pull frontend release ref: $FE_REF"
fi
DS_DIGEST="$(docker buildx imagetools inspect "$DS_REF" | awk '/^Digest:/ {print $2; exit}')"
FE_DIGEST="$(docker buildx imagetools inspect "$FE_REF" | awk '/^Digest:/ {print $2; exit}')"
[ -n "$DS_DIGEST" ] && [ -n "$FE_DIGEST" ] || fail_recorded "could not read registry digests"

DS_VER="$(docker run --rm --entrypoint /app/.venv/bin/python "$DS_REF" -c 'import datasette; print(datasette.__version__)' 2>/dev/null | tail -1)"
[ -n "$DS_VER" ] || fail_recorded "could not probe in-image datasette version"

# 2 — digest expectations (verify when supplied, else record + flag)
DS_DIG_OK="not-supplied"; FE_DIG_OK="not-supplied"
if [ -n "$EXPECTED_DS_DIGEST" ]; then
  [ "$DS_DIGEST" = "$EXPECTED_DS_DIGEST" ] || fail_recorded "datasette digest mismatch: got $DS_DIGEST expected $EXPECTED_DS_DIGEST"
  DS_DIG_OK="match"
fi
if [ -n "$EXPECTED_FE_DIGEST" ]; then
  [ "$FE_DIGEST" = "$EXPECTED_FE_DIGEST" ] || fail_recorded "frontend digest mismatch: got $FE_DIGEST expected $EXPECTED_FE_DIGEST"
  FE_DIG_OK="match"
fi

# 3 — version expectation (the non-hardcoded gate)
if [ "$DS_VER" != "$EXPECTED_VERSION" ]; then
  if [ "$MODE" = "defer" ]; then
    defer_recorded "intended release not verifiable yet: refs serve datasette $DS_VER but pyproject expects $EXPECTED_VERSION (dependency bump merged, compose pin-bump pending)"
  fi
  fail_recorded "datasette version mismatch: image reports $DS_VER, expected $EXPECTED_VERSION (compose pin may lag the dependency bump — that is a pre-deploy blocker by design)"
fi

# 4 — the identical disposable smoke on the exact release refs
SMOKE_RUNTIME_FILE="$(mktemp /tmp/release-runtime.XXXXXX.txt)"
if ! SMOKE_RUNTIME_FILE="$SMOKE_RUNTIME_FILE" \
  bash "$SCRIPT_DIR/run_smoke_stack.sh" "$DS_REF" "$FE_REF" "http://127.0.0.1:8891" 1; then
  fail_recorded "smoke checks failed on the exact release refs"
fi

# 5 — negative control on the same release refs (checker self-proof)
if ! bash "$SCRIPT_DIR/run_regressions.sh" "$DS_REF" "$FE_REF"; then
  fail_recorded "negative control failed against the release refs"
fi

# 6 — durable evidence record
{
  echo "# Smoke release-gate evidence"
  echo "generated            : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "commit               : $HEAD_SHA (checked-out tree this gate ran from)"
  [ -n "$PROVENANCE_NOTE" ] && echo "provenance-note      : $PROVENANCE_NOTE"
  echo "ds image             : $DS_REF"
  echo "ds digest            : $DS_DIGEST (expectation: ${DS_DIG_OK})"
  echo "fe image             : $FE_REF"
  echo "fe digest            : $FE_DIGEST (expectation: ${FE_DIG_OK})"
  echo "expected datasette   : $EXPECTED_VERSION"
  echo "observed datasette   : $DS_VER (in-image probe)"
  echo
  echo "## Runtime provenance (captured before teardown)"
  cat "$SMOKE_RUNTIME_FILE" 2>/dev/null || echo "(runtime file missing)"
  echo
  echo "## What was tested / what was NOT"
  echo "tested          : routing, frontend pages, data API, search-all, strip_columns," \
       "cache_headers, edge lockdown, owner bypass, negative control — against the EXACT" \
       "release image references above (never local rebuilds)"
  echo "NOT tested      : S3 bootstrap/download path (fixtures mounted; env blanked)," \
       "external TLS termination, Cloudflare edge behaviour — see README"
} | tee "$EVIDENCE_FILE"
rm -f "$SMOKE_RUNTIME_FILE"

echo ""
echo "RELEASE-GATE-PASSED: release refs verified (digest/version) + identical smoke green + negative control green"