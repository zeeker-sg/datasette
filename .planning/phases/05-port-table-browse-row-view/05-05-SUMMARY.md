---
phase: 05-port-table-browse-row-view
plan: "05"
subsystem: metadata + verification + deploy-ops
tags: [metadata, display-hints, verifier, deploy-notes, e2e]
dependency_graph:
  requires: [05-01, 05-02, 05-03, 05-04]
  provides: [display-hint-routing, phase-5-verifier, deploy-decision-capture]
  affects: [metadata.json, scripts/, .planning/phases/05-port-table-browse-row-view/]
tech_stack:
  added: []
  patterns:
    - display.* metadata hint blocks for editorial mode dispatch
    - bash verifier section A-O chain (delegation + aggregated FAILED flag)
    - four-category ship/no-ship triage (A/B/C/D)
key_files:
  created:
    - scripts/verify_phase_05.sh
    - .planning/phases/05-port-table-browse-row-view/05-DEPLOY-NOTES.md
  modified:
    - metadata.json
decisions:
  - "display.* blocks live in metadata.json alongside title/description/columns — no separate config file"
  - "judiciary_news kicker=content_type (not category); all other *_news tables kicker=category"
  - "sglawwatch.headlines source_url maps to source_link column (not source_url) per baseline"
  - "/-/search assertion strengthened: positive Datasette marker required on 200; negative frontend CSS check alone was spuriously passing"
  - "Phase-5 deploy remains deferred (operator decision at Task 4 checkpoint)"
metrics:
  duration_seconds: 233
  completed_date: "2026-04-25"
  tasks_completed: 3
  tasks_total: 4
  files_changed: 3
---

# Phase 05 Plan 05: Metadata Display Hints + Phase-5 Verifier + Deploy Notes Summary

**One-liner:** 11 display-hint blocks added to metadata.json to wire editorial mode dispatch; `verify_phase_05.sh` (15 sections A-O) authors the full-stack gate; deploy decision deferred to human checkpoint.

## What Was Built

### Task 1 — metadata.json display.* blocks (commit `4f79811`)

Added `display` keys to 11 tables across 3 databases:

| Database | Table | table_mode | row_mode |
|----------|-------|-----------|----------|
| sglawwatch | headlines | feed | article |
| sglawwatch | about_singapore_law | longform-list | longform |
| Zeeker-Judgements | judgments | tabular | judgment |
| sg-gov-newsrooms | mlaw_news | feed | article |
| sg-gov-newsrooms | judiciary_news | feed | article |
| sg-gov-newsrooms | acra_news | feed | article |
| sg-gov-newsrooms | agc_news | feed | article |
| sg-gov-newsrooms | ccs_news | feed | article |
| sg-gov-newsrooms | ipos_news | feed | article |
| sg-gov-newsrooms | mom_news | feed | article |
| sg-gov-newsrooms | pdpc_news | feed | article |

Key column mappings preserved per baselines:
- `sglawwatch.headlines.source_url` → `source_link` (NOT `source_url` — sglawwatch uses a different column name)
- `judiciary_news.kicker` → `content_type` (not `category` — judiciary uses content_type)
- `Zeeker-Judgements.judgments` adds `citation` slot (unique to judgment mode)

New database blocks added: `databases.sglawwatch`, `databases.Zeeker-Judgements`.
New table entries added to `databases.sg-gov-newsrooms.tables`: `acra_news`, `agc_news`, `ccs_news`, `ipos_news`, `mom_news`, `pdpc_news`.
Wildcard `databases.*` hidden-table entries (`_zeeker_schemas`, `_zeeker_updates`) preserved.
All top-level keys preserved (`title`, `license`, `menu_links`, `plugins`, `extra_css_urls`, `extra_js_urls`).

### Task 2 — scripts/verify_phase_05.sh (commit `591f550`)

New executable bash verifier (`chmod +x`; `set -euo pipefail`; `BASE_URL` env var with `http://localhost` default).

15 sections covering the full verifier outline from RESEARCH:

