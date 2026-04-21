# Phase 3 pre-flip baselines (post-Phase-2, pre-Phase-3)

Captured 2026-04-21 against the post-Phase-2 stack: Caddy on `:80` transparent-proxying everything to `zeeker-datasette:8001`. Datasette `0.65.2`. Three databases (`sg-gov-newsrooms`, `sglawwatch`, `zeeker-judgements`).

Capture command:
```bash
ZEEKER_BASELINE_URL=http://localhost bash scripts/capture_baseline.sh
git mv .planning/baselines/phase-02 .planning/baselines/phase-03-pre
```

These are the parity baselines for **Phase 3** (suffix-based routing flip). After Phase 3 changes the Caddyfile from "everything → datasette" to "`*.json *.csv *.db /-/* → datasette`, else → frontend":
- `*.json` URLs in this baseline set must continue to return byte-identical responses (same path, just routed via the suffix matcher instead of the catch-all).
- `verify_api_parity.sh` will diff against this directory.

`scripts/verify_api_parity.sh` strips `query_ms`, `__time__`, and `request_duration_ms` before diffing.

## History

- The original `phase-02/` baselines were captured 2026-04-20 against the **pre-Phase-2** single-service stack on `localhost:8001`. They are preserved in git history at commits `efdd3d5`/`4036226` if needed for forensic comparison.
- Phase 2 shipped with both verifier scripts red on triage-grade non-regressions (host-base-URL drift, S3 metadata refresh, datasette version bump, daily import drift). See `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` for the full triage. The post-Caddy capture in this directory eliminates the host-base-URL noise and starts Phase 3 with a clean comparison point.

## When to recapture

- Phase 3 ships → recapture as `.planning/baselines/phase-04-pre/` against the post-suffix-routing stack.
- Datasette version pin changes → recapture (versions can drift JSON shape).
- A new database is added to the platform → re-run `capture_baseline.sh` (it auto-discovers via `/.json`).
- S3 metadata is intentionally rewritten → recapture so the new metadata is the new normal.

## If a parity diff fails meaningfully

1. The change is intentional → recapture against the new normal and recommit.
2. The change is a regression → fix it before shipping.
