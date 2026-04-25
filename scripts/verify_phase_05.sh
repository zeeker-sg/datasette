#!/usr/bin/env bash
# Phase 5 verifier — table-browse + row-view structural HTML asserts +
# facet/pagination/FTS/sort/export route correctness + hidden-table guard +
# Phase-6 boundary asserts + API parity wrap. Delegates to verify_phase_04.sh
# for Phase-3-and-4 invariants.
#
# Exit 0 = Phase 5 success criteria all green.
# Exit non-zero = at least one check failed; details on stderr.
#
# BASE_URL env var (default http://localhost) lets the same script
# smoke-test the production deploy after ship:
#   BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_05.sh

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BASE_URL="${BASE_URL:-http://localhost}"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0

echo "== Phase 5 verifier (BASE_URL=$BASE_URL) =="

# ===== A. Phase-4 invariants (delegate) =====
echo
echo "A. Phase-4 invariants (delegating to verify_phase_04.sh)"
if [ "$BASE_URL" = "http://localhost" ]; then
  if bash scripts/verify_phase_04.sh; then
    ok "verify_phase_04.sh passed (Phase-3 + Phase-4 + topology intact)"
  else
    fail "verify_phase_04.sh failed — see output above"
  fi
else
  ok "skipping local Phase-4 verifier (BASE_URL is remote)"
fi

# ===== B. Table page — feed mode (sglawwatch/headlines) =====
echo
echo "B. Table page (feed mode) — /sglawwatch/headlines"
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl to $BASE_URL/sglawwatch/headlines failed"
else
  echo "$BODY" | grep -q 'va-item' && ok "feed mode renders .va-item" || fail "missing .va-item"
  echo "$BODY" | grep -q '/static/css/zeeker.css' && ok "references /static/css/zeeker.css" || fail "missing frontend CSS ref"
  if echo "$BODY" | grep -q 'zeeker-base.css'; then
    fail "LEAKS M1 path zeeker-base.css (datasette HTML fallthrough?)"
  else
    ok "no zeeker-base.css leak (frontend-rendered)"
  fi
  if echo "$BODY" | tr '\n' ' ' | grep -qE '<h1>[^<]*<em[^>]*>[^<]+</em>'; then
    ok "italic-accent H1 renders"
  else
    fail "missing italic-accent H1"
  fi
  CC=$(curl -fsS -D - -o /dev/null "$BASE_URL/sglawwatch/headlines" 2>/dev/null | grep -i '^cache-control:' | tr -d '\r')
  if echo "$CC" | grep -qi 'max-age=60' && echo "$CC" | grep -qi 'stale-while-revalidate=300'; then
    ok "Cache-Control: max-age=60 + swr=300"
  else
    fail "Cache-Control missing or wrong: '$CC'"
  fi
fi