| Section | What it checks |
|---------|---------------|
| A | Delegates to verify_phase_04.sh (Phase-3+4 invariants) |
| B | Feed mode: va-item, frontend CSS, no zeeker-base.css leak, italic-accent H1, Cache-Control |
| C | Tabular fallback: data-table present, va-item absent |
| D | Facet sidebar: class="facets", facet-block |
| E | Applied-facet chip: filter-chip, value text present |
| F | Pagination: class="pagination", Next link relative path, no hostname leak, Show: label |
| G | FTS: filter-chip renders on search |
| H | Sort: 200 status on ?_sort=date |
| I | Export anchors direct (.csv/.json hrefs); Caddy suffix-route text/csv confirmed |
| J | Row article mode: .article, .aside, italic-accent H1 (PK pulled live from .json endpoint) |
| K | Row tabular fallback: dl element (dynamically finds unhinted table) |
| L | Hidden-table 404: _zeeker_schemas, _zeeker_updates, headlines_fts, headlines_fts_data (table + row routes) |
| M | Phase-6 boundary: /developers/status/sources/about/how-to-use/llms.txt → 404; /-/sql /-/versions.json → 200; /-/search strengthened (positive Datasette marker on 200) |
| N | Error paths: unknown table 404, unknown row 404, FTS no-results message, nested-path 404 |
| O | Delegates to verify_api_parity.sh against phase-03-pre baselines |

Deviation from plan's verification pattern for /-/search: the plan described a negative-only check (no zeeker.css). The implemented check is strengthened — on 200 it requires the positive `Datasette` marker in the body. This closes a gap where any empty 200 body would pass spuriously.

### Task 3 — 05-DEPLOY-NOTES.md (commit `962f801`)

Operator-facing deploy decision document capturing:
- Phase-4 deferral carry-forward rationale
- Three deploy options (ship now / defer / partial — not recommended)
- Pre-checkpoint checklist: pytest + docker healthcheck + verifier + 6-mode visual sweep
- Four-category triage labels (A/B/C/D) inherited from Phase-2/3/4
- "Ship checkpoint outcome" table ready for operator to fill in after Task 4

### Task 4 — Human checkpoint (AWAITING)

The plan ends in a `checkpoint:human-verify` gate. The operator must:
1. Run `cd packages/zeeker-frontend && uv run pytest -q`
2. Run `docker compose up -d --build`
3. Run `bash scripts/verify_phase_05.sh` (exit 0 required)
4. Visual sweep of 6 layout modes at `http://localhost`
5. Triage any failures (A/B/C/D)
6. Decide ship-or-no-ship (options 1/2/3 in `05-DEPLOY-NOTES.md`)
7. Fill in the outcome table in `05-DEPLOY-NOTES.md`
8. Update STATE.md + ROADMAP.md atomically

## Deviations from Plan

### Auto-enhanced: /-/search assertion (Rule 2 — missing critical verification)

**Found during:** Task 2
**Issue:** The plan's verifier outline described only a negative check for /-/search (ensure `/static/css/zeeker.css` absent). Any 200 response with no frontend CSS — including empty bodies and minimal datasette 4xx HTML — would pass spuriously.
**Fix:** Added positive `Datasette` string marker requirement on 200 responses. On 404, the check still accepts. This closes T-05-04 (frontend HTML not reached by datasette routes).
**Files modified:** `scripts/verify_phase_05.sh`
**Commit:** `591f550`

## Known Stubs

None — all display.* blocks reference real column names confirmed against phase-03-pre baselines. The verifier is a static artifact; it exercises the running stack at operator invocation time.

## Threat Surface Scan

No new network endpoints or auth paths introduced by this plan. `metadata.json` is consumed by the datasette container at startup (read-only from the frontend's perspective). The verifier is a local operator tool. No new threat flags.

## Self-Check

Files created/modified:

- FOUND: metadata.json (modified — 11 display.* blocks added)
- FOUND: scripts/verify_phase_05.sh (created — 339 lines, executable)
- FOUND: .planning/phases/05-port-table-browse-row-view/05-DEPLOY-NOTES.md (created)

Commits:

- FOUND: 4f79811 (feat(05-05): add 11 display.* hint blocks to metadata.json)
- FOUND: 591f550 (feat(05-05): author scripts/verify_phase_05.sh end-to-end verifier)
- FOUND: 962f801 (docs(05-05): author 05-DEPLOY-NOTES.md deploy decision capture)

## Self-Check: PASSED
