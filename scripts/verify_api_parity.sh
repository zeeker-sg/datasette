#!/usr/bin/env bash
# Phase 2 — diff post-deploy JSON responses against the pre-mutation baselines
# committed by capture_baseline.sh.
#
# Run AFTER `docker compose up -d` of the new three-service compose. The new
# entry point is http://localhost (Caddy on :80), no longer http://localhost:8001.
set -euo pipefail

BASE_URL="${ZEEKER_VERIFY_URL:-http://localhost}"
BASELINE_DIR="$(git rev-parse --show-toplevel)/.planning/baselines/phase-02"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

JQ_STRIP='walk(if type == "object" then del(.query_ms, .__time__, .request_duration_ms) else . end)'

if [ ! -d "$BASELINE_DIR" ] || [ -z "$(ls "$BASELINE_DIR"/*.json 2>/dev/null)" ]; then
  echo "ERROR: no baselines found in $BASELINE_DIR" >&2
  echo "Run scripts/capture_baseline.sh against the pre-Phase-2 stack first." >&2
  exit 1
fi

# Probe Caddy is up
if ! curl -fsS "$BASE_URL/-/versions.json" >/dev/null; then
  echo "ERROR: cannot reach $BASE_URL/-/versions.json (Caddy not up?)" >&2
  exit 1
fi

# For each baseline file, derive the URL path back from its filename and re-fetch.
fail=0
for baseline in "$BASELINE_DIR"/*.json; do
  fname=$(basename "$baseline" .json)
  # Reverse the safe-encoding: underscores become / ? = &. We ONLY have to
  # guess at separators because capture_baseline.sh maps all of them to "_";
  # the canonical URL set is small enough that we can re-derive by trying
  # the literal path. To keep this robust, capture_baseline.sh ALSO writes
  # a sidecar mapping file — but to avoid coupling we instead store the
  # original path inside each baseline payload as a `_baseline_path` field.
  # Since we are NOT modifying capture_baseline.sh's payload shape (it must
  # stay byte-identical to datasette's response for diffing), we use a
  # sibling .url file instead.
  url_file="${baseline%.json}.url"
  if [ ! -f "$url_file" ]; then
    # Backwards-compat: derive from fname by replacing underscores with /
    # (lossy but works for the canonical set). Skip with a warning.
    echo "WARN: no $url_file (baseline missing URL hint); skipping $fname" >&2
    continue
  fi
  path=$(cat "$url_file")
  current="$TMP_DIR/${fname}.json"
  if ! curl -fsS "$BASE_URL${path}" | jq "$JQ_STRIP" > "$current" 2>/dev/null; then
    echo "FAIL: could not fetch $BASE_URL${path}" >&2
    fail=1
    continue
  fi
  # /-/versions.json: structural diff only (version string IS the payload)
  if [ "$path" = "/-/versions.json" ]; then
    if ! diff -q <(jq -S 'keys' "$baseline") <(jq -S 'keys' "$current") >/dev/null; then
      echo "FAIL: structural diff for $path"
      diff <(jq -S 'keys' "$baseline") <(jq -S 'keys' "$current") || true
      fail=1
    else
      echo "OK (structural):  $path"
    fi
  else
    if ! diff -q "$baseline" "$current" >/dev/null; then
      echo "FAIL: byte diff for $path"
      diff "$baseline" "$current" | head -40 || true
      fail=1
    else
      echo "OK:               $path"
    fi
  fi
done

if [ "$fail" -ne 0 ]; then
  echo
  echo "REQ-api-byte-parity: FAIL — see diffs above." >&2
  exit 1
fi

echo
echo "REQ-api-byte-parity: PASS"
