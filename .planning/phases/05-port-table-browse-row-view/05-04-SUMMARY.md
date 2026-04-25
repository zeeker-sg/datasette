---
phase: 05-port-table-browse-row-view
plan: "04"
subsystem: zeeker-frontend/css
tags: [css, table-browse, row-view, phase-05, civic-broadsheet]
dependency_graph:
  requires: [05-01]
  provides: [05-02, 05-03]
  affects: [packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css]
tech_stack:
  added: []
  patterns: [CSS-custom-properties, Fraunces-drop-cap, sticky-sidebar, css-grid-two-column]
key_files:
  created: []
  modified:
    - packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css
decisions:
  - Pre-existing Phase 4 tokens (--transition-fast, --z-sticky) are out-of-scope; validation scoped to new section only
  - Comment referencing "zeeker-base.css" in feed cards sub-section reworded to remove the deprecated path string
metrics:
  duration: "~8 minutes"
  completed: "2026-04-25"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 05 Plan 04: CSS — Table Browse + Row View Summary

Appended the locked civic-broadsheet CSS section (644 lines) for Phase 5 surfaces to `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css`, covering feed cards, facet sidebar, filter chips, pagination, tabular data-table, article reading layout, judgment broadsheet, row tabular fallback, and empty state — all sourced from sketch-findings-zeeker-datasette (LOCKED).

## What Was Built

A single CSS file modification: a new section delimited `/* =========== TABLE BROWSE + ROW VIEW — phase 05 ============ */` inserted immediately before the `HARVESTED FROM M1 zeeker-base.css LINES 4097..4116` tail block. File grew from 1102 lines to 1746 lines.

### Section Structure

| Sub-section | Line range (approx) | Sketch source |
|---|---|---|
| Two-column feed layout + toolbar export | 1074–1120 | sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md |
| Filter chips | 1121–1155 | sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md |
| Facet sidebar (.facets / .facet-block / .facet-item) | 1156–1220 | sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md |
| Pagination strip | 1221–1268 | sketch-findings-zeeker-datasette/references/theme-system.md |
| Tabular data table (.data-table) | 1269–1290 | sketch-findings-zeeker-datasette/references/database-table-grid.md (sketch 002-B) |
| Feed cards (.va-*) | 1292–1390 | sketch-findings-zeeker-datasette/references/table-as-news-archive.md (sketch 004-A) |
| Article reading layout (.article / .article-body / drop cap / .aside / .coda) | 1392–1555 | sketch-findings-zeeker-datasette/references/row-reading-layouts.md (sketch 003-A) |
| Judgment broadsheet (.dateline / .judgment-meta / .tag-chip) | 1556–1660 | sketch-findings-zeeker-datasette/references/row-reading-layouts.md (sketch 003-B) |
| Row tabular fallback (.row-tabular / .row-dl) | 1662–1705 | sketch-findings-zeeker-datasette/references/database-table-grid.md |
| Empty state | 1706–1715 | — |

### Class-Name Inventory (Plans 05-02 + 05-03 match)

All 42 required class names have at least one rule definition:

`.feed-layout`, `.va-feed`, `.va-item`, `.va-item-head`, `.va-item-title`, `.va-item-excerpt`, `.va-item-foot`, `.source-host`, `.va-empty`, `.va-citation`, `.va-item-wrap`, `.facets`, `.facet-block`, `.facet-list`, `.facet-item`, `.facet-item.active`, `.facet-block-title`, `.filter-chip`, `.filter-chip .x`, `.filter-chips`, `.filter-chip-search`, `.pagination`, `.pagination-nav`, `.pagination-next`, `.pagination-size`, `.pagination-size-current`, `.data-table`, `.data-table thead th`, `.data-table tbody tr`, `.data-table th.sorted`, `.article`, `.read`, `.article-body`, `.article-grid`, `.aside`, `.aside-block`, `.dateline`, `.dateline-agency`, `.dateline-date`, `.judgment-meta`, `.tag-chip`, `.tag-chips`, `.coda`, `.coda-label`, `.coda-fingerprint`, `.back-link`, `.empty-state`, `.row-tabular`, `.row-tabular-grid`, `.row-dl`, `.row-dd-long`, `.row-dd-preview`, `.longform-article`, `.judgment-body`, `.row-header`, `.db-toolbar-export`, `.row-section`

### Validation Results

- Section delimiter present exactly once: OK
- Brace balance full file: 300 open / 300 close: OK
- Total lines: 1746 (was 1102; +644): OK (> 1400 threshold)
- FOOTER LINK OVERRIDE preserved at tail: OK
- ACCESSIBILITY UTILITIES preserved at tail: OK
- visually-hidden on last line: OK
- No unknown CSS tokens in new section: OK
- No deprecated M1 paths (`zeeker-base.css`) in new section: OK
- `footer a:link` rule intact: OK (1 rule + 1 comment reference)

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `070297f` | feat(05-04): append phase-05 TABLE BROWSE + ROW VIEW CSS section to zeeker.css |

## Deviations from Plan

**1. [Rule 2 - Auto-fix] Removed deprecated M1 path reference from feed cards comment**
- **Found during:** Task 1 verification
- **Issue:** The feed cards sub-section comment originally read "direct copy from M1 zeeker-base.css 3864..3984" — acceptance criteria prohibits `zeeker-base.css` strings in the new section
- **Fix:** Reworded to "harvested from M1 lines 3864..3984" (no file path)
- **Files modified:** packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css

**2. [Observation] Pre-existing Phase 4 unknown tokens excluded from scope**
- **Found during:** Task 1 validation
- **Issue:** `--transition-fast` (line 305) and `--z-sticky` (line 598) are Phase 4 pre-existing tokens that don't match the known prefix list. They were in the file before this plan.
- **Resolution:** Validation scoped to the new phase-05 section only (lines 1074–1716). Pre-existing tokens out-of-scope per deviation rule (scope boundary: only issues directly caused by current task's changes).

## Known Stubs

None. This plan is CSS-only; it introduces no data-wiring or template stubs.

## Threat Flags

None. The Phase 05 CSS section introduces no `content` properties keyed on dataset values, no `url()` references, and no auth paths. All backgrounds use CSS custom property tokens. Static asset served by FastAPI StaticFiles.

## Self-Check

- [x] Modified file exists: `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` — FOUND
- [x] Commit `070297f` exists — FOUND
- [x] Section delimiter present: `grep -c '/* =========== TABLE BROWSE + ROW VIEW — phase 05 ============ */'` returns 1
- [x] All 42 required class names present

## Self-Check: PASSED
