# Synthesized Requirements

## REQ-api-byte-parity
**Source:** prd-zeeker-frontend-split.md §3, §6, §12
**Description:** Every `.json`, `.csv`, `.db`, and `/-/*` URL under `data.zeeker.sg` must return identical bytes before and after the refactor (timestamps and Datasette version strings excepted).
**Acceptance:** `diff` of `curl -s https://data.zeeker.sg/sglawwatch/headlines.json` pre- and post-migration shows no meaningful changes.
**Scope:** API contract preservation.

## REQ-suffix-routing-contract
**Source:** prd-zeeker-frontend-split.md §6
**Description:** Caddy reverse proxy must route by URL suffix: `*.json`, `*.csv`, `*.db`, `/-/*` → datasette; everything else → frontend.
**Acceptance:** local `curl` against both `.json` and HTML URLs proves both paths reach the correct backend.
**Scope:** URL routing contract.

## REQ-eliminate-template-drift
**Source:** prd-zeeker-frontend-split.md §3
**Description:** A single frontend codebase owns all HTML — no V1/V2 template drift.
**Acceptance:** homepage, database page, table page, and row page share a single design language; no `# (sglawwatch)` heading bug; no row-data-in-column-labels bug; no 2025/2026 footer year mismatch.
**Scope:** Frontend HTML rendering ownership.

## REQ-escape-datasette-template-surface
**Source:** prd-zeeker-frontend-split.md §3
**Description:** Frontend must not depend on Datasette's `database.html`/`table.html` template overrides or `app.css` specificity workarounds.
**Acceptance:** `packages/zeeker-datasette/` contains no `templates/` directory and no `static/` directory after migration.
**Scope:** Architectural constraint — Datasette template seam abandonment.

## REQ-preserve-zeeker-cli
**Source:** prd-zeeker-frontend-split.md §3, §9
**Description:** `zeeker init` / `add` / `build` / `deploy` and the S3 deployment pipeline continue to work unchanged.
**Acceptance:** `zeeker.toml` schema unchanged; S3 bucket layout (`latest/`, `assets/databases/`, `archives/`) unchanged; refresh cron mechanics unchanged.
**Scope:** zeeker CLI investment preservation.

## REQ-incremental-migration
**Source:** prd-zeeker-frontend-split.md §3, §10
**Description:** Migration proceeds in independently-deployable steps; site never fully down; un-ported pages fall back to legacy Datasette HTML during transition.
**Acceptance:** each of the 6 migration steps is deployable on its own without breaking existing URLs.
**Scope:** Migration safety.

## REQ-reduce-plugin-count
**Source:** prd-zeeker-frontend-split.md §3, §12
**Description:** UI-only Datasette plugins are deleted, not ported. Datasette service ends with 0 UI-coupled plugins.
**Acceptance:** `developers_page.py`, `status_page.py`, `sources_page.py`, `string_manager.py`, `template_filters.py` removed from datasette service.
**Scope:** Plugin reduction.

## REQ-frontend-route-set
**Source:** prd-zeeker-frontend-split.md §7.2
**Description:** Frontend FastAPI service serves `/`, `/{db}`, `/{db}/{table}`, `/{db}/{table}/{pk}`, `/-/search`, `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`.
**Acceptance:** every route returns 200 with rendered HTML for at least one valid input.
**Scope:** Frontend coverage.

## REQ-frontend-data-via-http
**Source:** prd-zeeker-frontend-split.md §7.2, Appendix A #5
**Description:** Frontend reads data exclusively via internal HTTP to `http://datasette:8001/...json`. No direct SQLite access from frontend.
**Acceptance:** frontend container has no SQLite client and no volume mount of `./data`.
**Scope:** Data-access discipline ("Datasette owns the database").

## REQ-internal-only-datasette-exposure
**Source:** prd-zeeker-frontend-split.md §7.1
**Description:** Datasette service is internal-only; only Caddy publishes `:80`/`:443`.
**Acceptance:** `docker compose config` shows datasette service has no `ports:` mapping; only Caddy exposes ports.
**Scope:** Network exposure.
