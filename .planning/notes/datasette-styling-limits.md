---
title: Datasette styling limits & escape hatches
date: 2026-04-19
context: Explored during UI polish work for the v2 generic base shell. Research verified against Datasette 0.65.1 source locally.
---

# Datasette styling limits & escape hatches

Customizing Datasette's UI runs into four distinct layers of constraint. Each has a documented workaround.

## 1. Templates — overridable, with quirks

**Override point:** `--template-dir` (already used: `templates/`)

You can replace any built-in template by dropping a file with the same name (`index.html`, `database.html`, `table.html`, `row.html`, `base.html`, `_footer.html`, etc.). The template runs inside Datasette's Jinja2 environment with its full context.

**Quirk:** when the resolved per-database metadata block has no `tables` key, `metadata.tables[...]` under StrictUndefined raises. Always guard with `metadata.get('tables', {}).get(name)` or `{% set table_meta = ... %}` at the top of the loop. (Hit this today in `templates/database.html` — 500 on `/fixtures`.)

## 2. Default `app.css` — always loads, wins specificity

Datasette's `/-/static/app.css` is unconditionally included. It ships rules like `footer a:link { color: rgba(255,255,244,0.8) }` and `a:link { color: #276890 }` that win specificity wars against `.footer-col a` (same spec, app.css usually later).

**Workarounds:**
- Match or beat the selector: use `footer a:link, footer a:visited, footer a:active { ... }` to match spec and load later via `extra_css_urls`.
- Do **not** use `!important` — it cascades and makes later overrides worse.
- Expect this to bite any selector that hits a bare element + pseudo-class (`a:link`, `table th`, `input[type=search]`).

## 3. Built-in table HTML — `_table-{db}-{table}.html` is the seam

Datasette's `table.html` renders the row-list via `{% include custom_table_templates %}`. The lookup (`datasette/views/table.py:771-775`) is:

```
_table-{database}-{table}.html   # most specific
_table-table-{database}-{table}.html
_table.html                       # fallback
```

**Key insight:** dropping `templates/_table-{database}-{table}.html` into `--template-dir` replaces **only the `<table class="rows-and-columns">` block** for that one table. Everything else — filter form, facets sidebar, FTS search box, sort links, pagination, CSV/JSON export links, the full advanced export pane, table-definition SQL pre, table-actions menu — stays rendered by the default `table.html`.

### Context available inside `_table-*.html`

Inherited from `table.html`'s Jinja scope (verified in `datasette/views/table.py:748-815`):

- `display_rows`, `display_columns`, `rows` (raw)
- `filtered_table_rows_count`, `next_url`
- `filters`, `facet_results`, `sort`, `sort_desc`, `is_sortable`
- `primary_keys`, `metadata`
- `url_csv`, `renderers`, `request`
- Helpers: `urls.row(db, table, pk)`, `path_with_replaced_args(request, {...})`, `append_querystring`, `fix_path`

Inside the row loop, prefer `row.display("col_name")` over `row["col_name"]` — it returns the HTML-rendered version, so `datasette-render-markdown` / `datasette-render-html` / foreign-key labels continue to work.

### What `render_cell` is not for

`render_cell(row, value, column, ...)` only rewrites the value of one cell. It can't restructure rows into cards and leaves the `<table>` wrapper intact. Use it for per-column markdown/HTML rendering, never for layout. No `render_row_html` hook exists in 0.65.x ([issue #1518](https://github.com/simonw/datasette/issues/1518)).

### Full `table.html` replacement: avoid

Possible via `table-{db}-{table}.html` or project-wide `table.html`, but you lose: filter form, facets sidebar, `supports_search` FTS search, sort headers, pagination, `.export-links`, `<div id="export" class="advanced-export">` (JSON shape + CSV options), `datasette_allow_facet` JS global, `table.js`. Not worth it for layout tweaks.

## 4. URL structure — fixed

`/-/static/*`, `/-/search`, `/db/table.json`, `/db/table/pk`, `/db?sql=...` — all hardcoded in Datasette's routing. You cannot rename them. Can add routes via `register_routes` plugin hook, not rename existing ones.

## Implications for our sketches

| Sketch | Layer | Approach | Risk |
|--------|-------|----------|------|
| 001-D Home | Template | `templates/index.html` (done) | Low |
| 002-B Database | Template | `templates/database.html` (done, bug fixed today) | Low |
| 004-A Table feed | Table partial | `templates/_table-{db}-{table}.html` per news table | Low-medium |
| 003 Row (parked) | Template | `templates/row.html` when resumed | Low |

## References

- [Datasette custom_templates docs](https://docs.datasette.io/en/stable/custom_templates.html)
- [`custom_templates.rst` on main](https://github.com/simonw/datasette/blob/main/docs/custom_templates.rst)
- [datasette-render-markdown](https://github.com/simonw/datasette-render-markdown) — cell-level, not layout
- [datasette-render-html](https://github.com/simonw/datasette-render-html) — cell-level, not layout
- [Issue #1518](https://github.com/simonw/datasette/issues/1518) — no `render_row_html` hook
- Local source: `.venv/lib/python3.12/site-packages/datasette/templates/table.html:152`, `datasette/views/table.py:771-815`