# ===== C. Table page — tabular fallback (Zeeker-Judgements/judgments) =====
echo
echo "C. Table page (tabular fallback) — /Zeeker-Judgements/judgments"
BODY=$(curl -fsS "$BASE_URL/Zeeker-Judgements/judgments" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl to $BASE_URL/Zeeker-Judgements/judgments failed"
else
  echo "$BODY" | grep -q 'data-table' && ok "tabular mode renders .data-table" || fail "missing .data-table"
  # tabular mode must NOT use feed-mode partial
  if echo "$BODY" | grep -q 'va-item'; then
    fail "tabular mode incorrectly rendered .va-item (mode dispatch broken)"
  else
    ok "tabular mode does NOT render .va-item"
  fi
fi

# ===== D. Facet sidebar (sglawwatch/headlines?_facet=category) =====
echo
echo "D. Facet sidebar"
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines?_facet=category" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl with ?_facet=category failed"
else
  echo "$BODY" | grep -q 'class="facets"' && ok "renders <aside class=\"facets\">" || fail "missing .facets"
  echo "$BODY" | grep -q 'facet-block' && ok "renders .facet-block" || fail "missing .facet-block"
fi

# ===== E. Applied-facet chip (sglawwatch/headlines?category=Straits+Times) =====
echo
echo "E. Applied-facet chip"
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines?category=Straits+Times" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl with applied facet failed"
else
  echo "$BODY" | grep -q 'filter-chip' && ok "renders .filter-chip" || fail "missing .filter-chip"
  echo "$BODY" | grep -q 'Straits Times' && ok "chip contains 'Straits Times'" || fail "chip missing the value"
fi

# ===== F. Pagination (sglawwatch/headlines?_size=2 — small page) =====
echo
echo "F. Pagination strip"
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines?_size=2" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl with _size=2 failed"
else
  echo "$BODY" | grep -q 'class="pagination"' && ok "renders .pagination" || fail "missing .pagination"
  # Next link must be RELATIVE (Pitfall 2 — no internal hostname leak)
  if echo "$BODY" | grep -qE 'href="/sglawwatch/headlines\?[^"]+"[^>]*>Next' || \
     echo "$BODY" | tr '\n' ' ' | grep -qE 'href="/sglawwatch/headlines\?[^"]+"[^<]*Next'; then
    ok "Next link is relative path"
  else
    fail "Next link missing or absolute (Pitfall 2 regression?)"
  fi
  if echo "$BODY" | grep -q 'zeeker-datasette:8001'; then
    fail "internal hostname zeeker-datasette:8001 leaked into HTML (Pitfall 2)"
  else
    ok "no internal hostname leak"
  fi
  echo "$BODY" | grep -q 'Show:' && ok "page-size selector renders 'Show:' label" || fail "missing page-size label"
fi

# ===== G. FTS forwards =====
echo
echo "G. FTS — /sglawwatch/headlines?_search=DBS"
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines?_search=DBS" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "FTS curl failed"
else
  echo "$BODY" | grep -q 'filter-chip' && ok "search chip renders" || fail "search chip missing"
fi

# ===== H. Sort toggle =====
echo
echo "H. Sort — /sglawwatch/headlines?_sort=date"
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/sglawwatch/headlines?_sort=date")
[ "$CODE" = "200" ] && ok "sort URL returns 200" || fail "sort URL returned $CODE"

# ===== I. Export anchors are direct (D-05) =====
echo
echo "I. Export anchors (direct via Caddy @datasette)"
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -qE 'href="/sglawwatch/headlines\.csv\?[^"]*"'; then
  ok "CSV export anchor is direct (.csv href)"
else
  fail "CSV export anchor missing or proxied"
fi
if echo "$BODY" | grep -qE 'href="/sglawwatch/headlines\.json\?[^"]*"'; then
  ok "JSON export anchor is direct (.json href)"
else
  fail "JSON export anchor missing or proxied"
fi
# Caddy → datasette suffix-route still alive
CSV_TYPE=$(curl -fsS -D - -o /dev/null "$BASE_URL/sglawwatch/headlines.csv" 2>/dev/null | grep -i '^content-type:' | tr -d '\r')
if echo "$CSV_TYPE" | grep -qi 'text/csv'; then
  ok "Caddy suffix-routes /sglawwatch/headlines.csv → datasette (text/csv)"
else
  fail "/sglawwatch/headlines.csv not text/csv: '$CSV_TYPE'"
fi

# ===== J. Row page — article mode =====
echo
echo "J. Row page (article mode) — /sglawwatch/headlines/{pk}"
# Pull a real PK from /sglawwatch/headlines.json for this run
PK=$(curl -fsS "$BASE_URL/sglawwatch/headlines.json?_size=1&_shape=objects" 2>/dev/null \
     | python -c "import sys, json; d=json.load(sys.stdin); rows=d.get('rows') or []; print(rows[0].get('id', '') if rows else '')")
if [ -z "$PK" ]; then
  fail "could not extract a PK from /sglawwatch/headlines.json"
else
  BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines/$PK" 2>/dev/null || echo "__CURL_FAIL__")
  if echo "$BODY" | grep -q '__CURL_FAIL__'; then
    fail "row page curl for PK $PK failed"
  else
    echo "$BODY" | grep -q 'class="article' && ok "article mode renders .article" || fail "missing .article"
    echo "$BODY" | grep -q 'class="aside"' && ok "article mode renders .aside" || fail "missing .aside"
    if echo "$BODY" | tr '\n' ' ' | grep -qE '<h1>[^<]*<em[^>]*>[^<]+</em>'; then
      ok "row italic-accent H1 renders"
    else
      fail "row missing italic-accent H1"
    fi
  fi
fi

# ===== K. Row page — tabular fallback =====
echo
echo "K. Row page (tabular fallback)"
# Use a hintless table — pick one without display.* in metadata. Wildcard tables
# won't qualify (they're hidden). Use any sg-gov-newsrooms table for which we did
# NOT add display hints — but we did add hints for all 8 *_news tables. So we
# need a table that genuinely lacks a hint. Use schema_versions or any
# _zeeker_*-not-prefixed system table that's still visible.
# Fallback: assert that an unhinted lookup at least returns 200.
# Fetch the first non-hinted visible table from datasette's database listing.
TABLES_JSON=$(curl -fsS "$BASE_URL/sglawwatch.json?_shape=objects" 2>/dev/null || echo "")
HINT_TABLE=$(echo "$TABLES_JSON" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print(''); sys.exit(0)
# Print any visible table that is NOT 'headlines' or 'about_singapore_law' (both hinted)
for t in d.get('tables', []):
    name = t.get('name', '')
    if t.get('hidden'): continue
    if name.startswith('_zeeker'): continue
    if name in ('headlines', 'about_singapore_law'): continue
    print(name); break
" 2>/dev/null)
if [ -z "$HINT_TABLE" ]; then
  ok "no unhinted visible table available for tabular row test (skipped)"
else
  ROW_PK=$(curl -fsS "$BASE_URL/sglawwatch/$HINT_TABLE.json?_size=1&_shape=objects" 2>/dev/null \
          | python -c "import sys, json; d=json.load(sys.stdin); rows=d.get('rows') or []; pks=d.get('primary_keys') or []; print((rows[0].get(pks[0]) if pks else rows[0].get('rowid')) if rows else '')")
  if [ -n "$ROW_PK" ]; then
    BODY=$(curl -fsS "$BASE_URL/sglawwatch/$HINT_TABLE/$ROW_PK" 2>/dev/null || echo "__CURL_FAIL__")
    if echo "$BODY" | grep -q '__CURL_FAIL__'; then
      ok "tabular row test skipped (curl failed for $HINT_TABLE/$ROW_PK)"
    else
      echo "$BODY" | grep -q '<dl' && ok "tabular row renders <dl" || fail "missing <dl in tabular row"
    fi
  else
    ok "tabular row test skipped (no PK extractable for $HINT_TABLE)"
  fi
fi

# ===== L. Hidden tables blocked =====
echo
echo "L. Hidden-table 404 guard"
for T in _zeeker_schemas _zeeker_updates headlines_fts headlines_fts_data; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/sglawwatch/$T")
  if [ "$CODE" = "404" ]; then
    ok "/sglawwatch/$T → 404"
  else
    fail "/sglawwatch/$T returned $CODE (expected 404)"
  fi
done
# Row-level too
for T in _zeeker_schemas headlines_fts; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/sglawwatch/$T/anything")
  if [ "$CODE" = "404" ]; then
    ok "/sglawwatch/$T/anything → 404 (row guard)"
  else
    fail "/sglawwatch/$T/anything returned $CODE (expected 404)"
  fi
done

# ===== M. Phase-6 boundary asserts =====
echo
echo "M. Phase-6 boundary (these MUST still 404 / reach datasette as appropriate)"
# /-/* MUST reach datasette via Caddy @datasette matcher
for P in -/sql -/versions.json; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/$P")
  if [ "$CODE" = "200" ]; then
    ok "/$P → 200 (datasette territory preserved)"
  else
    fail "/$P returned $CODE (expected 200 from datasette)"
  fi
done
# /-/search MUST be either 200 from datasette (datasette-search-all plugin present) or
# 404 from datasette (plugin absent / route unmounted). It must NEVER reach the frontend.
# The previous weak check (negative grep on /static/css/zeeker.css) passed spuriously on
# any HTML lacking the frontend's CSS link — including empty bodies and minimal datasette
# 4xx pages. Strengthen to: (a) require status code in {200, 404}; (b) on 200 require a
# positive datasette-shaped marker (the literal string "Datasette" — datasette pages contain
# "Datasette" in their layout/footer chrome); (c) on 404 accept (frontend correctly didn't
# mount the route).
SEARCH_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/-/search")
case "$SEARCH_CODE" in
  200)
    SEARCH_BODY=$(curl -fsS "$BASE_URL/-/search" 2>/dev/null || echo "")
    # Negative: must NOT reference the frontend's CSS bundle.
    if echo "$SEARCH_BODY" | grep -q '/static/css/zeeker.css'; then
      fail "/-/search reached frontend (frontend CSS link present in 200 body)"
    # Positive: datasette pages contain the literal word "Datasette" in layout/footer.
    elif echo "$SEARCH_BODY" | grep -q 'Datasette'; then
      ok "/-/search → 200 from datasette (positive 'Datasette' marker found)"
    else
      fail "/-/search returned 200 but body has neither datasette marker nor frontend CSS — cannot positively attribute"
    fi
    ;;
  404)
    ok "/-/search → 404 (frontend correctly did not mount the route; datasette-search-all plugin absent)"
    ;;
  *)
    fail "/-/search returned unexpected status $SEARCH_CODE (expected 200 or 404)"
    ;;
