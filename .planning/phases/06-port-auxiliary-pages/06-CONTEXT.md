# Phase 6: Port auxiliary pages — Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the remaining frontend HTML routes so the M2 split is HTML-complete and Phase 7 can prune the M1 datasette package without leaving auxiliary surfaces stranded:

- `GET /developers` — API portal (URL patterns, params, curl examples, schema reference)
- `GET /status` — system stats + recent-updates timeline
- `GET /sources` — data sources, attribution, license info per database
- `GET /about` — what this is / who uses it
- `GET /how-to-use` — practical user guide with SQL examples
- `GET /llms.txt` — machine-readable API description (text/plain)
- `GET /search` — cross-database full-text search UI (NEW path; see D-01)
- `GET /sql` and `POST /sql/{db}` — thin SQL editor (NEW path; see D-01)

Phase 6 does NOT:
- Modify the Caddyfile (`/-/*` matcher stays locked from Phase 3).
- Delete M1 plugins or templates from `packages/zeeker-datasette/` — Phase 7.
- Touch `/{db}/{table}` or `/{db}/{table}/{pk}` rendering — Phase 5 owns these.
- Add table-page inline query forms (D-08 defers these — `/sql` is sufficient).

After Phase 6, every public HTML surface on `data.zeeker.sg` is rendered by the frontend service. Datasette retains its native `/-/search` and `/-/sql` HTML pages reachable via the same URL but they become developer-facing only — the new `/search` and `/sql` are the user-facing surfaces.

</domain>

<decisions>
## Implementation Decisions

### Routing seam (resolves the Caddyfile collision)
- **D-01:** Frontend owns `/search` and `/sql` (no leading dash). Caddyfile's `/-/*` matcher stays untouched — Phase 3's load-bearing routing contract is not modified. Datasette's native `/-/search` and `/-/sql` remain reachable as today (developer/debug surfaces, branded as Datasette). Trade-off accepted: two URL conventions co-exist; the user-visible nav links to `/search` and `/sql`.
- **D-02:** No frontend handler may register a route under `/-/`. Caddy preempts it. This is enforced at code-review time, not in code (the Caddyfile note already states the constraint).

### `/search` cross-database search
- **D-03:** Frontend `/search?q=...` fans out to per-database FTS via internal HTTP — `GET http://zeeker-datasette:8001/{db}/{table}.json?_search={q}&_size=N` for each searchable table. No `datasette-search-all` dependency (its plugin only emits HTML; no JSON output exists at v1.1.4 — confirmed during scout).
- **D-04:** FTS-table discovery is **probed once at app startup** and cached for the process lifetime. Probe by reading `/-/databases.json` + `/{db}.json` per database, extracting tables whose schema indicates an FTS counterpart (`_fts` virtual table or matching `_fts_*` shadow tables). Daily database refresh = daily container restart, so cache invalidation happens naturally. New FTS tables surface on next deploy without metadata edits.
- **D-05:** Result presentation is **grouped by database/table with counts**; rows within each group are FTS-ranked (within-table BM25 / FTS5 rank() — comparable inside one FTS index but not across tables). Layout: `Database X › Table Y (N results)` heading + top-N rows per group + "see all in this table" link to `/{db}/{table}?_search={q}`. Honors the civic-broadsheet design.
- **D-06:** Empty state and "no results" handling — render `/search` with empty `q` as a hero search + recent / popular shortcuts; render no-results as a plain message with a "search tips" snippet (quoting, FTS5 operators).

### `/sql` thin SQL editor
- **D-07:** Scope = **PRD R2 v1 + canned queries listing**. Per-database only (no cross-db). Surface:
  - `GET /sql` — landing page listing every database with link to `/sql/{db}`
  - `GET /sql/{db}` — `<textarea>` (plain, no syntax highlight) + Run button + canned-queries list pulled from `/-/metadata.json` `databases.{db}.queries.*`. Pre-populates textarea on canned-query click.
  - `POST /sql/{db}` (or GET with `?sql=...`) — runs query via `GET http://zeeker-datasette:8001/{db}.json?sql={url-encoded}`, renders results as a `<table>` with column headers from the JSON `columns` array. Errors render the JSON `error` field inline.
