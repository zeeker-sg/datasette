---
phase: 05-port-table-browse-row-view
plan: "03"
subsystem: ui
tags: [fastapi, jinja2, httpx, row-view, templates, tdd, article-layout, judgment-layout]
dependency_graph:
  requires:
    - phase: 05-01
      provides: "fetch_row, fetch_site_metadata, routes_row stub with hidden-table guard, Wave-0 fixtures"
  provides:
    - "Full GET /{db}/{table}/{pk} handler with row_mode dispatch context"
    - "row.html mode-dispatch shell template"
    - "row_article.html — magazine article layout (sketch 003-A)"
    - "row_judgment.html — editorial broadsheet layout (sketch 003-B)"
    - "row_longform.html — reading-only layout (no aside)"
    - "row_tabular.html — default key-value <dl> with <details> expand for long-text"
    - "15 integration tests for GET /{db}/{table}/{pk}"
  affects: [05-04, 05-05, scripts/verify_phase_05.sh]
tech-stack:
  added: []
  patterns:
    - "row_mode dispatch: display.row_mode → partial include; tabular fallback (D-04) when unset"
    - "pk_label truncation: 12-char limit + ellipsis for UUID/hash PKs"
    - "long_text_columns dict precomputed in handler for tabular <details> wrapping"
    - "Jinja autoescape preserved throughout — no |safe on dataset content (T-05-04)"
    - "MockTransport + ASGITransport two-layer test pattern (same as 05-01/05-02)"

key-files:
  created:
    - packages/zeeker-frontend/src/zeeker_frontend/templates/row.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_article.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_judgment.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_longform.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_tabular.html
    - packages/zeeker-frontend/tests/test_routes_row.py
  modified:
    - packages/zeeker-frontend/src/zeeker_frontend/routes_row.py

key-decisions:
  - "row_mode = display.get('row_mode') or 'tabular' (D-04 tabular fallback when no hint set)"
  - "pk_label truncated to 12 chars + ellipsis (matching UI-SPEC breadcrumb spec for UUID/hash PKs)"
  - "long_text_columns precomputed as dict[col, bool] in handler (not in template)"
  - "Jinja autoescape ON; no |safe on any dataset content (T-05-04 mitigation)"
  - "longform partial has class='article read longform-article' but NO .aside sidebar"
  - "judgment partial uses .dateline + .tag-chip (sketch 003-B); tags parsed from JSON-encoded string"

patterns-established:
  - "row_mode dispatch via {% if row_mode == 'article' %} ... {% include %} chain in row.html"
  - "long-text expand uses native <details>/<summary>; threshold is len > 200 chars"
  - "hidden-table guard (prefix + suffix) FIRST in handler before any fetch (T-05-03)"

requirements-completed: [REQ-frontend-route-set, REQ-frontend-data-via-http, REQ-eliminate-template-drift]

duration: 3min
completed: "2026-04-25"
---

# Phase 05 Plan 03: Row View — Full Handler + 4 Layout Partials + Integration Tests Summary

**GET /{db}/{table}/{pk} fully implemented with four editorial row_mode layouts (article, judgment, longform, tabular fallback), row.html dispatch shell, and 15 green integration tests**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-25T07:31:19Z
- **Completed:** 2026-04-25T07:34:38Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- routes_row.py: full handler replacing 05-01 stub — hidden-table guard, fetch_row, site_metadata merge, row_mode dispatch, pk_label truncation, long_text_columns precomputation, Cache-Control header
- row.html + 4 row_mode partials: article (sketch 003-A magazine), judgment (sketch 003-B broadsheet), longform (article without aside), tabular (key-value dl with native <details>)
- 15 integration tests covering all 4 row_modes + cache control, breadcrumb, hidden-table guard, 503, export anchor, rowid-only table

## Task Commits

1. **Task 1: Implement full routes_row.py handler** — `14bb30a` (feat)
2. **Task 2: Author row.html + 4 row-mode partials** — `9f7b3cc` (feat)
3. **Task 3: Author test_routes_row.py** — `a088813` (test)
4. **Plan metadata** — (docs: this SUMMARY commit)

## Files Created/Modified

- `packages/zeeker-frontend/src/zeeker_frontend/routes_row.py` — Full GET /{db}/{table}/{pk} handler (~100 lines); replaces 05-01 stub
- `packages/zeeker-frontend/src/zeeker_frontend/templates/row.html` — Mode-dispatch shell extending base.html; italic-accent H1; no stat band
- `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_article.html` — Magazine article layout: .article.read + .aside (sketch 003-A)
- `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_judgment.html` — Editorial broadsheet: .dateline + .tag-chip + .coda (sketch 003-B)
- `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_longform.html` — Reading-only: .article.read.longform-article; NO .aside
- `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_tabular.html` — Default <dl> fallback; <details> for fields > 200 chars
- `packages/zeeker-frontend/tests/test_routes_row.py` — 15 integration tests; all green

## routes_row.py Final Shape

**Line count:** ~100 lines

