#!/usr/bin/env bash
# Phase 4 verifier — structural HTML + /static/css + /static/fonts + routing delegation.
#
# Extends Phase 3 by adding positive structural assertions for the new
# home + database routes and tightening the "no M1 path" negative. Phase
# 3 invariants are preserved by delegation to verify_phase_03.sh.
#
# Exit 0 = Phase 4 success criteria all green.
# Exit non-zero = at least one check failed; details on stderr.
#
# BASE_URL env var (default http://localhost) lets the same script
# smoke-test the production deploy after ship:
#   BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh
#
# Note: positive/negative assertions are OR'ed with `|| true` where
# appropriate so the FAILED flag aggregates; we want the full summary,
# not first-failure abort.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BASE_URL="${BASE_URL:-http://localhost}"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0

echo "== Phase 4 verifier (BASE_URL=$BASE_URL) =="

# ===== A. Phase-3 invariants still hold (topology + routing) =====
echo
echo "A. Phase-3 invariants (delegating to verify_phase_03.sh)"
# Only run the full Phase-3 verifier when smoke-testing LOCAL stack.
# When BASE_URL is a public hostname, Phase-3's docker-centric checks
# (docker compose ps, internal Caddy admin) don't apply.
if [ "$BASE_URL" = "http://localhost" ]; then
  if bash scripts/verify_phase_03.sh; then
    ok "verify_phase_03.sh passed (topology + routing intact)"
  else
    fail "verify_phase_03.sh failed — see output above; triage at Plan 04-05 checkpoint"
  fi
else
  ok "skipping local Phase-3 verifier (BASE_URL is remote)"
fi

# ===== B. POSITIVE HTML — home page renders frontend =====
echo
echo "B. Home page structural assertions"

BODY=$(curl -fsS "$BASE_URL/" 2>/dev/null || echo "__CURL_FAIL__")

if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl to $BASE_URL/ failed"
else
  # Shell + layout markers
  echo "$BODY" | grep -q 'db-statband'       && ok "/ contains .db-statband"            || fail "/ missing .db-statband"
  echo "$BODY" | grep -q 'class="cards"'     && ok "/ contains .cards grid"             || fail "/ missing .cards grid"
  # Italic-accent H1 (Fraunces <em> inside <h1>)
  echo "$BODY" | grep -qE '<h1>[^<]*<em'     && ok "/ italic-accent H1 renders"         || fail "/ missing italic-accent H1"
  # Frontend CSS path
  echo "$BODY" | grep -q '/static/css/zeeker.css' && ok "/ references /static/css/zeeker.css" || fail "/ missing frontend CSS ref"
  # M1 CSS path absent (confirms NOT datasette HTML)
  if echo "$BODY" | grep -q 'zeeker-base.css'; then
    fail "/ LEAKS M1 path zeeker-base.css (datasette HTML fallthrough?)"
  else
    ok "/ does NOT reference zeeker-base.css (frontend-rendered)"
  fi
  # Cache-Control header
  CC=$(curl -fsSI "$BASE_URL/" 2>/dev/null | grep -i '^cache-control:' | tr -d '\r')
  if echo "$CC" | grep -qi 'max-age=60' && echo "$CC" | grep -qi 'stale-while-revalidate=300'; then
    ok "/ Cache-Control: max-age=60 + swr=300"
  else
    fail "/ Cache-Control header missing or wrong: '$CC'"
  fi
fi

# ===== C. POSITIVE HTML — database page renders frontend =====
echo
echo "C. Database page structural assertions"

BODY=$(curl -fsS "$BASE_URL/sglawwatch" 2>/dev/null || echo "__CURL_FAIL__")

if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl to $BASE_URL/sglawwatch failed"
else
  echo "$BODY" | grep -q 'db-header'       && ok "/sglawwatch contains .db-header"         || fail "/sglawwatch missing .db-header"
  echo "$BODY" | grep -q 'class="list"'    && ok "/sglawwatch contains .list"              || fail "/sglawwatch missing .list"
  echo "$BODY" | grep -q 'headlines'       && ok "/sglawwatch lists 'headlines' table"     || fail "/sglawwatch missing headlines"
  echo "$BODY" | grep -q '/static/css/zeeker.css' && ok "/sglawwatch references /static/css/zeeker.css" || fail "/sglawwatch missing frontend CSS ref"

  # HIDDEN-TABLE NEGATIVE: no _zeeker_* nor *_fts* in rendered body
  if echo "$BODY" | grep -q '_zeeker'; then
    fail "/sglawwatch leaks _zeeker_* hidden tables"
  else
    ok "/sglawwatch does NOT leak _zeeker_*"
  fi
  if echo "$BODY" | grep -q 'headlines_fts'; then
    fail "/sglawwatch leaks FTS internal 'headlines_fts'"
  else
    ok "/sglawwatch does NOT leak FTS internals"
  fi

  # Italic-accent H1
  echo "$BODY" | grep -qE '<h1>[^<]*<em'   && ok "/sglawwatch italic-accent H1 renders"    || fail "/sglawwatch missing italic-accent H1"
fi

# ===== D. NEGATIVE — unknown database returns 404 (not 500, not 200) =====
echo
echo "D. Unknown database routes"
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/nonexistent-database-phase-4-check")
if [ "$CODE" = "404" ]; then
  ok "/nonexistent-database returns 404"
else
  fail "/nonexistent-database returned $CODE (expected 404)"
fi

# ===== E. STATIC ASSETS — CSS + 3 fonts =====
echo
echo "E. Static assets"

CSS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/static/css/zeeker.css")
CSS_TYPE=$(curl -sI "$BASE_URL/static/css/zeeker.css" | grep -i '^content-type:' | tr -d '\r')
if [ "$CSS_CODE" = "200" ] && echo "$CSS_TYPE" | grep -qi 'text/css'; then
  ok "/static/css/zeeker.css → 200 text/css"
else
  fail "/static/css/zeeker.css code=$CSS_CODE type='$CSS_TYPE' (expected 200 + text/css)"
fi

for font in inter-latin jetbrains-mono-latin fraunces-latin; do
  F_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/static/fonts/${font}.woff2")
  if [ "$F_CODE" = "200" ]; then
    ok "/static/fonts/${font}.woff2 → 200"
  else
    fail "/static/fonts/${font}.woff2 code=$F_CODE (expected 200)"
  fi
done

# ===== F. PHASE-5 BOUNDARY — table/row routes still 404 (intentional) =====
echo
echo "F. Phase-5 boundary (table/row routes MUST still 404)"
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/sglawwatch/headlines")
if [ "$CODE" = "404" ]; then
  ok "/sglawwatch/headlines → 404 (Phase-5 territory; correct)"
else
  fail "/sglawwatch/headlines returned $CODE; expected 404 until Phase 5"
fi

# ===== G. API PARITY (belt-and-suspenders — REQ-api-byte-parity) =====
# Only run parity locally. For prod, this would need a tunneled baseline dir.
if [ "$BASE_URL" = "http://localhost" ]; then
  echo
  echo "G. API byte-parity vs .planning/baselines/phase-03-pre/"
  export ZEEKER_BASELINE_DIR="$ROOT/.planning/baselines/phase-03-pre"
  if bash scripts/verify_api_parity.sh; then
    ok "verify_api_parity.sh against phase-03-pre"
  else
    fail "verify_api_parity.sh failed (triage using Phase-2 Categories A/B/C/D)"
  fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
  echo "Phase 4 verifier: ALL GREEN"
  exit 0
else
  echo "Phase 4 verifier: FAILURES — see above"
  exit 1
fi
