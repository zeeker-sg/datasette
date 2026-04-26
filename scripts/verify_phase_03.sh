#!/usr/bin/env bash
# Phase 3 verifier — positive routing + negative routing + frontend reachability +
# edge cases + parity wrap.
#
# Run AFTER Plan 02's Caddyfile edit AND the Caddy container has been
# restarted to pick up the new config (the Plan 04 sequence — see
# 03-TEST-PLAN.md for the exact docker compose invocation). Running this
# against the pre-flip stack will FAIL the negative-routing assertions
# because Caddy is still transparent-proxying everything to datasette —
# that's a true negative but not what this verifier is for.
#
# Inherits Phase-2 topology invariants (datasette internal-only, no
# sqlite3 in frontend, etc.) by sourcing verify_phase_02.sh first.
#
# Exit 0 = Phase 3 routing-flip success criteria all green.
# Exit non-zero = at least one check failed; details on stderr.
#
# Background: the load-bearing test in this script is the
# `check_negative` function. It probes URLs that should hit frontend
# (and 404) and grep's the response body for `zeeker-base.css` — the
# unique datasette-HTML fingerprint. If a "negative" URL returns body
# containing `zeeker-base.css`, the matcher is silently fall-through-ing
# to datasette and the routing flip is broken even though status codes
# may look normal.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0

echo "== Phase 3 verifier =="

# ===== A. Caddyfile validates =====
echo
echo "A. Caddyfile validates"
if docker run --rm -v "$ROOT/Caddyfile:/etc/caddy/Caddyfile:ro" \
     caddy:2.11.2-alpine \
     caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile \
     >/dev/null 2>&1; then
  ok "Caddyfile passes caddy validate"
else
  fail "Caddyfile invalid"
fi

# ===== B. Phase-2 topology invariants still hold =====
# Phase 3 inherits everything Phase 2 verified (datasette internal-only,
# frontend has no sqlite, all 3 healthy, etc.). Per RESEARCH Open Q#2 we
# invoke the Phase-2 verifier first; failures here mean the topology
# itself drifted, not Phase 3's routing flip.
echo
echo "B. Phase-2 topology invariants (delegating to verify_phase_02.sh)"
if bash scripts/verify_phase_02.sh; then
  ok "verify_phase_02.sh passed (Phase-2 topology intact)"
else
  # NOTE: Phase-2's verifier has a known check-#3 jq false positive
  # (Phase-2 SUMMARY documents this; not a Phase-3 regression).
  # Don't auto-fix here; surface the failure for human triage at the
  # Plan 04 checkpoint (same Categories A/B/C/D triage Phase 2 used).
  fail "verify_phase_02.sh failed — see its output above; triage at Plan 04 checkpoint"
fi

# ===== C. POSITIVE ROUTING — these MUST reach datasette =====
echo
echo "C. Positive routing (must reach datasette)"

check_positive() {
  local path="$1" expected_substr="$2"
  local body
  body=$(curl -fsS "http://localhost${path}" 2>/dev/null || echo "__CURL_FAIL__")
  if echo "$body" | grep -q "$expected_substr"; then
    ok "$path → datasette ($expected_substr present)"
  else
    fail "$path missing expected '$expected_substr' (body head: $(echo "$body" | head -c 80))"
  fi
}

check_positive "/-/versions.json"                       '"datasette"'
check_positive "/sglawwatch.json"                        '"tables"'
check_positive "/sglawwatch/headlines.json?_size=1"      '"rows"'

# .csv is plain-text; check status only
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch/headlines.csv?_size=1")
if [ "$HTTP" = "200" ]; then
  ok "/sglawwatch/headlines.csv?_size=1 → 200"
else
  fail ".csv got $HTTP (expected 200)"
fi

# .db is 403 in current config (databases not downloadable per metadata.json)
# but it MUST reach datasette (403 from datasette, NOT frontend's 404).
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch.db")
if [ "$HTTP" = "403" ] || [ "$HTTP" = "200" ]; then
  ok "/sglawwatch.db → datasette (HTTP $HTTP, not frontend-404)"
