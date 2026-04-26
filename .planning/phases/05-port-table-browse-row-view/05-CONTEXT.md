# Phase 5: Port table browse + row view — Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement frontend routes `/{db}/{table}` (paginated rows + facets + exports + FTS) and `/{db}/{table}/{pk}` (single row view). Everything from ROADMAP §Phase 5 is in scope; `/-/sql` inline query form, `/-/search`, `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt` are Phase 6; Datasette pruning is Phase 7.

Phase 5 closes the last 404-producing gap in the frontend — after this phase lands, `/{db}/{table}/{pk}` works end-to-end and the deploy deferral from Phase 4 becomes resolvable.

</domain>

<decisions>
## Implementation Decisions

### Table-page rendering strategy
- **D-01:** One generic `table.html` template drives every table. No per-table Jinja override files (no `_table-{db}-{table}.html` proliferation). Honors REQ-eliminate-template-drift; un-reintroducing the override seam would sabotage Phase 7's pruning.
- **D-02:** Per-table rendering is controlled by `metadata.databases.{db}.tables.{table}.display` hints inside the existing `metadata.json`. No new config files. The frontend reads the hint via the same per-DB metadata path `routes_database.py` already uses (`site_metadata.databases[db].tables[table]`).

### Row-page rendering strategy
- **D-03:** Table and row modes are **separate** fields:
  - `display.table_mode` — drives `/{db}/{table}` layout (e.g. `feed`, `tabular`, `longform-list`)
  - `display.row_mode` — drives `/{db}/{table}/{pk}` layout (e.g. `article`, `judgment`, `longform`, `tabular`)
  Rationale: a news-feed-style table (`table_mode: feed`, sketch 004-A) commonly opens into an `article` row (sketch 003-A). A judgment index (`table_mode: tabular`) opens into a `judgment` row with sidebar meta. Decoupling table_mode and row_mode keeps the common cases ergonomic without forcing them to match.
- **D-04:** When neither mode is set, fall back to **tabular** on both pages:
  - `table.html` → dense `<table>` grid with column headers and raw row values
  - `row.html` → key-value `<dl>` of all columns
  Preserves datasette's dynamic behavior for unclassified / utility / ad-hoc-exploration tables; editorial styling is opt-in per table via the hints. Zero-config tables are never broken.

### Export routing
- **D-05:** Export links go **direct to datasette via Caddy suffix routing** — `<a href="/{db}/{table}.csv?{same-query-params}">CSV</a>`. The `.csv` / `.json` / `.parquet` suffix triggers Caddy's `@datasette` matcher (already validated in Phase 3); the request never enters the frontend. Byte-identical to M1 exports (REQ-api-byte-parity automatically held). Frontend's only job is constructing the link with the active query string.

### Inline query form
- **D-06:** **Deferred to Phase 6.** Phase 5 table page has facets, pagination, sort, and FTS — but no free-form filter-input-per-column UI and no SQL editor. Phase 6 owns `/developers`, `/-/search`, `/status`, etc. and is the right seam for an inline SQL editor or global filter-builder. This keeps Phase 5 scope on "render what datasette already gives us via JSON, styled" without introducing a new input-parsing surface.

### Claude's Discretion

