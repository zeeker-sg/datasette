#!/usr/bin/env bash
# Phase 6 — auxiliary pages + /search + /sql verifier.
# Authored fresh per RESEARCH §Pitfall 11 (do not destructively edit verify_phase_05.sh).
# Delegates Phase-4 topology to verify_phase_04.sh; flips Phase-5 boundary asserts;
# adds Phase-6 positive structural asserts; wraps verify_api_parity.sh.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BASE_URL="${BASE_URL:-http://localhost}"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }

FAILED=0

echo "== Phase 6 verifier (BASE_URL=$BASE_URL) =="

# ============================================================
# A. Phase-4 invariants (delegate — only when running locally)
# ============================================================
echo
echo "A. Phase-4 invariants (delegating to verify_phase_04.sh)"
if [ "$BASE_URL" = "http://localhost" ]; then
  if bash scripts/verify_phase_04.sh > /tmp/p06-verify-04.log 2>&1; then
    ok "verify_phase_04.sh exit 0"
  else
    fail "verify_phase_04.sh failed — see /tmp/p06-verify-04.log"
  fi
else
  ok "skipping verify_phase_04.sh delegation for non-local BASE_URL=$BASE_URL"
fi

# ============================================================
# B. Phase-6 boundary flip — aux routes return 200 + civic-broadsheet body
# ============================================================
echo
echo "B. Phase-6 aux routes return 200 + italic-accent H1 + frontend CSS link"
for P in developers status sources about how-to-use; do
  BODY=$(curl -fsS "$BASE_URL/$P" 2>/dev/null || echo "__CURL_FAIL__")
  if echo "$BODY" | grep -q '__CURL_FAIL__'; then
    fail "/$P unreachable"
    continue
  fi
  if echo "$BODY" | tr '\n' ' ' | grep -qE '<h1>[^<]*<em[^>]*>[^<]+</em>'; then
    ok "/$P returns 200 with italic-accent H1"
  else
    fail "/$P missing italic-accent H1 (found: $(echo "$BODY" | grep -m1 '<h1' || echo 'no <h1>'))"
  fi
  if echo "$BODY" | grep -q '/static/css/zeeker.css'; then
    ok "/$P references /static/css/zeeker.css"
  else
    fail "/$P missing frontend CSS link"
  fi
  # Hidden-table filter: no _zeeker_ in response body
  if echo "$BODY" | grep -q '_zeeker'; then
    fail "/$P leaks _zeeker_* table reference"
  else
    ok "/$P has no _zeeker_ leakage"
  fi
  # No M1 stylesheet leak (Phase 7 boundary)
  if echo "$BODY" | grep -q 'zeeker-base.css'; then
    fail "/$P leaks M1 zeeker-base.css path (datasette fallthrough?)"
  else
    ok "/$P does not leak zeeker-base.css"
  fi
done

# ============================================================
# C. /llms.txt — text/plain Content-Type + canonical body shape
# ============================================================
echo
echo "C. /llms.txt"
CT=$(curl -fsS -D - -o /dev/null "$BASE_URL/llms.txt" 2>/dev/null | grep -i '^content-type:' | tr -d '\r')
if echo "$CT" | grep -qi 'text/plain'; then
  ok "/llms.txt Content-Type: text/plain"
else
  fail "/llms.txt wrong Content-Type: $CT"
fi
LLMS_BODY=$(curl -fsS "$BASE_URL/llms.txt" 2>/dev/null || echo "")
if echo "$LLMS_BODY" | head -1 | grep -q '^# data\.zeeker\.sg'; then
  ok "/llms.txt body starts with '# data.zeeker.sg'"
else
  fail "/llms.txt body header drift"
fi
if echo "$LLMS_BODY" | grep -q '_zeeker'; then
  fail "/llms.txt leaks _zeeker_ table"
else
  ok "/llms.txt no _zeeker_ leakage"
fi

# ============================================================
# D. /robots.txt — text/plain + GPTBot block preserved
# ============================================================
echo
echo "D. /robots.txt"
ROBOTS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/robots.txt")
if [ "$ROBOTS_CODE" = "200" ]; then
  ok "/robots.txt → 200"