else
  fail ".db got $HTTP (expected 403 or 200 from datasette; 404 would mean frontend-fallthrough)"
fi

# /-/sql is database-scoped → 404 from datasette (verified live: returns
# datasette HTML 404 with zeeker-base.css link). Body MUST contain
# datasette markers (proves it reached datasette).
BODY=$(curl -s "http://localhost/-/sql")
if echo "$BODY" | grep -qiE 'zeeker-base\.css|datasette'; then
  ok "/-/sql → datasette (zeeker-base.css/datasette in body)"
else
  fail "/-/sql did not reach datasette (body head: $(echo "$BODY" | head -c 80))"
fi

# /-/search — datasette-search-all plugin route.
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/-/search")
BODY=$(curl -s "http://localhost/-/search")
if [ "$HTTP" = "200" ] || [ "$HTTP" = "404" ]; then
  if echo "$BODY" | grep -qiE 'zeeker-base\.css|datasette|search'; then
    ok "/-/search → datasette (HTTP $HTTP)"
  else
    fail "/-/search did not reach datasette (body lacks datasette markers; head: $(echo "$BODY" | head -c 80))"
  fi
else
  fail "/-/search got $HTTP"
fi

# ===== D. NEGATIVE ROUTING — these MUST reach the frontend, NOT datasette =====
# The load-bearing assertion of this verifier. The body-content sniff
# for `zeeker-base.css` is the decisive guard against silent fall-through
# (RESEARCH Pitfall 1). Status code alone is NOT sufficient.
#
# Phase-3 origin: the frontend was a placeholder that 404'd every HTML
# path, so this check expected 404 + {"detail":"Not Found"}. After
# Phases 4-6 the frontend actually renders these routes, so the check
# was widened to: route is correctly served by the frontend if it's
# either (a) a frontend-rendered 200 (no zeeker-base.css, presence of
# the /static/css/zeeker.css link) or (b) the original Phase-3
# placeholder 404. Datasette HTML fallthrough still hard-fails.
echo
echo "D. Negative routing (HTML routes must reach frontend, NOT datasette HTML)"

check_negative() {
  local path="$1"
  local http
  http=$(curl -s -o /tmp/zeeker-neg-body -w '%{http_code}' "http://localhost${path}")

  # NOTE on grep vs echo|grep: `set -euo pipefail` + `echo "$body" | grep -q`
  # can fail with SIGPIPE (exit 141) when the body is large (e.g. Phase-5
  # table pages are ~800KB) — grep -q exits on first match, leaving echo
  # writing to a closed pipe, and pipefail surfaces the SIGPIPE as a
  # spurious "no match." Grepping the file directly side-steps this.

  # The decisive fallthrough sniff: datasette HTML always references
  # zeeker-base.css (verified live 2026-04-21 across /, /sglawwatch,
  # /sglawwatch/headlines, datasette's own 404 page).
  if grep -q 'zeeker-base.css' /tmp/zeeker-neg-body; then
    fail "$path FALLTHROUGH BUG: datasette HTML served (zeeker-base.css present in body)"
    return
  fi

  # Acceptable A — frontend rendered the route (Phases 4-6): 200 with
  # the frontend CSS link present.
  if [ "$http" = "200" ] && grep -q '/static/css/zeeker.css' /tmp/zeeker-neg-body; then
    ok "$path → frontend-rendered 200 (correct)"
    return
  fi

  # Acceptable B — frontend 404 (Phase-3 default `Not Found` OR Phase-5
  # row-handler's `Record not found`). Both are unmistakeably FastAPI
  # JSON-detail bodies; neither is datasette HTML.
  if [ "$http" = "404" ] && grep -qE '"detail":"(Not Found|Record not found)"' /tmp/zeeker-neg-body; then
    ok "$path → frontend 404 (correct)"
    return
  fi

  fail "$path got HTTP $http with body: $(head -c 80 /tmp/zeeker-neg-body)"
}

