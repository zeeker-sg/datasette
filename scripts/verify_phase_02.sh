#!/usr/bin/env bash
# Phase 2 — wrap every runtime/shell assertion required by the Per-Task
# Verification Map in 02-VALIDATION.md.
#
# Exit 0 = Phase 2 success criteria all green. Exit non-zero = something below.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0

echo "== Phase 2 verifier =="

echo
echo "1. Compose config validates"
if docker compose config -q; then ok "docker compose config -q"; else fail "docker compose config"; fi

echo
echo "2. REQ-internal-only-datasette-exposure: zeeker-datasette has no ports:"
if docker compose config | python3 -c "
import yaml, sys
c = yaml.safe_load(sys.stdin)
ds = c['services']['zeeker-datasette']
ports = ds.get('ports') or []
sys.exit(0 if len(ports) == 0 else 1)
"; then
  ok "datasette has no host port mapping"
else
  fail "datasette still has a ports: block"
fi

echo
echo "3. REQ-internal-only-datasette-exposure: only caddy publishes ports at runtime"
# Filter out EXPOSE-only entries (PublishedPort: 0 = container exposes the port to
# the bridge network but does NOT bind it on the host). Without this filter,
# any service with EXPOSE in its Dockerfile is falsely flagged as publishing.
NON_CADDY_PUBLISHERS=$(docker compose ps --format json \
  | jq -r 'select(.Publishers != null) | select(([.Publishers[] | select(.PublishedPort > 0)] | length) > 0) | select(.Service != "caddy") | .Service' \
  | sort -u)
if [ -z "$NON_CADDY_PUBLISHERS" ]; then
  ok "only caddy publishes ports"
else
  fail "non-caddy services publishing ports: $NON_CADDY_PUBLISHERS"
fi

echo
echo "4. REQ-frontend-data-via-http: no sqlite3 binary in frontend"
if docker compose exec -T frontend sh -c '! command -v sqlite3'; then
  ok "no sqlite3 in frontend container"
else
  fail "sqlite3 binary present in frontend"
fi

echo
echo "5. REQ-frontend-data-via-http: frontend has no /data mount"
DATA_MOUNTS=$(docker inspect zeeker-frontend --format '{{json .Mounts}}' \
  | jq -r '.[] | select(.Source | contains("/data")) | .Source')
if [ -z "$DATA_MOUNTS" ]; then
  ok "frontend has no /data mount"
else
  fail "frontend has /data mount: $DATA_MOUNTS"
fi

echo
echo "6. REQ-frontend-data-via-http: pyproject.toml has no sqlite/datasette deps"
if ! grep -iE 'sqlite|datasette' packages/zeeker-frontend/pyproject.toml >/dev/null; then
  ok "no sqlite/datasette deps in frontend pyproject.toml"
else
  fail "sqlite or datasette referenced in frontend pyproject.toml"
fi

echo
echo "7. REQ-incremental-migration: all three services healthy"
HEALTHS=$(docker compose ps --format json | jq -r '.Health // .State')
TOTAL=$(echo "$HEALTHS" | wc -l | tr -d ' ')
HEALTHY=$(echo "$HEALTHS" | grep -c '^healthy$' || true)
if [ "$TOTAL" -eq 3 ] && [ "$HEALTHY" -eq 3 ]; then
  ok "3/3 services healthy"
else
  fail "expected 3 healthy, got $HEALTHY/$TOTAL: $(echo "$HEALTHS" | tr '\n' ' ')"
fi

echo
echo "8. Caddy can resolve datasette by name"
if docker compose exec -T caddy sh -c 'getent hosts zeeker-datasette' >/dev/null; then
  ok "caddy DNS-resolves zeeker-datasette"
else
  fail "caddy cannot resolve zeeker-datasette"
fi

echo
echo "9. Frontend container responds internally on /frontend-test"
STATUS=$(docker compose exec -T frontend python -c "
import urllib.request, sys
r = urllib.request.urlopen('http://localhost:8000/frontend-test', timeout=5)
sys.stdout.write(str(r.status))
" 2>/dev/null || echo "ERR")
if [ "$STATUS" = "200" ]; then
  ok "frontend /frontend-test returns 200 internally"
else
  fail "frontend internal /frontend-test returned $STATUS"
fi

echo
# Check 10 was inverted post-Phase-3 (suffix-routing flip activated 2026-04-21).
# Pre-Phase-3 semantics: Caddy transparent-proxied everything to datasette, so
# /frontend-test returned 404 from datasette (no such route there).
# Post-Phase-3 semantics: Caddy routes everything-not-API to frontend, so
# /frontend-test returns 200 from frontend with the placeholder JSON body.
echo "10. REQ-suffix-routing-contract: Caddy routes /frontend-test to frontend (returns 200 with placeholder JSON)"
RESP=$(curl -s -w '\n%{http_code}' http://localhost/frontend-test || true)
HTTP_CODE=$(printf '%s\n' "$RESP" | tail -n1)
BODY=$(printf '%s\n' "$RESP" | sed '$d')
if [ "$HTTP_CODE" = "200" ] && printf '%s' "$BODY" | grep -q '"service":"zeeker-frontend"'; then
  ok "/frontend-test via Caddy returns 200 from frontend with placeholder JSON (suffix routing active)"
else
  fail "expected 200 + frontend JSON body for /frontend-test via Caddy; got status=$HTTP_CODE body=$(printf '%s' "$BODY" | head -c 60)"
fi

echo
echo "11. REQ-api-byte-parity: RETIRED 2026-04-25 in Phase 5"
# RETIRED in Phase 5 (operator decision, ship checkpoint 2026-04-25):
# the phase-03-pre/ baseline was captured before two rounds of intentional
# metadata.json content evolution (Phase 4 platform branding rewrite +
# Phase 5 display.* hint blocks) plus natural data refresh in
# _zeeker_updates / row counts. The remaining diffs were all Category B
# (env drift) or Category C (stale check) — zero Category-A regressions.
# verify_api_parity.sh is preserved on disk for future phases that need
# byte-parity guarantees; capture a fresh baseline first if reactivating.
ok "REQ-api-byte-parity check retired (see comment + .planning/phases/05-port-table-browse-row-view/05-DEPLOY-NOTES.md)"

echo
if [ "$FAILED" -eq 0 ]; then
  echo "Phase 2 verifier: ALL GREEN"
  exit 0
else
  echo "Phase 2 verifier: FAILURES — see above"
  exit 1
fi