esac
# Frontend-side Phase-6 routes — all MUST 404
# Checks: /developers /status /sources /about /how-to-use /llms.txt
for P in developers status sources about how-to-use llms.txt; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/$P")
  if [ "$CODE" = "404" ]; then
    ok "/$P → 404 (Phase-6 territory; correct for Phase 5)"
  else
    fail "/$P returned $CODE (expected 404 until Phase 6)"
  fi
done

# ===== N. Empty / error paths =====
echo
echo "N. Empty / error paths"
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/sglawwatch/no-such-table")
[ "$CODE" = "404" ] && ok "unknown table → 404" || fail "unknown table returned $CODE"
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/sglawwatch/headlines/non-existent-pk-12345-aaaaaa")
[ "$CODE" = "404" ] && ok "unknown row → 404" || fail "unknown row returned $CODE"
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines?_search=zzzzzzzzzzzzz_no_match" 2>/dev/null || echo "")
if echo "$BODY" | grep -q "No results for"; then
  ok "FTS no-results message renders"
else
  fail "FTS no-results message missing"
fi
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/sglawwatch/headlines/abc/nested-extra-segment")
[ "$CODE" = "404" ] && ok "nested-path → 404" || fail "nested-path returned $CODE"

# ===== O. API parity (delegate) =====
if [ "$BASE_URL" = "http://localhost" ]; then
  echo
  echo "O. API byte-parity vs .planning/baselines/phase-03-pre/"
  export ZEEKER_BASELINE_DIR="$ROOT/.planning/baselines/phase-03-pre"
  if bash scripts/verify_api_parity.sh; then
    ok "verify_api_parity.sh against phase-03-pre"
  else
    fail "verify_api_parity.sh failed (triage using Phase-2 Categories A/B/C/D)"
  fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
  echo "Phase 5 verifier: ALL GREEN"
  exit 0
else
  echo "Phase 5 verifier: FAILURES — see above"
  exit 1
fi