else
  fail "/robots.txt → $ROBOTS_CODE"
fi
ROBOTS_BODY=$(curl -fsS "$BASE_URL/robots.txt" 2>/dev/null || echo "")
if echo "$ROBOTS_BODY" | grep -q 'User-agent: GPTBot'; then
  ok "/robots.txt preserves GPTBot block"
else
  fail "/robots.txt missing GPTBot block — verbatim port broken"
fi

# ============================================================
# E. /search — State A + State B + XSS escape
# ============================================================
echo
echo "E. /search"
SEARCH_A=$(curl -fsS "$BASE_URL/search" 2>/dev/null || echo "__FAIL__")
if echo "$SEARCH_A" | grep -q 'Search across'; then
  ok "/search State A renders hero"
else
  fail "/search State A missing 'Search across' header"
fi
if echo "$SEARCH_A" | grep -qE 'name="q"'; then
  ok "/search State A has form input"
else
  fail "/search State A missing form input"
fi
# State B — issue a safe q
SEARCH_B=$(curl -fsS "$BASE_URL/search?q=test" 2>/dev/null || echo "__FAIL__")
if echo "$SEARCH_B" | grep -qE 'Results for'; then
  ok "/search State B header rendered"
else
  fail "/search State B missing 'Results for' header"
fi
# XSS — Reflected XSS prevention (autoescape)
XSS_BODY=$(curl -fsS "$BASE_URL/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E" 2>/dev/null || echo "__FAIL__")
if echo "$XSS_BODY" | grep -qF '<script>alert(1)</script>'; then
  fail "/search reflected XSS — raw <script>alert(1)</script> leaked into body"
else
  ok "/search autoescapes <script> tag (no raw injection)"
fi

# ============================================================
# F. /sql + /sql/{db}
# ============================================================
echo
echo "F. /sql"
SQL_LANDING=$(curl -fsS "$BASE_URL/sql" 2>/dev/null || echo "__FAIL__")
if echo "$SQL_LANDING" | tr '\n' ' ' | grep -qE '<h1>Run\s*<em>SQL</em>'; then
  ok "/sql landing renders Run <em>SQL</em> H1"
else
  fail "/sql landing missing italic-accent H1"
fi

# Pick the first visible db link from the landing page for the editor test
FIRST_DB=$(echo "$SQL_LANDING" | grep -oE 'href="/sql/[^"]+"' | head -1 | sed 's|href="/sql/||;s|"||')
if [ -n "$FIRST_DB" ]; then
  SQL_EDITOR=$(curl -fsS "$BASE_URL/sql/$FIRST_DB" 2>/dev/null || echo "__FAIL__")
  if echo "$SQL_EDITOR" | grep -q '<textarea'; then
    ok "/sql/$FIRST_DB editor renders textarea"
  else
    fail "/sql/$FIRST_DB missing textarea"
  fi
fi

# ============================================================
# G. D-01 boundary — /-/search and /-/sql STILL reach datasette
# ============================================================
echo
echo "G. D-01 — /-/* still reaches datasette via Caddy"
SEARCH_DS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/-/search?q=test")
case "$SEARCH_DS_CODE" in
  200|404) ok "/-/search → $SEARCH_DS_CODE (datasette via Caddy)" ;;
  *) fail "/-/search → $SEARCH_DS_CODE (D-01 broken: should reach datasette)" ;;
esac
SQL_DS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/-/sql")
case "$SQL_DS_CODE" in
  200|404) ok "/-/sql → $SQL_DS_CODE (datasette via Caddy)" ;;
  *) fail "/-/sql → $SQL_DS_CODE (D-01 broken)" ;;
esac

# ============================================================
# H. Cache-Control on aux routes (D-14)
# ============================================================
echo
echo "H. Cache-Control headers"
for P in developers status sources about how-to-use llms.txt search sql; do
  CC=$(curl -fsS -D - -o /dev/null "$BASE_URL/$P" 2>/dev/null | grep -i '^cache-control:' | tr -d '\r' || echo '')
  if echo "$CC" | grep -qE 'max-age=60' && echo "$CC" | grep -qE 'stale-while-revalidate=300'; then
    ok "/$P Cache-Control: max-age=60 + stale-while-revalidate=300"
  else
    fail "/$P missing Cache-Control directives ($CC)"
  fi
