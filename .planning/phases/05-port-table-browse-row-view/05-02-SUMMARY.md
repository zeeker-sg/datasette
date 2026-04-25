---
phase: 05-port-table-browse-row-view
plan: "02"
subsystem: zeeker-frontend
tags: [table-browse, jinja-templates, routing, tdd, facets, pagination, feed-mode]
dependency_graph:
  requires: [05-01]
  provides: [routes_table_full_handler, table_html_mode_dispatch, table_partials_6, test_routes_table_18]
  affects: [05-03, 05-04, 05-05]
tech_stack:
  added: []
  patterns:
    - "mode-dispatch Jinja include pattern (feed/longform-list/tabular)"
    - "next_url Pitfall-2 rewrite via urlparse"
    - "display.columns slot-driven partials"
    - "MockTransport + ASGITransport integration test pyramid"
key_files:
  created:
    - packages/zeeker-frontend/src/zeeker_frontend/routes_table.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/table.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_feed.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_tabular.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_longform_list.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/facet_sidebar.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/applied_facets.html
    - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/pagination.html
    - packages/zeeker-frontend/tests/test_routes_table.py
  modified: []
decisions:
  - "export_url() helper used for direct Caddy suffix routing — never proxied through FastAPI (D-05)"
  - "display_columns dict passed from handler to template — slot lookups in partials are data-driven, not per-table overrides (D-01)"
  - "test_table_renders_breadcrumb asserts class='db-crumb' confirmed by grep of base.html"
  - "pagination.html always rendered when rows present — no-op when next_url is None (span.disabled)"
metrics:
  duration: "4 minutes"
  completed: "2026-04-25T07:35:00Z"
  tasks_completed: 3
  files_changed: 9
---

# Phase 05 Plan 02: GET /{db}/{table} handler + templates + tests Summary

Full implementation of the table browse route: routes_table.py handler (~130 lines), table.html mode-dispatch shell (~127 lines), 6 partials covering feed/tabular/longform-list modes + facet sidebar + applied chips + pagination, and 18 integration tests via ASGITransport + MockTransport.

## What Was Built

### Task 1 — routes_table.py full handler (commit f829688)

**`routes_table.py`** — 130 lines. Complete replacement of the 05-01 stub.

Key control flow:
1. **Hidden-table guard** (T-05-03) as the FIRST conditional — prefix `_zeeker` + suffix `_fts*` → 404
2. `await fetch_table(client, db, table, dict(request.query_params))` — allowlist in client, not handler
3. `httpx.HTTPError` → `HTTPException(503)` / `payload is None` → `HTTPException(404)`
4. `await fetch_site_metadata(client)` (cached) → deep-merge `databases.{db}.tables.{table}` for `display.*`
5. `table_mode = display.get("table_mode") or "tabular"` (D-04 fallback)
6. **Pitfall 2 next_url rewrite**: `urlparse(payload["next_url"])` → rebuild as `f"/{db}/{table}?{parsed.query}"`
7. Sort state from `_sort` / `_sort_desc` query params → `current_sort_dir`, `current_sort_col`
8. `applied_filters` = non-underscore query params → drives `.filter-chip` partials
9. `active_search` = `_search` query param → FTS chip + empty-state copy
10. `TemplateResponse(name="table.html", context={...})` + `Cache-Control: public, max-age=60, stale-while-revalidate=300`

Context keys passed to template: `database, table, rows, columns, primary_keys, facet_results, suggested_facets, filtered_table_rows_count, next_url, request_qs, table_mode, row_mode, display, display_columns, table_meta, metadata, breadcrumbs, breadcrumb_table, current_year, current_sort_col, current_sort_dir, applied_filters, active_search, human_description_en, is_view`

---

### Task 2 — table.html + 6 partials (commit 717ea59)

**`templates/table.html`** — 127 lines. Extends `base.html`.

Mode-dispatch contract:

| `display.table_mode` | Partial included |
|---------------------|-----------------|
| `"feed"` | `_partials/table_feed.html` |
| `"longform-list"` | `_partials/table_longform_list.html` |
| anything else (or unset) | `_partials/table_tabular.html` (D-04 default) |

**6 Partials — CSS class inventory:**

| Partial | CSS Classes | Sketch Reference |
|---------|-------------|-----------------|
| `table_feed.html` | `.va-feed`, `.va-item`, `.va-item-head`, `.va-item-title`, `.va-item-excerpt`, `.va-item-foot`, `.kicker`, `.va-date`, `.byline`, `.source-host` | sketch 004-A |
| `table_tabular.html` | `.data-table`, `.pk`, `.sorted` | sketch 002-B |
| `table_longform_list.html` | `.va-feed.longform-list`, `.va-item.longform`, `.va-item-excerpt.longform` | sketch 002-B variant |
| `facet_sidebar.html` | `.facet-block`, `.facet-block-title`, `.facet-list`, `.facet-item`, `.facet-item.active`, `.facet-label`, `.count` | directory-and-feed-lists.md |
| `applied_facets.html` | `.filter-chips`, `.filter-chip`, `.filter-chip-search`, `.x` | UI-SPEC §Applied-facet chips |
| `pagination.html` | `.pagination`, `.pagination-nav`, `.pagination-next`, `.pagination-next.disabled`, `.pagination-size`, `.pagination-size-label`, `.pagination-size-current` | UI-SPEC §Pagination |

