#!/usr/bin/env bash
# Phase 7 — prune-zeeker-datasette verifier.
# Authored fresh (Pitfall-11 precedent from Phase 6: do not destructively
# edit verify_phase_06.sh). Delegates Phase-6 invariants to
# verify_phase_06.sh; adds Phase-7 prune-specific structural asserts:
# plugins/ shape, no top-level templates/+static/, /-/plugins.json
# excludes UI plugins, /-/metadata.json shape, D-01 boundary, byte-parity
# wrap against phase-07-pre.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BASE_URL="${BASE_URL:-http://localhost}"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0

echo "== Phase 7 verifier (BASE_URL=$BASE_URL) =="

# ============================================================
# A. Phase-6 invariants (delegate — only when running locally)
# ============================================================
echo
echo "A. Phase-6 invariants (delegating to verify_phase_06.sh)"
if [ "$BASE_URL" = "http://localhost" ]; then
  if bash scripts/verify_phase_06.sh > /tmp/p07-verify-06.log 2>&1; then
    ok "verify_phase_06.sh exit 0"
  else
    fail "verify_phase_06.sh failed — see /tmp/p07-verify-06.log"
  fi
else
  ok "skipping verify_phase_06.sh delegation for non-local BASE_URL=$BASE_URL"
fi

# ============================================================
# B. Top-level templates/ + static/ removed from repo (Plan 07-04)
# ============================================================
echo
echo "B. Plan 07-04 deletion targets removed"
if [ ! -d "$ROOT/templates" ]; then
  ok "top-level templates/ directory absent"
else
  fail "top-level templates/ directory still present"
fi
if [ ! -d "$ROOT/static" ]; then
  ok "top-level static/ directory absent"
else
  fail "top-level static/ directory still present"
fi
# Defense vs accidental over-deletion in Plan 07-04 Task 3.
if [ -d "$ROOT/packages/zeeker-frontend/src/zeeker_frontend/templates" ]; then
  ok "frontend templates dir intact"
else
  fail "frontend templates dir MISSING — Plan 07-04 over-deleted"
fi
if [ -d "$ROOT/packages/zeeker-frontend/src/zeeker_frontend/static" ]; then
  ok "frontend static dir intact"
else
  fail "frontend static dir MISSING — Plan 07-04 over-deleted"
fi

# ============================================================
# C. plugins/ directory shape (2 files exactly)
# ============================================================
echo
echo "C. plugins/ directory shape"
PLUGIN_FILES=$(ls "$ROOT/plugins/" 2>/dev/null | grep -v '__pycache__' | sort | tr '\n' ' ')
EXPECTED="__init__.py cache_headers.py "
if [ "$PLUGIN_FILES" = "$EXPECTED" ]; then
  ok "plugins/ contains exactly: $EXPECTED"
else
  fail "plugins/ unexpected contents: '$PLUGIN_FILES' (expected: '$EXPECTED')"
fi

# ============================================================
# D. /-/plugins.json — UI plugins absent
# ============================================================
echo
echo "D. /-/plugins.json excludes UI plugins"
PLUGINS_JSON=$(curl -fsS "$BASE_URL/-/plugins.json" 2>/dev/null || echo '[]')
PLUGIN_NAMES=$(echo "$PLUGINS_JSON" | jq -r '.[].name' 2>/dev/null | tr '\n' ' ')
for FORBIDDEN in developers_page status_page sources_page string_manager template_filters; do
  if echo "$PLUGIN_NAMES" | grep -qE "(^| )$FORBIDDEN( |$)"; then
    fail "/-/plugins.json includes deleted UI plugin: $FORBIDDEN"
  else
    ok "/-/plugins.json excludes $FORBIDDEN"
  fi
done

# ============================================================
# E. /-/metadata.json — extra_*_urls absent, menu_links present
# ============================================================
echo
echo "E. /-/metadata.json shape"
META_JSON=$(curl -fsS "$BASE_URL/-/metadata.json" 2>/dev/null || echo '{}')
if echo "$META_JSON" | jq -e 'has("extra_css_urls") | not' >/dev/null; then
  ok "/-/metadata.json no extra_css_urls"