- **D-08:** SQL execution trusts **Datasette's built-in safeguards** — 3s `ms_limit`, 1000-row response cap, read-only mode. Frontend does NOT add timeouts, paginate, or chunk. Power users hitting the cap get a "download as CSV" link routed direct-to-datasette via Caddy suffix (Phase 5 D-05 pattern: `<a href="/{db}.csv?sql=...">CSV</a>`).
- **D-09:** Param-binding for canned queries — supported in v1. If a canned query has parameters (per `/-/metadata.json` `queries.{name}.params` or `:param` placeholders detected in the SQL string), render an input per param above the textarea. Submit fills the placeholders before execution.
- **D-10:** **No inline query form on `/{db}/{table}`** — Phase 5 D-06's deferral stays deferred. `/sql/{db}` is the single SQL surface; from a table page, users navigate via the nav.

### Auxiliary HTML pages (Claude's discretion within constraints below)
- **D-11:** `/developers`, `/sources`, `/about`, `/how-to-use`, `/status`, `/llms.txt` are 1:1 ports of the M1 plugins/templates into FastAPI handlers + Jinja templates. The M1 templates (`templates/pages/*.html`) and the M1 plugin payload functions (`developers_page._get_databases_info`, `sources_page.sources_page`, `status_page.status_page`) are reference material — port the data shape, not the Datasette plugin idiom (no `datasette.databases`, no `db.execute`; everything goes through `datasette_client.fetch_*` helpers).
- **D-12:** Status page `recent_updates` timeline data — **port the YAML list from `plugins/strings.yaml` into a frontend-owned config** (e.g., `packages/zeeker-frontend/src/zeeker_frontend/data/changelog.yaml` or a Python module). Daily refresh != changelog edit, so config-file is fine; no datasette round-trip needed. New entries get added via PR. (Carry-forward: same pattern Phase 4-5 used for static page content.)
- **D-13:** `/llms.txt` content is generated from `/-/databases.json` + per-db `/{db}.json` (tables + columns + row counts) at request time — same shape as M1's `developers_page.llms_txt`. Cache-Control matches HTML routes (`public, max-age=60, swr=300`). `Content-Type: text/plain; charset=utf-8`.

### Reused patterns (carry-forward, no re-discussion)
- **D-14:** Cache-Control: `public, max-age=60, stale-while-revalidate=300` on every GET. POST `/sql/{db}` is `Cache-Control: no-store`.
- **D-15:** Hidden-table filter — every page that lists tables (`/sources`, `/developers`, `/llms.txt`) uses the same `t.get("hidden")` flag + `_zeeker_*` prefix predicate from Phase 4 D / Phase 5.
- **D-16:** Italic-accent H1 with colored `<em>` on every auxiliary page. No new design tokens; `zeeker.css` Phase-6 append section reuses existing palette/typography variables.
- **D-17:** Route-handler shape mirrors `routes_database.py` / `routes_table.py` — lifespan-scoped `app.state.http`, explicit `Cache-Control` header, `HTTPException(404)` for unknown databases.

### Claude's Discretion
- Exact Jinja partial split for the auxiliary pages — `_partials/api_table.html`, `_partials/method_card.html` etc. — researcher/planner decides based on shared HTML chunks.
- Whether `/search` empty-state shows recent FTS queries (would need a small in-memory ring buffer) or just the hero search. Default: just the hero, no telemetry.
- CSS for `/search` results, `/sql` editor, status timeline — harvest the auxiliary subset of M1's `zeeker-base.css` (lines roughly covering `.timeline`, `.method-card`, `.api-table`, `.feature`, `.use-case-grid`). Append-only to `zeeker.css`; no token changes.
- Whether `/about` and `/how-to-use` content stays exactly as M1 wrote it or gets a light copy-edit pass. Default: copy 1:1; deviate only for stale references (e.g., the 2025 launch date stays factual).
- `/robots.txt` and `/favicon.ico` — port M1's robots.txt (35 lines); favicon ships as a static file. Trivial; no decision needed.

### Folded Todos
None.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD + intel (locks scope, R2/R4 reasoning)
- `prd-zeeker-frontend-split.md` §7.2 (frontend route inventory: `/-/search`, `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`), §10 Step 3 remainder, R2 (SQL UI v1 spec), R4 (cross-database search recommendation — premise broken; D-03 + D-04 supersede)
- `.planning/intel/SYNTHESIS.md`
- `.planning/REQUIREMENTS.md` — REQ-frontend-route-set (auxiliary leg), REQ-eliminate-template-drift, REQ-frontend-data-via-http, REQ-api-byte-parity