**Slot mapping** in feed/longform partials is driven by `display_columns` dict (handler-pre-computed from `display.columns`): `kicker`, `title`, `byline`, `body`, `date`, `source_url`.

**Security**: No `|safe` filter on any dataset-sourced content. `striptags|truncate` applied to excerpt body text (T-05-04).

**Export anchors** use `export_url(database, table, 'csv', request_qs)` → `/{db}/{table}.csv?{qs}` direct Caddy suffix routing (D-05).

---

### Task 3 — test_routes_table.py (commit 79e5eff)

**18 tests, all green.** Test-local `METADATA_WITH_DISPLAY` fixture with `display.table_mode: "feed"` for `headlines` and no hint for `about_singapore_law` (tabular fallback).

| Test | Must-Have Covered |
|------|------------------|
| `test_table_returns_200_feed_mode` | 200 for visible table; va-item + va-feed in body; correct CSS |
| `test_table_feed_mode_does_not_render_data_table` | Mode dispatch correctness |
| `test_table_tabular_fallback` | D-04 tabular fallback; no va-item |
| `test_facet_sidebar_renders` | `.facets` + `.facet-block` + CATEGORY uppercase |
| `test_applied_facet_chip_renders` | `.filter-chip` for column filter in querystring |
| `test_applied_search_chip_renders` | FTS chip when `_search=` present |
| `test_pagination_next_link_when_next_url` | `.pagination` + "Next →" + no internal hostname (Pitfall 2) |
| `test_export_anchors_are_direct` | CSV/JSON anchors match `/{db}/{table}.csv?...` regex; no `/export?` |
| `test_table_cache_control_header` | `max-age=60` + `stale-while-revalidate=300` |
| `test_table_italic_accent_h1` | `<h1>...<em>...</em>...</h1>` regex |
| `test_zeeker_prefix_table_returns_404` | T-05-03 hidden-table guard (prefix) |
| `test_fts_suffix_table_returns_404` | T-05-03 hidden-table guard (suffix `_fts`) |
| `test_fts_data_suffix_returns_404` | T-05-03 hidden-table guard (suffix `_fts_data`) |
| `test_unknown_table_returns_404` | datasette 404 → handler 404 |
| `test_search_no_results_message` | "No results for" empty-state copy |
| `test_rowid_pk_fallback_renders_row_link` | Pitfall 4 — primary_keys=[] → 200 |
| `test_table_returns_503_on_upstream_error` | httpx.ConnectError → 503 |
| `test_table_renders_breadcrumb` | `class="db-crumb"` (verified from base.html grep) + db + table labels |

---

## Test Results

Full suite after this plan: **101 tests, 0 failures**

Breakdown (delta from 05-01's 83 tests):
- test_routes_table.py: **18 new tests** (this plan)

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Threat Mitigations Applied

| Threat ID | Status |
|-----------|--------|
| T-05-01 (path traversal) | fetch_table returns None on datasette 404 → HTTPException 404 |
| T-05-02 (querystring smuggling) | allowlist enforced inside fetch_table (05-01 carry-forward); handler does not re-filter |
| T-05-03 (hidden table access) | prefix+suffix guard preserved as first conditional; 3 test cases |
| T-05-04 (XSS) | Jinja autoescape ON; no `|safe` on dataset content; striptags on excerpts |
| T-05-05 (open redirect) | next_url rewritten via urlparse to relative `/{db}/{table}?{qs}`; tested by pagination assertion |
| T-05-06 (cache poisoning) | accepted; HTML-only, no Accept-based negotiation |

---

## Self-Check

### Files exist:
- [x] packages/zeeker-frontend/src/zeeker_frontend/routes_table.py
- [x] packages/zeeker-frontend/src/zeeker_frontend/templates/table.html
- [x] packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_feed.html
- [x] packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_tabular.html
- [x] packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_longform_list.html
- [x] packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/facet_sidebar.html
- [x] packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/applied_facets.html
- [x] packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/pagination.html
- [x] packages/zeeker-frontend/tests/test_routes_table.py

### Commits exist on master:
- [x] f829688 — Task 1 (routes_table.py full handler)
- [x] 717ea59 — Task 2 (table.html + 6 partials)
- [x] 79e5eff — Task 3 (test_routes_table.py)

## Self-Check: PASSED
