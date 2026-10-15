#!/usr/bin/env bash
# release_gate.sh — release-artifact verification (CI + local).
#
# Pulls EXACT image references, reads their registry digests, verifies them
# against expectations WHEN SUPPLIED (optional), runs the disposable smoke
# stack + negative control against the DIGEST-PINNED form of the exact refs
# (immutable identity — the verified digest is bound to the executed
# artifact, no tag-inspect/tag-exec gap), and writes a durable evidence
# record on EVERY outcome: pass, defer, or failure. Nothing here touches
# production or zeeker stats surfaces.
#
# Source of truth defaults (derivations, NOT hardcoded versions):
#   DATASETTE_REF / FRONTEND_REF  default → the compose pin in
#                 docker-compose.yml (the production-intended release)
#   EXPECTED_DATASETTE_VERSION    default → the datasette== pin in
#                 pyproject.toml (the repo's dependency state)
#   EXPECTED_DS_DIGEST / EXPECTED_FE_DIGEST optional ("" = record observed,
#                 flag "no expectation supplied")
#
# MODE (arg 6; default below — explicit input implies strict):
#   strict — the pre-deployment blocker. Any unmet expectation (refs not
#         pullable, digest or version mismatch) FAILS with a full evidence
#         record including the observed identities.
#   defer — PR mode for the bump-merge → pin-bump-merge window: when the
#         intended release cannot be verified yet, record the OBSERVED
#         state (refs, digests, in-image version) + the reason, exit 0, and
#         do not run the smoke. Unrelated PRs are not blocked; the strict
#         master-push run enforces the real gate.
#   DEFAULT RULE: strict when any of refs / expected version were passed
#   explicitly (an explicit intended-release run always verifies strictly);
#   defer only for a fully derived run.
#
# Usage:
#   tests/smoke-stack/release_gate.sh [DS_REF] [FRONTEND_REF] \
#       [EXPECTED_DATASETTE_VERSION] [EXPECTED_DS_DIGEST] [EXPECTED_FE_DIGEST] \
#       [defer|strict]
# Env: PROVENANCE_NOTE, PR_HEAD_SHA, PR_HEAD_LABEL (optional provenance)
# Exit codes: 0 full verification passed · 1 a material check failed ·
#             2 setup/usage error. Deferred runs exit 0 WITH evidence.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

ARG_DS_REF="${1:-}"
ARG_FE_REF="${2:-}"
ARG_EXPECTED="${3:-}"

DS_REF="${ARG_DS_REF:-$(grep -E 'image: .*zeeker-datasette:' docker-compose.yml | awk '{print $2}')}"
FE_REF="${ARG_FE_REF:-$(grep -E 'image: .*zeeker-frontend:' docker-compose.yml | awk '{print $2}')}"
EXPECTED_VERSION="${ARG_EXPECTED:-$(grep -oE 'datasette==[0-9abrc.dev]+' pyproject.toml | head -1 | cut -d= -f3)}"
EXPECTED_DS_DIGEST="${4:-}"
EXPECTED_FE_DIGEST="${5:-}"

# (5) explicit intended-release input ⇒ strict by default
if [ -n "${6:-}" ]; then
  MODE="$6"
elif [ -n "$ARG_DS_REF" ] || [ -n "$ARG_FE_REF" ] || [ -n "$ARG_EXPECTED" ]; then
  MODE="strict"
else
  MODE="defer"
fi
# Durable evidence by default: a per-run timestamped file so concurrent or
# repeated runs (e.g. a validation sequence) can never overwrite a previous
# outcome's retained record. Explicit RELEASE_EVIDENCE_FILE wins.
EVIDENCE_FILE="${RELEASE_EVIDENCE_FILE:-/tmp/release-gate-evidence-$(date -u '+%Y%m%dT%H%M%SZ').txt}"

[ -n "$DS_REF" ] && [ -n "$FE_REF" ] || { echo "usage: release_gate.sh [DS_REF] [FE_REF] [EXPECTED_VER] [DS_DIGEST?] [FE_DIGEST?] [defer|strict]"; exit 2; }
[ -n "$EXPECTED_VERSION" ] || { echo "no expected datasette version (pass arg3 or fix pyproject derivation)"; exit 2; }
case "$MODE" in defer|strict) ;; *) echo "MODE must be defer or strict (got: $MODE)"; exit 2;; esac