### Prior CONTEXT chain (carry-forward locked decisions)
- `.planning/phases/05-port-table-browse-row-view/05-CONTEXT.md` — D-01 (one generic template per route), D-05 (export direct-to-datasette via Caddy suffix — reused by `/sql` CSV export link), D-06 (table-page inline query form deferred — D-10 keeps it deferred)
- `.planning/phases/04-port-home-database-pages/04-CONTEXT.md` — route-handler pattern, base.html shell, hidden-table filter, Cache-Control values, Jinja `extends` pattern, in-memory metadata TTL cache
- `.planning/phases/03-flip-suffix-based-routing/03-CONTEXT.md` — Caddy suffix routing contract; **`/-/*` matcher is locked** and Phase 6 does not modify it (forces D-01)
- `.planning/phases/02-dual-service-bring-up/02-CONTEXT.md` — frontend package structure; no sqlite3 import in frontend; httpx-only data access

### Prior SUMMARY chain (built artifacts this phase extends)
- `.planning/phases/04-port-home-database-pages/04-01-SUMMARY.md` — FastAPI scaffold, `app.state.http`, `app.state.templates`, Jinja filters (`s()`, `plural()`, `safe_format`, `filesizeformat`, `pluralize`)
- `.planning/phases/04-port-home-database-pages/04-04-SUMMARY.md` — `routes_database.py` hidden + prefix filter; reuse for views/queries listing on `/sql/{db}`
- `.planning/phases/05-port-table-browse-row-view/05-01-SUMMARY.md` — `datasette_client.py` extension pattern + querystring allowlist (`/sql` query forwarder reuses this)
- `.planning/phases/05-port-table-browse-row-view/05-05-SUMMARY.md` — verifier script shape; `verify_phase_06.sh` should follow

### Design contract (load first — locks palette, typography, layout)
- `.claude/skills/sketch-findings-zeeker-datasette/SKILL.md` — validated design decisions; the enforceable contract
- `.claude/skills/sketch-findings-zeeker-datasette/references/theme-system.md` (palette + tokens — auxiliary CSS append must use existing tokens only)
- `.claude/skills/sketch-findings-zeeker-datasette/references/shared-shell-chrome.md` (nav + breadcrumb + footer — auxiliary pages inherit base.html)

### M1 harvest source (reference only — port the data shape, not the Datasette plugin idiom)
- `plugins/developers_page.py` — `_get_databases_info()` data shape powers both `/developers` and `/llms.txt`. `llms_txt()` body is the canonical /llms.txt format.
- `plugins/status_page.py` — `system_stats` data shape (`total_databases`, `total_tables`, `total_rows`)
- `plugins/sources_page.py` — adds `description`, `source_url`, `license`, `license_url`, `size` per database (read from `/-/metadata.json`)
- `plugins/strings.yaml` — `recent_updates:` YAML list (8 entries as of 2026-04-25); D-12 ports this into the frontend package
- `templates/pages/about.html` (110 lines) — port 1:1 less Datasette extends/include
- `templates/pages/how-to-use.html` (349 lines) — port 1:1; preserves SQL examples
- `templates/pages/sources.html` (141 lines) — port 1:1
- `templates/pages/status.html` (71 lines) — port 1:1
- `templates/pages/developers.html` (220 lines) — port 1:1
- `templates/pages/robots.txt` (35 lines) — copy verbatim to `packages/zeeker-frontend/src/zeeker_frontend/static/robots.txt` (or serve via handler)
- `static/css/zeeker-base.css` — auxiliary CSS subsections (`.timeline`, `.method-card`, `.api-table`, `.feature`, `.use-case-grid`, `.guide-hero`, `.example-box`, `.cta-section`) — harvest into `zeeker.css` Phase-6 append block

### Datasette JSON reference (live data — frontend reads exclusively via httpx)
- `http://zeeker-datasette:8001/-/databases.json` — database list (used by `/sql` landing, FTS discovery probe, `/llms.txt`, `/sources`)
- `http://zeeker-datasette:8001/{db}.json` — table list per db (FTS discovery, `/sources`, `/developers` schema reference, `/llms.txt`)
- `http://zeeker-datasette:8001/{db}/{table}.json?_search={q}&_size=N` — FTS results per table (drives `/search` fan-out)
- `http://zeeker-datasette:8001/{db}.json?sql={query}` — SQL execution endpoint (drives `/sql/{db}` POST)
- `http://zeeker-datasette:8001/-/metadata.json` — site + per-db + per-table metadata; canned queries live at `databases.{db}.queries.*`

