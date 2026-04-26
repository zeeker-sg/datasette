# Synthesized Technical Constraints

> No SPEC documents were ingested. The following constraints are PRD-level technical requirements that downstream specs must honor.

## CON-routing-table — URL routing contract
**Source:** prd-zeeker-frontend-split.md §6
**Type:** routing-contract
**Constraint:**
- `*.json` → datasette
- `*.csv` → datasette
- `*.db` → datasette
- `/-/*` → datasette (`/-/sql`, `/-/versions.json`, `/-/search-all`)
- everything else → frontend
Suffix matching only — no path-prefix routing.

## CON-frontend-stack — Frontend implementation stack
**Source:** prd-zeeker-frontend-split.md §7.2
**Type:** technology-constraint
**Constraint:** FastAPI + Jinja2 + httpx + uv + black-formatted code. In-memory TTL cache (seconds–minutes) on metadata endpoints; row-level queries uncached.

## CON-datasette-shrink — Datasette service shrinkage
**Source:** prd-zeeker-frontend-split.md §7.1
**Type:** scope-constraint
**Constraint:** Post-migration `packages/zeeker-datasette/` keeps only: `Dockerfile`, `scripts/download_from_s3.py`, `entrypoint.sh`, `metadata.json`, `--cors`, read-only mode. Deletes: all `templates/`, all `static/`, UI plugins (`developers_page.py`, `status_page.py`, `sources_page.py`, `string_manager.py`, `template_filters.py`).

## CON-healthcheck — Datasette healthcheck
**Source:** prd-zeeker-frontend-split.md §7.1
**Type:** operational-constraint
**Constraint:** `GET /-/versions.json` returns 200 = healthy. Boot window 10–30s for S3 download.

## CON-immutable-zeeker-surface — Out-of-scope surfaces
**Source:** prd-zeeker-frontend-split.md Appendix B
**Type:** scope-fence
**Constraint:** This refactor does NOT modify: `fetch_data()` implementations, `zeeker.toml` schema, S3 bucket layout, refresh cron mechanics, data scraping projects.