User deferred the "Facets, pagination, FTS UX" gray area to Claude. Recommended defaults (confirm during planning if ambiguous):
- **Facets:** collapsible accordion per facet column. Top N values shown with counts; "show all" expands. Applied facets surface as chip pills above the table with `×` to remove each. Matches datasette's `?_facet=col&col=val` URL scheme 1:1.
- **Pagination:** cursor-based, using datasette's native `next_url` from the JSON payload. Rendered as "← Previous / Next →" with page-size selector (25 / 50 / 100). No numbered pages — datasette doesn't expose total-count cheaply on large tables.
- **FTS:** hero search input on the table page. Submits as `?_search={term}` (datasette's native param), forwards to datasette, renders results in the same table layout. Highlight (`<mark>`) comes from datasette's `_search_highlight` when present.
- **Sort:** column header click toggles asc → desc → clear; URL reflects `?_sort=col` / `?_sort_desc=col`.
- **Carry forward from Phase 4:** Cache-Control: `public, max-age=60, stale-while-revalidate=300` on both GET routes. Italic-accent H1 on both pages. `_zeeker_*` prefix + `hidden` flag filter applies to views/queries as well as tables. `app.state.http` + `app.state.templates` wiring; no circular imports.

### Folded Todos
None.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design contract (load first — locks palette, typography, layout)
- `.claude/skills/sketch-findings-zeeker-datasette/SKILL.md` — validated design decisions; the enforceable contract
- `.claude/skills/sketch-findings-zeeker-datasette/references/row-as-article.md` (sketch 003-A — article row layout)
- `.claude/skills/sketch-findings-zeeker-datasette/references/table-as-news-archive.md` (sketch 004-A — feed card table layout)
- `.claude/skills/sketch-findings-zeeker-datasette/references/database-table-grid.md` (sketch 002-B — already harvested in Phase 4, cross-reference for consistency)

### Prior CONTEXT chain (carry-forward locked decisions)
- `.planning/phases/04-port-home-database-pages/04-CONTEXT.md` — route-handler pattern, filter strategy, Cache-Control, data-access contract, base.html shell
- `.planning/phases/03-flip-suffix-based-routing/03-CONTEXT.md` — Caddy suffix routing contract (`.csv`/`.json`/`.parquet` → datasette); do NOT modify
- `.planning/phases/02-dual-service-bring-up/02-CONTEXT.md` — frontend package structure; no sqlite3 import anywhere in frontend

### Prior SUMMARY chain (built artifacts this phase extends)
- `.planning/phases/04-port-home-database-pages/04-01-SUMMARY.md` — FastAPI scaffold, `app.state.http`, `app.state.templates`, Jinja filters
- `.planning/phases/04-port-home-database-pages/04-03-SUMMARY.md` — `routes_home.py` handler pattern to replicate for `routes_table.py` and `routes_row.py`
- `.planning/phases/04-port-home-database-pages/04-04-SUMMARY.md` — `routes_database.py` hidden + prefix filter; reuse for views/queries
- `.planning/phases/04-port-home-database-pages/04-05-SUMMARY.md` — verifier script shape; `verify_phase_05.sh` should follow the same structure

### PRD + requirements
- `prd-zeeker-frontend-split.md` §7.2 (frontend route inventory), §10 Step 3 second tranche (phase 5 scope), R1 (facet edge cases: array columns, m2m)
- `.planning/REQUIREMENTS.md` — REQ-frontend-route-set (table + row), REQ-frontend-data-via-http, REQ-api-byte-parity, REQ-eliminate-template-drift (see D-01 rationale)

### M1 harvest source (reference only — do NOT copy wholesale)
- `templates/table.html` — M1 generic table page; read for structural patterns, do NOT port verbatim
- `templates/row.html` — M1 generic row page
- `templates/_table-sg-gov-newsrooms-*.html` (8 files) — M1 feed-card overrides; reference ONLY for what `feed` mode should encode in the generic template (column slots: kicker / title / byline / body / date / source / tags)
- `templates/_table-Sglawwatch-about_singapore_law.html` — M1 longform reference
- `templates/_table-Zeeker-Judgements-judgments.html` — M1 judgment reference (informs `row_mode: judgment`)

### Datasette JSON reference (live data)
- `http://zeeker-datasette:8001/{db}/{table}.json?_size=N&_facet=col&_search=term&_sort=col` — paginated rows + facets + FTS + sort
- `http://zeeker-datasette:8001/{db}/{table}/{pk}.json` — single row
- `http://zeeker-datasette:8001/-/metadata.json` — table metadata incl. the new `display.*` hints (read via cached helper in `datasette_client.py`)

### CLAUDE.md conventions
- `CLAUDE.md` §Design & UI Routing — sketch-findings skill is authoritative for visual decisions
- `.planning/notes/datasette-styling-limits.md` — Datasette template override surface (reference for what the M1 `_table-*.html` files existed to work around)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` — add `fetch_table(client, db, table, params)` and `fetch_row(client, db, table, pk)` helpers following the existing `fetch_database` pattern. The 60s TTL metadata cache already covers `/-/metadata.json` reads.
- `packages/zeeker-frontend/src/zeeker_frontend/filters.py` — `filesizeformat`, `pluralize`, `safe_format` all apply directly; `s()` and `plural()` globals are available.
- `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` — extends without modification; table and row pages both `{% extends "base.html" %}`.
- `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` — Phase 4 harvested the home + database + shell + rows subsets. Phase 5 likely needs to harvest the **table feed** + **row reading** CSS ranges from M1's `static/css/zeeker-base.css` (plan 05-02 target).

### Established Patterns
- Route handler: `@router.get("/{db}/{table}", response_class=HTMLResponse)` with `(request, db, table)` params. Follow `routes_database.py` exactly — lifespan-scoped httpx client, 404 via `HTTPException(404)` when `fetch_table` returns `None`, explicit `Cache-Control` header on the response.
- Metadata merge: `(site_metadata.get("databases") or {}).get(db, {}).get("tables", {}).get(table, {})` — gets per-table display hints alongside title/description.
- Filter: `if not t.get("hidden") and not t.get("name", "").startswith("_zeeker")` — apply the same rule to **views** and **canned queries** the database page renders today.

### Integration Points
- `main.py` currently mounts `home_router` and `database_router`. Phase 5 adds `routes_table` and `routes_row` routers. **Registration order matters** (learned in Phase 4): any new explicit `/{magic-path}` routes (there shouldn't be any) must register BEFORE `database_router`, which must register BEFORE `routes_table`/`routes_row` because `/{db}/{table}` is strictly more specific than `/{db}`. FastAPI picks the most specific match when routes are declared in order.
- Caddy suffix routing is already configured for `.csv`, `.json`, `.parquet`, `.db`, `/-/*` → datasette. Phase 5 does NOT modify Caddyfile or Caddyfile.prod.
- `verify_phase_04.sh` is the template for `verify_phase_05.sh`. Expect sections for: positive structural asserts on `/{db}/{table}` and `/{db}/{table}/{pk}`, negative asserts that `_zeeker_*` views don't leak, export-link correctness (href matches `.csv` / `.json` pattern and suffix-routes to datasette), Phase-6 boundary (`/{db}/{table}/{pk}/some-nested-path` → 404).

</code_context>

<specifics>
## Specific Ideas

### Proposed `display` hint schema (the planner should confirm during planning)

```json
{
  "databases": {
    "sglawwatch": {
      "tables": {
        "headlines": {
          "title": "Headlines",
          "display": {
            "table_mode": "feed",
            "row_mode": "article",
            "columns": {
              "kicker": "source",
              "title": "title",
              "byline": "byline",
              "body": "summary",
              "date": "published_date",
              "source_url": "source_url"
            }
          }
        },
        "about_singapore_law": {
          "display": {
            "table_mode": "longform-list",
            "row_mode": "longform"
          }
        }
      }
    },
    "Zeeker-Judgements": {
      "tables": {
        "judgments": {
          "display": {
            "table_mode": "tabular",
            "row_mode": "judgment",
            "columns": {
              "title": "case_name",
              "citation": "citation",
              "court": "court",
              "date": "date"
            }
          }
        }
      }
    }
  }
}
```

Unhinted tables (e.g. `schema_versions`, `_zeeker_updates` if it ever surfaces) fall to tabular. `columns` is only read when `table_mode`/`row_mode` references slotted layouts; modes like `tabular` ignore it.

### Deploy deferral note
Phase 4's production deploy is still deferred. Phase 5 ships locally; the deploy un-deferral decision waits until Phase 6 (or whenever the operator considers the UX complete enough for public ship).

</specifics>

<deferred>
## Deferred Ideas

- **Inline SQL editor / `/-/sql`-like on the table page** — moved to Phase 6 per D-06.
- **Global search `/-/search`** — Phase 6.
- **Facet edge cases: array columns, m2m** — PRD R1 flags these. Default facet UI handles the common case (simple-value columns); array/m2m edge cases get noted in plan 05-0x as "handle gracefully, tabular fallback acceptable" unless they surface in sglawwatch/Zeeker-Judgements data.
- **Permalink URL design polish** (e.g. `?page=N` friendly URLs vs datasette's cursor tokens) — stays with datasette's native scheme for phase 5; revisit if the cursor URLs are visibly ugly post-ship.
- **Numbered pagination** — deferred. Datasette doesn't expose total-count cheaply; adding count-queries would slow large tables. Cursor next/prev is the default.

</deferred>

---

*Phase: 05-port-table-browse-row-view*
*Context gathered: 2026-04-22*
