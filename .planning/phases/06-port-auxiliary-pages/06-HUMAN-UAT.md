---
status: partial
phase: 06-port-auxiliary-pages
source: [06-VERIFICATION.md]
started: 2026-04-26T02:45:00Z
updated: 2026-04-26T03:30:00Z
---

## Current Test

[awaiting production deploy + smoke]

## Tests

### 1. Visual QA sweep of every aux page in a real browser
expected: Italic-accent H1 with colored `<em>` visible; civic-broadsheet paper/petrol palette; 4-column footer renders; footer links contrast correctly against Datasette's `app.css` cascade; no layout regressions on /developers, /status, /sources, /about, /how-to-use, /search, /sql, /sql/{db}.
result: passed
notes: |
  Walked through every aux page in the local stack (http://localhost) during the close-out session.
  Issues found and resolved as commits inside Phase 6:
    - aux page container max-width / margins missing (commit a72a83b)
    - /status changelog out of order (commit 0c6a98b)
    - /sql landing too sparse for casual researchers (commit 4f5dfd6)
    - /sql/{db} schema reference missing (commit 7d5f9e1)
    - /how-to-use button row inconsistent (commits a7e214f + 17dcba0; root cause: missing .btn-secondary CSS)
    - /how-to-use URL claims didn't match the actual API contract (commit db39492)
    - home page still pointed search at Datasette and didn't link to /sql (commit 2dfae70)
    - changelog rewritten for content focus (commits e6cd559, 67dc556)
    - WR-01 orphan CSS comment text stripped (part of commit 05b97af)
  Browser eyeball confirmed each fix; no remaining layout regressions in local stack.

### 2. Re-baseline API parity reference and re-run scripts/verify_phase_06.sh against running stack
expected: All 11 sections (A–K) of `verify_phase_06.sh` exit OK after re-baselining `.planning/baselines/phase-03-pre/` → `phase-06-pre/` via `scripts/capture_baseline.sh`; `verify_api_parity.sh` exits 0.
result: passed
notes: |
  Captured fresh baseline at .planning/baselines/phase-06-pre/ via
  `ZEEKER_BASELINE_URL=http://localhost ZEEKER_BASELINE_DIR=...phase-06-pre bash scripts/capture_baseline.sh`.
  Repaired three stale verifier issues during close-out (commit 8ed46ef):
    - Hard-pinned phase-03-pre/ baseline in verify_phase_03/04/06 — replaced with self-healing
      cascade (phase-06-pre → ... → phase-03-pre) so future phases stay green.
    - Stale negative-routing assertions written for the Phase-3 placeholder frontend; widened
      to accept Phase-4-6 actually-rendered 200s in addition to the original 404 placeholder shape.
    - SIGPIPE bug under `set -euo pipefail` + `echo $body | grep -q` on Phase-5's ~800KB table
      pages; switched to file-based grep.
  `bash scripts/verify_phase_06.sh` now exits PASS with all 11 sections (A–K) green.

### 3. Production smoke against https://data.zeeker.sg/ aux routes
expected: Each of /developers, /status, /sources, /about, /how-to-use, /llms.txt, /search, /sql, /sql/{db}, /robots.txt returns 200 + civic-broadsheet body + correct Content-Type; /-/search and /-/sql still reach Datasette (D-01 boundary); reflected XSS escaped on /search?q=<script>.
result: pending
notes: |
  Production deploy is gated; smoke test happens after deploy-checkpoint. Requires live
  HTTPS environment + DNS resolution. Local stack smoke check done — every aux route
  serves 200 from the frontend, /-/search reaches Datasette through Caddy, /-/sql 404s
  as expected (Datasette has no top-level /-/sql route — that's correct, not a
  regression), reflected XSS escaped on /search?q=<script>alert(1)</script>.

## Summary

total: 3
passed: 2
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps

### allow_download config gap (surfaced during URL accuracy audit, not a Phase-6 regression)

`/{db}.db` whole-database download returns 403 because metadata.json sets
`allow_download: true` on the `*` wildcard but Datasette doesn't apply that
fallback to the named databases (`sglawwatch`, `zeeker-judgements`, `sg-gov-newsrooms`).
The `/how-to-use` doc was rewritten to drop the `.db` claim until this is
addressed. Fix is a one-line `allow_download: true` per database in
`metadata.json` — out of scope for Phase 6, captured here as a known
config gap to address in a future commit.

### FTS shadow tables missing for judgments + government newsrooms

Discovery: `discover_searchable_tables` only finds 3 FTS-indexed tables on
`sglawwatch` (headlines, about_singapore_law, about_singapore_law_fragments).
The `judgments` (10,508 rows), `judgments_fragments`, and the eight `*_news`
tables in `sg-gov-newsrooms` all have `fts_table: None` in Datasette's
payload. The frontend correctly fans out across whatever Datasette reports
as searchable, so this is upstream data-layer scope (build pipeline needs
`sqlite-utils enable-fts` calls). Not a Phase-6 frontend regression.
