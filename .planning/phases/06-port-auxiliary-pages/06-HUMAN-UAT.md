---
status: partial
phase: 06-port-auxiliary-pages
source: [06-VERIFICATION.md]
started: 2026-04-26T02:45:00Z
updated: 2026-04-26T02:45:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual QA sweep of every aux page in a real browser
expected: Italic-accent H1 with colored `<em>` visible; civic-broadsheet paper/petrol palette; 4-column footer renders; footer links contrast correctly against Datasette's `app.css` cascade; no layout regressions on /developers, /status, /sources, /about, /how-to-use, /search, /sql, /sql/{db}.
result: [pending]
notes: WR-01 (orphan CSS comment text near FOOTER LINK OVERRIDE block) flags potential cascade-skip risk that requires browser visual confirmation.

### 2. Re-baseline API parity reference and re-run scripts/verify_phase_06.sh against running stack
expected: All 11 sections (A–K) of `verify_phase_06.sh` exit OK after re-baselining `.planning/baselines/phase-03-pre/` → `phase-06-pre/` via `scripts/capture_baseline.sh`; `verify_api_parity.sh` exits 0.
result: [pending]
notes: Sections A and K currently FAIL on pre-existing Category-A/B environmental drift (S3 metadata refresh + daily import drift since April 2026 baseline capture). Phase 6 added zero new datasette routes (T-06-06-03 mitigation), so the parity drift is environmental, not a phase regression.

### 3. Production smoke against https://data.zeeker.sg/ aux routes
expected: Each of /developers, /status, /sources, /about, /how-to-use, /llms.txt, /search, /sql, /sql/{db}, /robots.txt returns 200 + civic-broadsheet body + correct Content-Type; /-/search and /-/sql still reach Datasette (D-01 boundary); reflected XSS escaped on /search?q=<script>.
result: [pending]
notes: Production deploy is gated; smoke test happens after deploy-checkpoint. Requires live HTTPS environment + DNS resolution.

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