check_negative "/"
check_negative "/sglawwatch"
check_negative "/sglawwatch/headlines"
check_negative "/sg-gov-newsrooms"
check_negative "/zeeker-judgements"
check_negative "/developers"
check_negative "/about"
check_negative "/how-to-use"
check_negative "/status"
check_negative "/sources"
# Row-URL shape (3 path segments: db/table/pk). Catches a class of
# matcher bug where a regex only matches 1-2 segments. The pk is
# synthetic — datasette would 404 on it; what matters is the routing
# decision, not whether the row exists.
check_negative "/sglawwatch/headlines/synthetic-row-id-not-real"

# ===== E. FRONTEND REACHABILITY =====
# Proves the catch-all reverse_proxy frontend:8000 is reachable AND that
# the @datasette matcher is NOT over-matching /frontend-test (Pitfall 7).
echo
echo "E. Frontend /frontend-test still reachable"
BODY=$(curl -fsS "http://localhost/frontend-test" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '"status":"ok"' && echo "$BODY" | grep -q '"service":"zeeker-frontend"'; then
  ok "/frontend-test → frontend OK"
else
  fail "/frontend-test body unexpected: $BODY"
fi

# ===== F. EDGE CASES =====
echo
echo "F. Edge cases"

# Multi-dot URL with query string (RESEARCH Assumption A6)
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/sg-gov-newsrooms/_zeeker_schemas.json?_size=10")
if [ "$HTTP" = "200" ]; then
  ok "multi-dot+query .json → 200"
else
  fail "multi-dot+query got $HTTP (expected 200)"
fi

# HEAD vs GET symmetry (RESEARCH Pitfall 6)
HTTP_GET=$(curl -s  -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch.json?_size=1")
HTTP_HEAD=$(curl -sI -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch.json?_size=1")
if [ "$HTTP_GET" = "$HTTP_HEAD" ]; then
  ok "HEAD/GET symmetric ($HTTP_GET)"
else
  fail "HEAD=$HTTP_HEAD GET=$HTTP_GET (expected symmetric)"
fi

# Case-sensitivity (Caddy path matcher is case-insensitive)
BODY_UPPER=$(curl -s "http://localhost/SGLAWWATCH.JSON?_size=1")
if echo "$BODY_UPPER" | grep -qE 'zeeker-base\.css|"error"|"ok"|"tables"'; then
  ok "uppercase .JSON also routes to datasette (case-insensitive)"
else
  fail "uppercase .JSON may have fallen through (body: $(echo "$BODY_UPPER" | head -c 80))"
fi

# CORS headers preserved (CLAUDE.md: all API endpoints have CORS enabled)
CORS=$(curl -sI "http://localhost/-/versions.json" | grep -i '^access-control-allow-origin:' || true)
if [ -n "$CORS" ]; then
  ok "CORS preserved: $(echo "$CORS" | tr -d '\r')"
else
  fail "CORS header missing on /-/versions.json"
fi

# ===== G. PARITY (REQ-api-byte-parity) — uses parameterized verifier =====
# Prefer the most recent per-phase baseline; phase-03-pre is the original
# pre-mutation baseline kept as the floor. Each subsequent phase captures a
# fresh baseline so environmental drift (S3 metadata refresh, daily import
# row counts) doesn't compound across phases.
echo
PARITY_DIR=""
for cand in phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do
  if [ -d "$ROOT/.planning/baselines/$cand" ]; then
    PARITY_DIR="$ROOT/.planning/baselines/$cand"
    break
  fi
done
echo "G. API byte-parity vs ${PARITY_DIR:-(none)}"
if [ -n "$PARITY_DIR" ]; then
  export ZEEKER_BASELINE_DIR="$PARITY_DIR"
  if bash scripts/verify_api_parity.sh; then
    ok "verify_api_parity.sh against $(basename $PARITY_DIR)"
  else
    fail "verify_api_parity.sh failed (triage using Phase-2 Categories A/B/C/D)"
  fi
else
  ok "skipping parity check (no baseline dir present locally)"
fi

echo
if [ "$FAILED" -eq 0 ]; then
  echo "Phase 3 verifier: ALL GREEN"
  exit 0
else
  echo "Phase 3 verifier: FAILURES — see above"
  exit 1
fi