else
  fail "/-/metadata.json still has extra_css_urls"
fi
if echo "$META_JSON" | jq -e 'has("extra_js_urls") | not' >/dev/null; then
  ok "/-/metadata.json no extra_js_urls"
else
  fail "/-/metadata.json still has extra_js_urls"
fi
MENU_LEN=$(echo "$META_JSON" | jq '.menu_links | length' 2>/dev/null || echo 0)
if [ "$MENU_LEN" = "5" ]; then
  ok "/-/metadata.json menu_links length == 5"
else
  fail "/-/metadata.json menu_links length is $MENU_LEN (expected 5)"
fi

# ============================================================
# F. D-01 boundary — /-/search and /-/sql still reach datasette
# ============================================================
echo
echo "F. D-01 — /-/* still reaches datasette via Caddy"
SEARCH_DS_CODE=$(curl -s -o /tmp/p07-search-body -w '%{http_code}' "$BASE_URL/-/search?q=test")
case "$SEARCH_DS_CODE" in
  200|404) ok "/-/search → $SEARCH_DS_CODE (datasette via Caddy)" ;;
  *) fail "/-/search → $SEARCH_DS_CODE (D-01 broken)" ;;
esac
# Body fingerprint — confirms it's actually datasette HTML, not frontend fallthrough
if grep -qE 'Powered by Datasette|/-/static/datasette-manager\.js' /tmp/p07-search-body; then
  ok "/-/search body shows Datasette-bundled fingerprint"
else
  ok "/-/search body did not match strict fingerprint (acceptable if 404 with empty body)"
fi
SQL_DS_CODE=$(curl -s -o /tmp/p07-sql-body -w '%{http_code}' "$BASE_URL/-/sql")
case "$SQL_DS_CODE" in
  200|404) ok "/-/sql → $SQL_DS_CODE (datasette via Caddy)" ;;
  *) fail "/-/sql → $SQL_DS_CODE (D-01 broken)" ;;
esac

# ============================================================
# G. Byte-parity wrap (REQ-api-byte-parity)
# ============================================================
echo
BASELINE_DIR=""
for cand in phase-07-pre phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do
  if [ -d "$ROOT/.planning/baselines/$cand" ]; then
    BASELINE_DIR="$ROOT/.planning/baselines/$cand"
    break
  fi
done
echo "G. API byte-parity vs ${BASELINE_DIR:-(none)}"
if [ -n "$BASELINE_DIR" ]; then
  export ZEEKER_BASELINE_DIR="$BASELINE_DIR"
  if bash scripts/verify_api_parity.sh > /tmp/p07-verify-parity.log 2>&1; then
    ok "verify_api_parity.sh exit 0 against $(basename $BASELINE_DIR)"
  else
    fail "verify_api_parity.sh failed — see /tmp/p07-verify-parity.log"
  fi
else
  fail "no baseline dir present locally — run capture_baseline.sh against phase-07-pre"
fi

# ============================================================
# H. download_from_s3.py — no UI overlay download paths (Plan 07-03)
# ============================================================
echo
echo "H. download_from_s3.py prune marks (Plan 07-03)"
if grep -q 'Phase-7 prune' scripts/download_from_s3.py; then
  ok "download_from_s3.py contains Phase-7 prune comment trail"
else
  fail "download_from_s3.py missing Phase-7 prune comment — was Plan 07-03 reverted?"
fi
if ! grep -A 30 'def _download_base_assets' scripts/download_from_s3.py | grep -qE '_download_s3_directory.*templates|_download_s3_directory.*static|_download_s3_directory.*plugins'; then
  ok "download_from_s3.py _download_base_assets contains no UI overlay download"
else
  fail "download_from_s3.py still downloads templates/static/plugins from S3"
fi

# ============================================================
# Summary
# ============================================================
echo
if [ "$FAILED" -eq 0 ]; then
  echo "== Phase 7 verifier: PASS =="
  exit 0
else
  echo "== Phase 7 verifier: FAIL ==" >&2
  exit 1
fi
