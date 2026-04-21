---
phase: 04-port-home-database-pages
plan: 05
status: complete
completed: 2026-04-22
tasks_completed: 1/2
deploy_status: deferred
---

## 04-05: Ship frontend HTML routes to production — DEFERRED

Prod-deploy artifacts authored and committed; the actual production push to
`https://data.zeeker.sg` is **deferred** by operator decision. The project is
still under active development, and a staging / soft-launch boundary does not
exist yet — shipping the M2 split to live public traffic would happen without
a rollback audience or canary. The Phase-5 table/row routes are not built yet;
shipping home + database alone produces a half-working UX (everything below
`/{db}/` 404s).

Phase 4 is therefore closed on the **pre-deploy gate green** against the local
dev stack.

## What landed

- `scripts/verify_phase_04.sh` — executable, delegates to `verify_phase_03.sh`
  for topology/routing invariants, adds Phase-4 structural checks for home +
  database + static assets + Phase-5 boundary + API byte-parity
- `docker-compose.prod.yml` — minimal overlay, caddy mounts `Caddyfile.prod`
- `Caddyfile.prod` — auto-HTTPS for `data.zeeker.sg`, Phase-3 suffix routing
  preserved byte-for-byte
- `.planning/phases/04-port-home-database-pages/04-05-DEPLOY.md` — deploy
  runbook + three-layer rollback + four-category (A/B/C/D) triage template

These are inert until someone chooses to run the deploy recipe. When that
day comes, the operator reads `04-05-DEPLOY.md` and executes.

## Pre-deploy gate results (2026-04-22, dev stack)

Phase-4 structural checks (sections B–F of `verify_phase_04.sh`) all green:

- `/` renders: `.db-statband`, `.cards`, italic-accent H1, `/static/css/zeeker.css`, no `zeeker-base.css` leak, `Cache-Control: public, max-age=60, stale-while-revalidate=300`
- `/sglawwatch` renders: `.db-header`, `.list`, `headlines` row, `/static/css/zeeker.css`, no `_zeeker_*` leak, no `headlines_fts` leak, italic-accent H1
- `/nonexistent-database-phase-4-check` → 404
- `/static/css/zeeker.css` → 200 text/css
- `/static/fonts/{inter,jetbrains-mono,fraunces}-latin.woff2` → 200
- `/sglawwatch/headlines` → 404 (Phase-5 boundary intact)

Pytest: 41 passed, 0 failed.

API byte-parity against `.planning/baselines/phase-03-pre/` shows content
drift only (newer headlines row, one extra newsroom entry, edited
`metadata.json` title, newer ingestion timestamps) — no routing regressions.
That baseline is a 2026-04-20 snapshot; the data has advanced. Phase-4 code
did not alter datasette's API responses. A `phase-04-pre` baseline can be
captured fresh when deploy is un-deferred.

## Gaps closed during this checkpoint

Three issues surfaced when the operator ran `verify_phase_04.sh` live:

1. **`_zeeker_*` table leak on `/{db}`** — real regression vs M1. Datasette's
   `hidden: true` covers FTS internals but not `_zeeker_*` platform tables;
   M1 hid those via per-database `metadata.json` entries, which not every
   overlay carries. Added a prefix check alongside the hidden-flag filter in
   `routes_database.py`, matching the pattern M1's `sources_page.py` and
   `developers_page.py` already use. Fixture regression added: flipped
   `_zeeker_updates` to `hidden: false` so the test exercises the prefix
   path instead of the flag path. Live stack re-verified clean after
   frontend container rebuild. Commit `f5fb2f9`.

2. **Verifier italic-H1 regex never matched** — H1 renders across multiple
   lines; `grep '<h1>[^<]*<em'` is single-line. Fixed with `tr '\n' ' '`
   before grep. Templates were always correct; regex was the bug.

3. **Verifier Cache-Control check used HEAD** — uvicorn returns 405 on HEAD
   for `@router.get("/")`, so the header never arrived. Switched to
   `curl -D - -o /dev/null` (GET with headers). Route handler already sets
   the header correctly on GET.

## Rollback

Not applicable — no production deploy ran. If the in-repo prod artifacts
themselves need revert, they are isolated to these commits:

- `cb6cecf` (merged via `4de63a1`) — initial artifacts
- `f5fb2f9` — pre-deploy-gate fixes

## When deploy is un-deferred

1. Re-verify the pre-deploy gate: `cd packages/zeeker-frontend && uv run pytest -q` + `docker compose up -d --build && sleep 30 && bash scripts/verify_phase_04.sh`
2. Capture `.planning/baselines/phase-04-pre/` from the current dev stack (updates the baseline to match live data)
3. Execute the deploy recipe in `04-05-DEPLOY.md`
4. Smoke with `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh`
5. Triage per the A/B/C/D table in the runbook

## Commits

- `cb6cecf` — feat(04-05): author verify_phase_04.sh + Caddyfile.prod + docker-compose.prod.yml + DEPLOY.md (via merge `4de63a1`)
- `f5fb2f9` — fix(04): prefix-filter _zeeker_ tables + fix verifier H1 regex + GET-based Cache-Control check
