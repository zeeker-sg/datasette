# Synthesized Context

## Background — why this PRD exists
**Source:** prd-zeeker-frontend-split.md §1, §2

`data.zeeker.sg` runs a customised Datasette container. Successive UI redesigns (V1 dark/futuristic → V2 light/editorial) have left technical debt from fighting Datasette's template override surface. The homepage was migrated to V2; `database.html`, `table.html`, `row.html`, the SQL examples partial, and header/footer were not. Two eras co-exist in the same deployment.

Observable defects on `/sglawwatch` cited in the PRD: malformed heading (`# (sglawwatch)`), duplicated slug labels, row data leaking into "Key Columns," invalid auto-generated SQL (`SELECT , FROM ...`), 2025/2026 copyright mismatch.

Five custom plugins (`developers_page`, `status_page`, `sources_page`, `string_manager`, `template_filters`) exist primarily to work around UI constraints, not to extend data functionality.

The author values the API surface (`.json`, `.csv`, `.db`, `/-/sql`, facets, FTS) and explicitly does NOT want to re-implement it.

Cross-referenced in `.planning/notes/datasette-styling-limits.md` (existing repo doc) which already documents known dead-ends with `app.css` specificity and the narrow `_table-{db}-{table}.html` seam.

## Risks documented in the PRD
**Source:** prd-zeeker-frontend-split.md §11

- **R1 — Facet JSON parity** — facets with array columns or m2m may need extra API calls.
- **R2 — Query UI** — `/-/sql` HTML page replacement is non-trivial; v1 can be a `<textarea>`.
- **R3 — Streaming CSV** — preserved automatically (CSV URLs route to datasette).
- **R4 — Cross-database search** — call `datasette-search-all` JSON in v1; re-implement later if needed.
- **R5 — Per-database overlays** — retain S3 overlay mechanism vs retire? Decision deferred to migration Step 6.
- **R6 — Matomo analytics** — moves from datasette to frontend as `<script>` include.
- **R7 — Time cost vs project ROI** — author flags continuation of project itself is in question; PRD targets minimum viable change. Steps 1 + first page of Step 3 deliver >50% of perceived UI fix in under a weekend.

## Out of scope
**Source:** prd-zeeker-frontend-split.md §13, Appendix B

Explicitly out: authentication, private databases, full SQL editor with syntax highlighting, API versioning, hosted SaaS, replacing Datasette, modifying `fetch_data()`, `zeeker.toml`, S3 bucket layout, refresh cron, scraping projects.
