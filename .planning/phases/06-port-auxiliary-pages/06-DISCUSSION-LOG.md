# Phase 6: Port auxiliary pages — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 06-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 06-port-auxiliary-pages
**Areas discussed:** Routing seam for search & SQL UI, Cross-database search backend, SQL UI surface (PRD R2)
**Areas skipped:** Status/llms.txt data source (Claude's discretion — defaulted to YAML port + httpx-driven generation per D-12, D-13)

---

## Routing seam for search & SQL UI

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend owns /search + /sql (no dash) | Two new frontend routes outside the /-/ namespace. Zero Caddyfile change. Datasette's native /-/search and /-/sql remain reachable. | ✓ |
| Carve /-/search + /-/sql out of @datasette | Edit Caddyfile to peel these two paths off the datasette matcher. Preserves URLs but muddles Phase-3 routing contract. | |
| Skip frontend port — keep Datasette's native pages | No frontend search or SQL UI. Removes scope but leaves Datasette branding visible after Phase 7. | |

**User's choice:** Frontend owns /search + /sql (no dash) — D-01.
**Notes:** Caddyfile is load-bearing from Phase 3 ("@datasette { path *.json *.csv *.db ; path /-/* }"); the Caddyfile itself contains a comment "Frontend handlers MUST NOT register routes under /-/". Choosing new paths preserves the suffix-routing contract intact and avoids API parity risk.

---

## Cross-database search backend

| Option | Description | Selected |
|--------|-------------|----------|
| Fan out to per-DB FTS via JSON | N parallel httpx calls to `/{db}/{table}.json?_search=`. ~3 dbs / ~10 tables today; fast. | ✓ |
| Discover FTS tables once, then fan out | Same fan-out, but introspect `/-/databases.json` + `/{db}.json` to detect FTS tables; cache via 60s metadata TTL. | |
| Scrape datasette-search-all HTML | httpx-fetch /-/search?q=X, parse HTML. Brittle; coupled to plugin output. | |

**User's choice:** Fan out to per-DB FTS via JSON — D-03.
**Notes:** Scout confirmed datasette-search-all 1.1.4 only emits HTML (`Response.html(...)` in `/app/.venv/lib/python3.12/site-packages/datasette_search_all/__init__.py`), so PRD R4's "call its JSON output" is based on a false premise. Fan-out is the simplest path that satisfies REQ-eliminate-template-drift.

### Follow-up: FTS table discovery strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded FTS table list in metadata.json | Add `display.searchable: true` hint per table; frontend reads cached metadata. | |
| Auto-discover at request time | Probe /-/databases.json + /{db}.json each search; rely on 60s cache. | |
| Auto-discover at boot / cache for app lifetime | One probe at startup; cached for process lifetime. Daily refresh = daily restart. | ✓ |

**User's choice:** Auto-discover at boot — D-04.
**Notes:** Process-lifetime cache is the cheapest per-query path. Container restarts on each daily DB refresh, so cache invalidation is automatic.

### Follow-up: Result presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by database/table with counts | "Headlines (12 results)" then top N rows per table. Familiar from datasette-search-all HTML. | |
| Interleaved single feed, sorted by date | Merge into one chronological feed; needs per-table date hints. | |
| Interleaved by relevance score | Use FTS5 rank() / BM25; merge globally. | (initially picked, then revised) |

**Initial pick:** Interleaved by relevance score.
**Refinement question raised:** FTS5 rank scores are not reliably comparable across separate FTS indexes — strict cross-table relevance ranking is research-risk.

### Refinement: Strictness of relevance ranking

| Option | Description | Selected |
|--------|-------------|----------|
| Best-effort, fall back to grouped if needed | Try cross-table ranking; if scores aren't comparable, fall back. Captures intent without blocking. | |
| Hard requirement — must be relevance-interleaved | Frontend computes a custom rank if needed. More code, debatable fairness. | |
| Relevance-ranked WITHIN groups, groups still shown | Hybrid: groups with counts, FTS-ranked within each group. Lower research risk; familiar UX. | ✓ |

**User's final choice:** Relevance-ranked WITHIN groups, groups still shown — D-05.
**Notes:** Cross-index BM25 comparison is unreliable; within-index ranking is trivially correct. Accepted hybrid that ships rank quality where it's free.

---

## SQL UI surface (PRD R2)

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal v1: textarea + db picker + table render | PRD R2 spec literally — no canned queries, no param binding. | |
| v1 + canned queries listing | All of v1 plus list per-db canned queries from /-/metadata.json. Pre-populates textarea on click. | ✓ |
| Defer SQL UI entirely | Skip /sql; users still have datasette's /-/sql. | |

**User's choice:** v1 + canned queries listing — D-07.
**Notes:** Per PRD R2 v1 + listing of `databases.{db}.queries.*` from metadata.json. Param-binding for parametric canned queries supported in v1 (D-09).

### Follow-up: SQL access scope

| Option | Description | Selected |
|--------|-------------|----------|
| Per-database only | User picks db; queries hit `/{db}.json?sql=...`. Matches /-/sql today. | ✓ |
| Add a /sql global landing | /sql lists all dbs with links to /sql/{db}. | (folded — landing page is included in D-07) |

**User's choice:** Per-database only — D-07.
**Notes:** Datasette doesn't support cross-db JOINs anyway. /sql does ship a landing page that lists all dbs (sub-feature of v1+canned), but execution is per-db.

### Follow-up: Long-running / large-result queries

| Option | Description | Selected |
|--------|-------------|----------|
| Datasette defaults (3s ms_limit, 1000 row cap) | Trust built-in safeguards. CSV export link as escape hatch. | ✓ |
| Frontend timeout + paginated re-fetch | Chunk via _next pagination tokens. More code; CSV export already solves. | |

**User's choice:** Datasette defaults — D-08.

### Follow-up: Inline query form on /{db}/{table}

| Option | Description | Selected |
|--------|-------------|----------|
| Defer entirely — /sql is sufficient | Phase 5 D-06's deferral stays deferred. | ✓ |
| Include a collapsed "SQL on this table" panel | Add `<details>` with pre-populated `SELECT * FROM [table]`. | |

**User's choice:** Defer entirely — D-10.

---

## Claude's Discretion

The following decisions did not require user input and were resolved within Phase 6 D-11..D-17 + the Claude's Discretion subsection:

- Auxiliary HTML pages (`/developers`, `/sources`, `/about`, `/how-to-use`, `/status`) are 1:1 ports of M1 templates + plugin payload shapes, refactored into FastAPI handlers using existing `datasette_client.fetch_*` helpers (D-11).
- `/status` recent_updates timeline data: port `plugins/strings.yaml`'s `recent_updates:` list into a frontend-owned `data/changelog.yaml`, loaded once at lifespan startup (D-12).
- `/llms.txt`: regenerate from datasette JSON at request time (1:1 with M1's `developers_page.llms_txt`), `Content-Type: text/plain; charset=utf-8`, same Cache-Control as HTML routes (D-13).
- Reused patterns: Cache-Control, hidden-table filter, italic-accent H1, route-handler shape, no new design tokens (D-14..D-17).
- CSS harvest: append-only Phase-6 section to `zeeker.css` covering `.timeline`, `.method-card`, `.api-table`, `.feature`, `.use-case-grid`, `.guide-hero`, `.example-box`, `.cta-section`.
- `/robots.txt` and `/favicon.ico`: port M1 robots.txt verbatim; ship favicon as a static asset.
- `/search` empty-state: hero search only, no recent / popular shortcuts (no telemetry).

## Deferred Ideas

- Inline query form on /{db}/{table} (D-10; carries Phase 5 D-06 forward).
- Cross-database SQL (datasette limitation; per-db only).
- `/-/search` → `/search` redirect (would require Caddyfile carve-out, contradicts D-01).
- SQL syntax highlighting (PRD Appendix B non-goal).
- Recent / popular searches on `/search` empty state (no telemetry in v1).
- A11y audit pass (Phase 8).
- Production deploy un-deferral (Phase 4 deploy still deferred; decision belongs in Phase 6 verifier checkpoint or Phase 7 prep).