done

# ============================================================
# I. main.py router order invariant (Pitfall 3)
# ============================================================
echo
echo "I. main.py router order"
MAIN_PY="packages/zeeker-frontend/src/zeeker_frontend/main.py"
if [ -f "$MAIN_PY" ]; then
  AUX_LINE=$(grep -nE '^\s*app\.include_router\(aux_router\)' "$MAIN_PY" | head -1 | cut -d: -f1 || echo "")
  SEARCH_LINE=$(grep -nE '^\s*app\.include_router\(search_router\)' "$MAIN_PY" | head -1 | cut -d: -f1 || echo "")
  SQL_LINE=$(grep -nE '^\s*app\.include_router\(sql_router\)' "$MAIN_PY" | head -1 | cut -d: -f1 || echo "")
  DB_LINE=$(grep -nE '^\s*app\.include_router\(database_router\)' "$MAIN_PY" | head -1 | cut -d: -f1 || echo "")
  if [ -z "$AUX_LINE" ] || [ -z "$SEARCH_LINE" ] || [ -z "$SQL_LINE" ] || [ -z "$DB_LINE" ]; then
    fail "missing one of: aux_router/search_router/sql_router/database_router include_router calls"
  else
    if [ "$AUX_LINE" -lt "$DB_LINE" ] && [ "$SEARCH_LINE" -lt "$DB_LINE" ] && [ "$SQL_LINE" -lt "$DB_LINE" ]; then
      ok "Phase-6 routers (aux=$AUX_LINE, search=$SEARCH_LINE, sql=$SQL_LINE) all precede database_router (line $DB_LINE)"
    else
      fail "router order violation: phase-6 routers must precede database_router (aux=$AUX_LINE, search=$SEARCH_LINE, sql=$SQL_LINE, db=$DB_LINE)"
    fi
  fi
else
  fail "main.py not found at $MAIN_PY"
fi

# ============================================================
# J. base.html nav re-pointed to /search
# ============================================================
echo
echo "J. base.html nav"
BASE_HTML="packages/zeeker-frontend/src/zeeker_frontend/templates/base.html"
if grep -qE 'href="/search"' "$BASE_HTML"; then
  ok "base.html links to /search"
else
  fail "base.html missing /search link"
fi
if grep -qE 'href="/-/search"' "$BASE_HTML"; then
  fail "base.html still has /-/search link (D-01 violation)"
else
  ok "base.html does not reference /-/search"
fi

# ============================================================
# K. API byte-parity wrap (REQ-api-byte-parity)
# ============================================================
# Prefer the most recent per-phase baseline if present (phase-06-pre,
# phase-05-pre, ...). Fall back to phase-03-pre (the original Phase-3
# pre-mutation baseline) so first-time runs on older checkouts still work.
echo
BASELINE_DIR=""
for cand in phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do
  if [ -d "$ROOT/.planning/baselines/$cand" ]; then
    BASELINE_DIR="$ROOT/.planning/baselines/$cand"
    break
  fi
done
echo "K. API byte-parity vs ${BASELINE_DIR:-(none)}"
if [ -n "$BASELINE_DIR" ]; then
  export ZEEKER_BASELINE_DIR="$BASELINE_DIR"
  if bash scripts/verify_api_parity.sh > /tmp/p06-verify-parity.log 2>&1; then
    ok "verify_api_parity.sh exit 0 against $(basename $BASELINE_DIR)"
  else
    fail "verify_api_parity.sh failed — see /tmp/p06-verify-parity.log"
  fi
else
  ok "skipping parity check (no baseline dir present locally)"
fi

# ============================================================
# Summary
# ============================================================
echo
if [ "$FAILED" -eq 0 ]; then
  echo "== Phase 6 verifier: PASS =="
  exit 0
else
  echo "== Phase 6 verifier: FAIL ==" >&2
  exit 1
fi
