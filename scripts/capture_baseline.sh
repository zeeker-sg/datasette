#!/usr/bin/env bash
# Phase 2 — capture baseline JSON against the PRE-MUTATION single-service stack.
#
# Run this BEFORE plan 04 removes `ports:` from datasette. It captures
# representative JSON responses to $ZEEKER_BASELINE_DIR (default
# .planning/baselines/phase-03-pre/) and commits
# them to git so verify_api_parity.sh has something to diff against post-deploy.
#
# Pre-req: `docker compose up -d` of the CURRENT (pre-Phase-2) compose, with
# datasette reachable at http://localhost:8001.
set -euo pipefail

BASE_URL="${ZEEKER_BASELINE_URL:-http://localhost:8001}"
OUT_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"
mkdir -p "$OUT_DIR"

# Strip volatile fields (timing, request IDs) so diffs are meaningful.
# Add fields here if first-run diff reveals more volatility (RESEARCH A8).
JQ_STRIP='walk(if type == "object" then del(.query_ms, .__time__, .request_duration_ms) else . end)'

echo "Capturing baselines from $BASE_URL into $OUT_DIR"

# Probe datasette is reachable
if ! curl -fsS "$BASE_URL/-/versions.json" >/dev/null; then
  echo "ERROR: datasette not reachable at $BASE_URL/-/versions.json" >&2
  echo "Run \`docker compose up -d\` against the CURRENT (pre-Phase-2) compose first." >&2
  exit 1
fi

# Always-capture endpoints (stable across all installs).
PATHS=(
  "/-/versions.json"
  "/-/metadata.json"
  "/-/plugins.json"
  "/.json"
)

# Discover databases from /.json and add per-database endpoints.
DBS=$(curl -fsS "$BASE_URL/.json" | jq -r 'keys[]?' || true)
for db in $DBS; do
  PATHS+=("/${db}.json?_size=10")
  # First two tables of each db (if any)
  TABLES=$(curl -fsS "$BASE_URL/${db}.json" | jq -r '.tables[0:2][]?.name' 2>/dev/null || true)
  for t in $TABLES; do
    PATHS+=("/${db}/${t}.json?_size=10")
  done
done

for path in "${PATHS[@]}"; do
  safe=$(printf '%s' "$path" | tr '/?=&' '____')
  out="$OUT_DIR/${safe#_}.json"
  echo "  -> $path  =>  $out"
  curl -fsS "$BASE_URL${path}" | jq "$JQ_STRIP" > "$out"
  echo "$path" > "${out%.json}.url"
done

# Drop a README so future readers know what this directory is.
cat > "$OUT_DIR/README.md" <<'EOF'
# Phase 2 baselines

Captured by `scripts/capture_baseline.sh` against the pre-Phase-2 single-service
Datasette stack (datasette directly exposed on `:8001`).

`scripts/verify_api_parity.sh` diffs the post-deploy responses (now coming via
Caddy on `:80`) against these files, with `query_ms`, `__time__`, and
`request_duration_ms` stripped.

If a baseline diff fails meaningfully, either:
  1. The change is intentional — re-run `capture_baseline.sh` against the
     pre-deploy stack and re-commit; or
  2. The change is a regression — fix it before shipping.
EOF

# Empty marker so the directory exists in git even if no baselines captured.
touch "$OUT_DIR/.gitkeep"

echo "Done. Commit $OUT_DIR to git."
