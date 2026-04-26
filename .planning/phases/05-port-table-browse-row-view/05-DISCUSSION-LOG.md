# Phase 5: Port table browse + row view — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 05-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 05-port-table-browse-row-view
**Areas discussed:** Per-table overrides vs generic; Row view dispatch; Export + inline query form scope
**Skipped (Claude's discretion):** Facets / pagination / FTS UX

---

## Per-table overrides vs generic

### Q1: How should the frontend handle table pages?

| Option | Description | Selected |
|--------|-------------|----------|
| Generic + metadata hints | One `table.html`, per-table `display` hints in `metadata.json`. | ✓ |
| Single universal template, no hints | Pure column-shape convention, no escape hatch. | |
| Mirror M1's `_table-{db}-{table}.html` seam | 11+ Jinja overrides, reinstates template drift. | |
| You decide | Claude picks based on existing patterns. | |

**User's choice:** Generic + metadata hints (Recommended).
**Notes:** Honors REQ-eliminate-template-drift. Per-table expressiveness stays declarative in config, not in template proliferation.

### Q2: Where should the per-table display hints live?

| Option | Description | Selected |
|--------|-------------|----------|
| Nested under `metadata.databases.{db}.tables.{table}.display` | Colocated with existing per-table metadata (title, description, license). | ✓ |
| Separate `display.json` per database | New file alongside each DB's metadata. | |
| Inline in frontend config | Global frontend-owned `display.json`; divorces display from DB metadata. | |
| You decide | Claude picks. | |

**User's choice:** Nested under the existing `metadata.json` per-table path.
**Notes:** Inherits S3 overlay pipeline; zero new files; same pattern `routes_database.py` already uses.

---

## Row view dispatch

### Q3: How should `/{db}/{table}/{pk}` pick which row layout to render?

| Option | Description | Selected |
|--------|-------------|----------|
| Single `display` hint drives both table and row | One `mode` field controls both pages. | |
| Separate `display.table_mode` and `display.row_mode` | Independent fields — tables and rows can differ. | ✓ |
| Column-shape heuristic, no hint | Inspect columns at render time; no config. | |
| You decide | Claude picks based on sketch composition. | |

**User's choice:** Separate `display.table_mode` and `display.row_mode`.
**Notes:** Enables common pair (`feed` table → `article` row) without forcing equality. Judgment tables (tabular index) opening to judgment row views work naturally.

### Q4: Fallback when `display.table_mode` / `display.row_mode` are unset?

| Option | Description | Selected |
|--------|-------------|----------|
| Tabular fallback — classic grid | Dense `<table>` on table pages, key-value `<dl>` on row pages. | ✓ |
| Try column-shape heuristic, fall back to tabular | Confidence-scored guess; tabular when unsure. | |
| Editorial-first — default to longform | Opinionated; weird tables look broken. | |
| You decide | Claude picks. | |

**User's choice:** Tabular fallback.
**Notes:** Preserves datasette's dynamic behavior for unclassified / utility tables. Editorial styling is opt-in per table.

---

## Export + inline query form scope

### Q5: How should export links (CSV / JSON / Parquet) be routed?

| Option | Description | Selected |
|--------|-------------|----------|
| Direct to datasette via Caddy suffix routing | `.csv` / `.json` / `.parquet` routes via Caddy's `@datasette` matcher; byte-identical. | ✓ |
| Frontend proxies through to datasette | Extra hop; enables filename headers; risks parity drift. | |
| No exports in phase 5 | Defer entirely; violates ROADMAP success criterion. | |
| You decide | Claude picks based on Caddy contract. | |

**User's choice:** Direct to datasette via Caddy suffix routing.
**Notes:** Zero frontend code; REQ-api-byte-parity automatically held; already validated in Phase 3.

### Q6: Should the inline query form ship in phase 5?

| Option | Description | Selected |
|--------|-------------|----------|
| Ship per-table `=` filter inputs | Per-column equality filters that update the query string. | |
| Defer to phase 6 (aux routes) | Phase 6 adds inline SQL editor alongside `/-/search`. | ✓ |
| Ship a full SQL editor inline | Duplicate `/-/sql`; security surface; scope creep. | |
| You decide | Claude picks. | |

**User's choice:** Defer to phase 6.
**Notes:** Keeps phase 5 on "render what datasette gives us, styled." Phase 6 owns the free-form input surface.

---

## Claude's Discretion

User skipped the "Facets, pagination, FTS UX" gray area. CONTEXT.md documents recommended defaults (collapsible accordion facets, cursor pagination via datasette's `next_url`, FTS as `?_search=` matching datasette native, sort via column-header toggle). The planner or executor may adjust if research turns up better patterns.

## Deferred Ideas

- Inline SQL editor → Phase 6
- Global `/-/search` → Phase 6
- Facet edge cases (array columns, m2m) → planner to note in 05-0x plan
- Numbered pagination → deferred; cursor-based is default
- Permalink URL polish → defer unless cursor tokens are visibly ugly post-ship