COMPOSE_ARGS=(-p smoke-stack -f docker-compose.yml -f tests/smoke-stack/docker-compose.smoke.yml)
# (2) provenance: distinguish the PR head from the actually checked-out tree.
PR_HEAD_SHA="${PR_HEAD_SHA:-}"
PR_HEAD_LABEL="${PR_HEAD_LABEL:-}"
CHECKOUT_SHA="$(git rev-parse HEAD 2>/dev/null || echo 'no-git')"
PROVENANCE_NOTE="${PROVENANCE_NOTE:-}"

OUTCOME=""
DS_EXEC_REF="" FE_EXEC_REF=""
DS_ID="" FE_ID="" DS_EXEC_ID="" FE_EXEC_ID=""
DS_DIGEST="" FE_DIGEST="" DS_VER=""

cleanup() {
  docker compose "${COMPOSE_ARGS[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# Provenance block shared by every outcome (pass/defer/fail).
provenance_block() {
  echo "generated            : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "tested checkout      : $CHECKOUT_SHA (git rev-parse HEAD — the tree this gate executed from)"
  if [ -n "$PR_HEAD_SHA" ] && [ "$PR_HEAD_SHA" != "$CHECKOUT_SHA" ]; then
    echo "pr head sha          : $PR_HEAD_SHA (${PR_HEAD_LABEL:-PR head})"
    echo "checkout relation    : the checked-out merge ref CONTAINS the PR head but is NOT the head commit itself — the tested tree is the merge ref"
  elif [ -n "$PR_HEAD_SHA" ]; then
    echo "pr head sha          : $PR_HEAD_SHA (= the checked-out tree)"
  fi
  if [ -n "${PROVENANCE_NOTE:-}" ]; then
    echo "provenance-note      : $PROVENANCE_NOTE"
  fi
}

# Observed-identity block shared by every outcome; reflects everything the
# gate learned even when it defers or fails afterwards.
observed_block() {
  echo "intended refs (compose pin): $DS_REF / $FE_REF"
  echo "expected version (pyproject): $EXPECTED_VERSION"
  if [ -n "$DS_DIGEST" ] || [ -n "$FE_DIGEST" ]; then
    echo "observed ds digest   : ${DS_DIGEST:-(not read)}"
    echo "observed fe digest   : ${FE_DIGEST:-(not read)}"
    [ -n "$EXPECTED_DS_DIGEST" ] && echo "ds digest expectation: $EXPECTED_DS_DIGEST"
    [ -n "$EXPECTED_FE_DIGEST" ] && echo "fe digest expectation: $EXPECTED_FE_DIGEST"
  else
    echo "observed digests     : (none — refs not pulled)"
  fi
  # Always report the observed/last-probed version: failure paths after a
  # successful probe (mismatch verdicts, smoke failures) retain it, and
  # earlier failures explicitly show it was never obtained.
  if [ -n "$DS_VER" ]; then
    echo "observed ds version  : $DS_VER (in-image probe)"
  else
    echo "observed ds version  : (not probed)"
  fi
}

fail_recorded() {
  local why="$1"
  {
    echo "# Smoke release-gate evidence (FAILED)"
    provenance_block
    echo "mode                 : $MODE"
    echo "outcome              : FAILED — $why"
    echo
    observed_block
    echo
    echo "This is a pre-deployment blocker: nothing was tested, nothing passes."
  } | tee "$EVIDENCE_FILE"
  echo "RELEASE-GATE-FAILED: $why"
  exit 1
}

# defer-mode: record everything observed so far + the reason, exit 0.
defer_recorded() {
  local reason="$1"
  {
    echo "# Smoke release-gate evidence (DEFERRED)"
    provenance_block
    echo "mode                 : defer"
    echo "outcome              : DEFERRED — $reason"
    echo
    observed_block
    echo
    echo "IMPORTANT: nothing was smoke-tested and NO negative control ran in"
    echo "this run — deferred is NOT release-verified. A strict run (master"
    echo "push, or explicit refs+version) enforces the real gate once the"
    echo "compose pin and the published images carry the bump."
  } | tee "$EVIDENCE_FILE"
  exit 0
}

echo "== release gate (mode: $MODE) =="
echo "datasette ref        : $DS_REF"
echo "frontend ref         : $FE_REF"
echo "expected datasette   : $EXPECTED_VERSION"
echo "digest expectations  : $([ -n "$EXPECTED_DS_DIGEST" ] && echo "ds=$EXPECTED_DS_DIGEST" || echo "ds=(none)") $([ -n "$EXPECTED_FE_DIGEST" ] && echo "fe=$EXPECTED_FE_DIGEST" || echo "fe=(none)")"
echo "tested checkout      : $CHECKOUT_SHA"
echo ""

# 1 — pull exact refs + capture registry digests + local image IDs
if ! docker pull -q "$DS_REF"; then
  [ "$MODE" = "defer" ] && defer_recorded "intended datasette ref not pullable yet: $DS_REF (not published at this commit's state)"
  fail_recorded "could not pull datasette release ref: $DS_REF"
fi
if ! docker pull -q "$FE_REF"; then
  [ "$MODE" = "defer" ] && defer_recorded "intended frontend ref not pullable yet: $FE_REF (not published at this commit's state)"
  fail_recorded "could not pull frontend release ref: $FE_REF"
fi
if ! DS_DIGEST="$(docker buildx imagetools inspect "$DS_REF" 2>/dev/null | awk '/^Digest:/ {print $2; exit}')"; then
  [ "$MODE" = "defer" ] && defer_recorded "registry inspect failed for datasette ref: $DS_REF"
  fail_recorded "registry inspect failed for datasette ref: $DS_REF"
fi
if ! FE_DIGEST="$(docker buildx imagetools inspect "$FE_REF" 2>/dev/null | awk '/^Digest:/ {print $2; exit}')"; then
  [ "$MODE" = "defer" ] && defer_recorded "registry inspect failed for frontend ref: $FE_REF"
  fail_recorded "registry inspect failed for frontend ref: $FE_REF"
fi
if [ -z "$DS_DIGEST" ] || [ -z "$FE_DIGEST" ]; then
  [ "$MODE" = "defer" ] && defer_recorded "registry digests unreadable (empty) for: $DS_REF / $FE_REF"
  fail_recorded "could not read registry digests for: $DS_REF / $FE_REF"
fi
if ! DS_ID="$(docker image inspect --format '{{.Id}}' "$DS_REF")"; then
  [ "$MODE" = "defer" ] && defer_recorded "local image inspect failed for datasette ref: $DS_REF"
  fail_recorded "local image inspect failed for datasette ref: $DS_REF"
fi
if ! FE_ID="$(docker image inspect --format '{{.Id}}' "$FE_REF")"; then
  [ "$MODE" = "defer" ] && defer_recorded "local image inspect failed for frontend ref: $FE_REF"
  fail_recorded "local image inspect failed for frontend ref: $FE_REF"
fi

if ! DS_VER="$(docker run --rm --entrypoint /app/.venv/bin/python "$DS_REF" -c 'import datasette; print(datasette.__version__)' 2>/dev/null | tail -1)"; then
  [ "$MODE" = "defer" ] && defer_recorded "in-image version probe failed for: $DS_REF"
  fail_recorded "could not probe in-image datasette version: $DS_REF"
fi
if [ -z "$DS_VER" ]; then
  [ "$MODE" = "defer" ] && defer_recorded "in-image version probe returned empty for: $DS_REF"
  fail_recorded "in-image datasette version probe empty: $DS_REF"
fi

# 2 — digest expectations (verify when supplied, else record + flag)
DS_DIG_OK="not-supplied"; FE_DIG_OK="not-supplied"
if [ -n "$EXPECTED_DS_DIGEST" ]; then
  if [ "$DS_DIGEST" != "$EXPECTED_DS_DIGEST" ]; then
    [ "$MODE" = "defer" ] && defer_recorded "intended datasette digest moved: $DS_REF serves $DS_DIGEST, expected $EXPECTED_DS_DIGEST (deferred, not tested)"
    fail_recorded "datasette digest mismatch: $DS_REF is $DS_DIGEST, expected $EXPECTED_DS_DIGEST"
  fi
  DS_DIG_OK="match"
fi
if [ -n "$EXPECTED_FE_DIGEST" ]; then
  if [ "$FE_DIGEST" != "$EXPECTED_FE_DIGEST" ]; then
    [ "$MODE" = "defer" ] && defer_recorded "intended frontend digest moved: $FE_REF serves $FE_DIGEST, expected $EXPECTED_FE_DIGEST (deferred, not tested)"
    fail_recorded "frontend digest mismatch: $FE_REF is $FE_DIGEST, expected $EXPECTED_FE_DIGEST"
  fi
  FE_DIG_OK="match"
fi

# 3 — version expectation (the non-hardcoded gate)
if [ "$DS_VER" != "$EXPECTED_VERSION" ]; then
  [ "$MODE" = "defer" ] && defer_recorded "intended release not verifiable yet: refs serve datasette $DS_VER but pyproject expects $EXPECTED_VERSION (dependency bump merged, compose pin-bump pending)"
  fail_recorded "datasette version mismatch: image reports $DS_VER, expected $EXPECTED_VERSION (compose pin may lag the dependency bump — that is a pre-deploy blocker by design)"
fi

# 4 — (3) bind the verified identity to the EXECUTED artifact: run the smoke
#     + negative control against the DIGEST-pinned refs (immutable), with
#     the local image IDs recorded for the tie.
DS_EXEC_REF="${DS_REF%%:*}@${DS_DIGEST}"
FE_EXEC_REF="${FE_REF%%:*}@${FE_DIGEST}"
if ! DS_EXEC_ID="$(docker image inspect --format '{{.Id}}' "$DS_EXEC_REF")"; then
  fail_recorded "digest-pinned datasette ref not locally resolvable: $DS_EXEC_REF"
fi
if ! FE_EXEC_ID="$(docker image inspect --format '{{.Id}}' "$FE_EXEC_REF")"; then
  fail_recorded "digest-pinned frontend ref not locally resolvable: $FE_EXEC_REF"
fi
[ "$DS_EXEC_ID" = "$DS_ID" ] && [ "$FE_EXEC_ID" = "$FE_ID" ] || fail_recorded "digest-ref resolves to a different local image than the verified ref (unexpected local state)"

# 5 — the identical disposable smoke, on the digest-pinned release refs
SMOKE_RUNTIME_FILE="$(mktemp /tmp/release-runtime.XXXXXX.txt)"
if ! SMOKE_RUNTIME_FILE="$SMOKE_RUNTIME_FILE" \
  bash "$SCRIPT_DIR/run_smoke_stack.sh" "$DS_EXEC_REF" "$FE_EXEC_REF" "http://127.0.0.1:8891" 1; then
  OUTCOME="smoke failed against the digest-pinned release refs"
  {
    echo "# Smoke release-gate evidence (FAILED)"
    provenance_block
    echo "mode                 : $MODE"
    echo "outcome              : FAILED — $OUTCOME"
    echo
    observed_block
    echo "executed ds ref      : $DS_EXEC_REF (id $DS_EXEC_ID)"
    echo "executed fe ref      : $FE_EXEC_REF (id $FE_EXEC_ID)"
  } | tee "$EVIDENCE_FILE"
  echo "RELEASE-GATE-FAILED: $OUTCOME"
  exit 1
fi

# 6 — negative control against the same digest-pinned refs
if ! bash "$SCRIPT_DIR/run_regressions.sh" "$DS_EXEC_REF" "$FE_EXEC_REF"; then
  {
    echo "# Smoke release-gate evidence (FAILED)"
    provenance_block
    echo "mode                 : $MODE"
    echo "outcome              : FAILED — negative control FAILED against the release refs"
    echo
    observed_block
    echo "executed ds ref      : $DS_EXEC_REF (id $DS_EXEC_ID)"
    echo "executed fe ref      : $FE_EXEC_REF (id $FE_EXEC_ID)"
  } | tee "$EVIDENCE_FILE"
  echo "RELEASE-GATE-FAILED: negative control failed against the release refs"
  exit 1
fi

# 7 — durable evidence record (passed)
{
  echo "# Smoke release-gate evidence"
  provenance_block
  echo "mode                 : $MODE"
  echo "outcome              : PASSED"
  echo
  observed_block
  echo
  echo "## Executed artifacts (digest-bound)"
  echo "executed ds ref      : $DS_EXEC_REF"
  echo "executed ds image id : $DS_EXEC_ID (= verified ref's local id: match)"
  echo "executed fe ref      : $FE_EXEC_REF"
  echo "executed fe image id : $FE_EXEC_ID (= verified ref's local id: match)"
  echo
  echo "## Runtime provenance (captured before teardown; container image IDs)"
  cat "$SMOKE_RUNTIME_FILE" 2>/dev/null || echo "(runtime file missing)"
  echo
  echo "## What was tested / what was NOT"
  echo "tested          : routing, frontend pages, data API, search-all, strip_columns," \
       "cache_headers, edge lockdown, owner bypass, negative control — against the" \
       "DIGEST-PINNED forms of the exact release references above (never local rebuilds)"
  echo "NOT tested      : S3 bootstrap/download path — IMPORTANT: the smoke mounts its own" \
       "fixture metadata.json over the image-baked /app/metadata.json (single-file ro" \
       "bind mount), so the image's BAKED metadata content itself is not what is" \
       "exercised, and production's S3-delivered metadata/config delivery is out of" \
       "scope. Fixtures mount directly (env blanked); external TLS termination and" \
       "Cloudflare edge behaviour remain uncovered — see README"
} | tee "$EVIDENCE_FILE"
rm -f "$SMOKE_RUNTIME_FILE"

echo ""
echo "RELEASE-GATE-PASSED: digest-bound release refs verified + identical smoke green + negative control green"