**Key control flow:**
1. Hidden-table prefix+suffix guard (FIRST — T-05-03)
2. `fetch_row(client, db, table, pk)` — 503 on `httpx.HTTPError`; 404 on `None` or empty rows
3. `fetch_site_metadata(client)` — 60s TTL cached
4. `row_mode = display.get("row_mode") or "tabular"` — D-04 fallback
5. `pk_label = _truncate_pk(pk)` — 12-char limit + "…" for UUID/hash PKs
6. `long_text_columns` dict precomputed (`len(val) > 200` per column)
7. `TemplateResponse("row.html", context={...})` with Cache-Control header

## row.html Mode-Dispatch Contract

| `display.row_mode` | Partial Included |
|--------------------|-----------------|
| `"article"` | `_partials/row_article.html` |
| `"judgment"` | `_partials/row_judgment.html` |
| `"longform"` | `_partials/row_longform.html` |
| `None` / `"tabular"` / any other | `_partials/row_tabular.html` |

## 4 Row Partials Inventory

| Partial | Key CSS Classes | Sidebar? |
|---------|----------------|----------|
| row_article.html | `.article.read`, `.aside` | Yes — aside with record DL + export |
| row_judgment.html | `.article.judgment`, `.dateline`, `.tag-chip`, `.coda` | No |
| row_longform.html | `.article.read.longform-article` | No |
| row_tabular.html | `.article.row-tabular`, `.aside` | Yes — aside with export only |

## Test File: 15 Tests

| Test Name | Coverage |
|-----------|---------|
| test_row_returns_200_article_mode | Article mode 200; .article + .aside present |
| test_row_article_mode_does_not_render_dateline | .dateline absent in article mode |
| test_row_judgment_mode_renders_dateline | .dateline + tag-chip in judgment mode |
| test_row_longform_mode_no_aside | .article present, .aside absent in longform |
| test_row_tabular_fallback_renders_dl | <dl> in tabular fallback |
| test_row_tabular_long_text_uses_details | <details> + "Show full content" for > 200 chars |
| test_row_cache_control_header | max-age=60 + stale-while-revalidate=300 |
| test_row_italic_accent_h1 | <h1>...<em>...</em>...</h1> regex match |
| test_row_renders_three_segment_breadcrumb | db/table/pk 3-segment + 12-char PK truncation |
| test_row_zeeker_prefix_returns_404 | Hidden table guard (_zeeker_*) |
| test_row_fts_suffix_returns_404 | Hidden table guard (*_fts) |
| test_unknown_row_returns_404 | Unknown table/pk → 404 |
| test_row_returns_503_on_upstream_error | httpx.ConnectError → 503 |
| test_row_export_json_anchor_present | /{db}/{table}/{pk}.json anchor |
| test_row_rowid_only_table_renders_200 | primary_keys=[] Pitfall 4 safety |

## pk_label Truncation Behavior

`_truncate_pk(pk, n=12)`:
- If `len(pk) <= 12`: return pk unchanged
- If `len(pk) > 12`: return `pk[:12] + "…"` (Unicode ellipsis U+2026)
- UUID example: `"fdd3ea972982da1e8326e4233586bd8e"` → `"fdd3ea972982…"`

## Long-Text Details Threshold

- Threshold: `len(value) > 200` characters
- Applied only in `row_tabular.html` (tabular fallback mode)
- Implementation: `long_text_columns` dict precomputed in handler; template uses `long_text_columns.get(col)` per column
- Output: `<details><summary>Show full content</summary>` wrapping full value + preview `val[:200]…` visible by default

## Threat Mitigations Applied

| Threat ID | Status |
|-----------|--------|
| T-05-01 (path traversal) | fetch_row None → 404; httpx base_url pinned |
| T-05-03 (hidden-table row access) | prefix+suffix guard FIRST in handler |
| T-05-04 (XSS via row content) | Jinja autoescape ON; no \|safe on dataset content |
| T-05-05 (open-redirect via source_url) | rendered as `<a href="..." rel="noopener noreferrer">` with autoescape |
| T-05-06 (cache poisoning) | accepted — HTML-only response |

## Deviations from Plan

None — plan executed exactly as written.

The plan specified using `display_columns.get("kicker")` calls in row.html. Since `display_columns` is a plain dict passed from the handler (not a Jinja `Undefined`), `.get()` is safe and works correctly.

## Issues Encountered

None.

## Next Phase Readiness

- `GET /{db}/{table}/{pk}` fully operational; all 4 row_modes render correctly
- 15 tests green; 98 total suite green (0 regressions)
- CSS for `.article`, `.aside`, `.dateline`, `.tag-chip`, `.coda`, `.article-grid` classes must be added to `zeeker.css` (Phase 05 Plan 04 or 05 CSS harvest)
- `_partials/` directory now created; Plan 05-02 table partials will coexist without conflict

---
*Phase: 05-port-table-browse-row-view*
*Completed: 2026-04-25*

## Self-Check: PASSED

All files verified present. All task commits verified in git log.

| Item | Status |
|------|--------|
| routes_row.py | FOUND |
| templates/row.html | FOUND |
| _partials/row_article.html | FOUND |
| _partials/row_judgment.html | FOUND |
| _partials/row_longform.html | FOUND |
| _partials/row_tabular.html | FOUND |
| tests/test_routes_row.py | FOUND |
| 05-03-SUMMARY.md | FOUND |
| Commit 14bb30a (Task 1) | FOUND |
| Commit 9f7b3cc (Task 2) | FOUND |
| Commit a088813 (Task 3) | FOUND |