### Build / verify infrastructure (Phase 7 boundary asserts will reuse this)
- `scripts/verify_phase_05.sh` — pattern for `verify_phase_06.sh`. Boundary assert section currently fires on Phase-6 routes (`/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/search`, `/sql`, `/llms.txt`); Phase 6 verifier flips those from "expect 404" to "expect 200".
- `scripts/verify_api_parity.sh` + `capture_baseline.sh` — REQ-api-byte-parity gate; Phase 6 adds no new datasette routes, so existing baselines remain valid (re-baseline post-deploy as `phase-06-pre/`).

### CLAUDE.md conventions
- `CLAUDE.md` §Routes — auxiliary page route inventory (already documented; Phase 6 makes it true at the frontend tier)
- `CLAUDE.md` §Notes — `_zeeker_*` metadata tables hidden from UI (apply to `/sources`, `/developers`, `/llms.txt`)
- `.planning/notes/datasette-styling-limits.md` — informs why we're porting away from Datasette plugins, not patching them

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` — extend with:
  - `discover_searchable_tables(client) -> dict[str, list[str]]` (one-time at startup; called from lifespan), keyed `{db: [table_names_with_fts]}`.
  - `search_table(client, db, table, q, size)` — wraps `/{db}/{table}.json?_search=...&_size=...`.
  - `execute_sql(client, db, sql, params)` — wraps `/{db}.json?sql=...&_param_*=...`.
  Pattern matches existing `fetch_table` / `fetch_row` from Phase 5.
- `packages/zeeker-frontend/src/zeeker_frontend/filters.py` — `filesizeformat`, `pluralize`, `safe_format`, `s()`, `plural()` all apply to auxiliary pages without modification.
- `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` — auxiliary pages all `{% extends "base.html" %}`.
- `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` — append-only Phase 6 section. No token changes; reuse `--color-*` and typography vars.
- `packages/zeeker-frontend/src/zeeker_frontend/urls.py` (Phase 5) — querystring allowlist pattern; `/sql` query forwarder will need an `_sql_param` allowlist.

### Established Patterns
- **Route handler shape:** `@router.get("/path", response_class=HTMLResponse)` with `(request, ...)` params; lifespan-scoped httpx; explicit `Cache-Control` header; `HTTPException(404)` for missing data.
- **Hidden filter:** `t.get("hidden") or t.get("name", "").startswith("_zeeker")` — applies to `/sources`, `/developers`, `/llms.txt`, AND `/sql` canned-queries listing.
- **Metadata access:** `(site_metadata.get("databases") or {}).get(db, {}).get("tables", {}).get(table, {})` — same path Phase 4-5 use; canned queries live at `.get("queries", {})`.
- **POST handler:** new for `/sql/{db}`. Use FastAPI `Form(...)` for textarea body; CSRF not needed (read-only execution; no session state).

### Integration Points
- `main.py` router registration order matters (Phase 5 lesson). New routers register **before** `database_router` and `routes_table_router` because `/search`, `/sql`, `/sql/{db}`, `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt` are all more-specific (literal-prefix) than the catch-all `/{db}` and `/{db}/{table}`. FastAPI picks first-registered matching route.
- Lifespan extension: `app.state.searchable_tables = await discover_searchable_tables(...)` runs after `app.state.http` is set up (Phase 4 lifespan). One-shot probe at boot; no TTL needed.
- Caddyfile is **not modified**. CSS / fonts / static / robots.txt all already route to frontend (none match `*.json|*.csv|*.db|/-/*`).
- `verify_phase_06.sh` extends `verify_phase_05.sh` — flips Phase-5's "expect 404 on auxiliary routes" assertions into "expect 200 with HTML body containing italic-accent H1 + zeeker.css link".

</code_context>

<specifics>
## Specific Ideas

### `/search` data flow

```python
# At startup (lifespan):
app.state.searchable_tables = {
    "sglawwatch": ["headlines", "about_singapore_law"],
    "sg-gov-newsrooms": ["acra_news", "judiciary_news", ...],
    "Zeeker-Judgements": ["judgments"],
}

# At request time (GET /search?q=foo):
async with asyncio.TaskGroup() as tg:
    tasks = {
        f"{db}/{table}": tg.create_task(
            search_table(client, db, table, q, size=10)
        )
        for db, tables in app.state.searchable_tables.items()
        for table in tables
    }
results = {key: t.result() for key, t in tasks.items()}
# Render: per-(db, table) group with count + top-10 ranked rows + "see all" link.
```

### `/sql/{db}` minimal HTML shape

```html
<form method="POST" action="/sql/{{ db }}">
  {% if canned %}
  <details>
    <summary>Saved queries ({{ canned|length }})</summary>
    <ul>
      {% for name, q in canned.items() %}
      <li><button type="button" data-sql="{{ q.sql }}">{{ name }}</button></li>
      {% endfor %}
    </ul>
  </details>
  {% endif %}
  <textarea name="sql" rows="6">{{ sql or 'SELECT * FROM ' + first_table + ' LIMIT 10' }}</textarea>
  <button type="submit">Run</button>
</form>
{% if results %}
  <table>...</table>
  <p>
    <a href="/{{ db }}.csv?sql={{ sql|urlencode }}">CSV</a> ·
    <a href="/{{ db }}.json?sql={{ sql|urlencode }}">JSON</a>
  </p>
{% endif %}
```

CSV/JSON links route through Caddy to datasette automatically (suffix matcher).

### Status changelog migration

`plugins/strings.yaml` `recent_updates:` block → new file:

```
packages/zeeker-frontend/src/zeeker_frontend/data/changelog.yaml
```

Loaded once at startup (lifespan) and stored on `app.state.changelog`. Format unchanged (date / type / title / description). Phase 7 deletion of `plugins/strings.yaml` is safe because the frontend has its own copy.

### `/llms.txt` content
Identical to M1's `developers_page.llms_txt` output, regenerated from `/-/databases.json` + per-db `/{db}.json`. `Content-Type: text/plain; charset=utf-8`. `_zeeker_*` tables filtered.

### `verify_phase_06.sh` shape
Extend `verify_phase_05.sh`:
- Flip Phase-5 boundary asserts: `/developers /status /sources /about /how-to-use /llms.txt /search /sql` → expect 200 + frontend body
- Add positive structural asserts:
  - `/search?q=test` 200, body contains `<form` + at least one result group OR a "no results" message
  - `/sql/sglawwatch` 200, body contains `<textarea` + canned-queries section if metadata.json defines any
  - `/llms.txt` 200, `Content-Type: text/plain`, body starts with `# data.zeeker.sg`
  - `/static/robots.txt` 200 (or `/robots.txt` 200 — pick one and document)
- Add negative asserts:
  - `/-/search?q=test` still 200 from datasette (HTML, not frontend)
  - `/-/sql` still 200 from datasette
  - `/sql/_zeeker_internal` 404 (hidden-db filter — N/A unless we have a hidden db; if not, omit)

</specifics>

<deferred>
## Deferred Ideas

- **Inline query form on `/{db}/{table}` page** — Phase 5 D-06 deferred this; Phase 6 D-10 keeps it deferred. `/sql/{db}` is the single SQL surface.
- **Cross-database SQL** — datasette doesn't support cross-db JOINs; v1 is per-db only.
- **`/-/search` redirect to `/search`** — would require Caddyfile carve-out, contradicting D-01. If users want it later, reconsider in Phase 8.
- **SQL syntax highlighting (CodeMirror / Prism)** — explicitly out per PRD Appendix B (full SQL editor is non-goal). Plain textarea ships in v1.
- **Recent / popular searches on empty `/search`** — Claude's discretion (default: omit; no telemetry).
- **`/favicon.ico`** — port the M1 file if present; trivial.
- **A11y audit pass on auxiliary pages** — Phase 8 follow-up.
- **Production deploy un-deferral** — Phase 4's deploy is still deferred. Decision belongs in Phase 6's verifier checkpoint or Phase 7 prep, not in this CONTEXT.

### Reviewed Todos (not folded)
None — no pending todos surfaced in cross-reference.

</deferred>

---

*Phase: 06-port-auxiliary-pages*
*Context gathered: 2026-04-25*
