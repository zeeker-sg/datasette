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
