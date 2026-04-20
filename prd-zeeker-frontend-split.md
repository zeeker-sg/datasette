# PRD: Split data.zeeker.sg into API (Datasette) + Frontend (FastAPI)

**Status:** Draft
**Author:** houfu
**Last updated:** 20 April 2026
**Scope:** Architectural refactor of the `zeeker-datasette` deployment; no changes to data pipeline or zeeker CLI core.

---

## 1. Background

`data.zeeker.sg` serves Singapore legal datasets via a customised Datasette container. Over successive redesigns (V1 dark/futuristic → V2 light/editorial), the UI has accumulated technical debt from fighting Datasette's template override surface:

- Homepage (`index.html`) and a few supporting pages were migrated to V2; `database.html`, `table.html`, `row.html`, the SQL examples partial, and header/footer were not. The two eras co-exist in the same deployment.
- Observable defects on `/sglawwatch` today include: malformed heading (`# (sglawwatch)`), duplicated slug labels, row data leaking into "Key Columns," invalid auto-generated SQL (`SELECT , FROM ...`), and a 2025/2026 copyright mismatch between homepage and database pages.
- `.planning/notes/datasette-styling-limits.md` in the repo already documents known dead-ends with the override system (`app.css` specificity, narrow `_table-{db}-{table}.html` seam).
- Five custom plugins (`developers_page`, `status_page`, `sources_page`, `string_manager`, `template_filters`) exist primarily to work around UI constraints, not to extend data functionality.

The API, by contrast, works well and is the surface the author values most: `.json`, `.csv`, `.db`, `/-/sql`, facets, FTS.

## 2. Problem Statement

The HTML rendering path in Datasette's template system is where all the debt lives. Continuing to patch templates produces drift; replacing the stack wholesale risks re-implementing the API surface (which works). A minimal-investment path is needed that fixes the UI decisively while preserving the API byte-for-byte and reusing the existing zeeker CLI and S3 pipeline.

## 3. Goals

- **Preserve the API contract.** Every `.json`, `.csv`, `.db`, and `/-/*` URL under `data.zeeker.sg` returns identical bytes before and after the refactor.
- **Eliminate V1/V2 template drift.** A single frontend codebase owns all HTML.
- **Escape Datasette's template override surface.** No more overriding `database.html`, `table.html`, or fighting `app.css` specificity.
- **Preserve the zeeker CLI investment.** `zeeker init` / `add` / `build` / `deploy` and the S3 deployment pipeline continue to work unchanged.
- **Support incremental migration.** No "big-bang" cutover; the site remains deployable at every step.
- **Reduce plugin count.** UI-only plugins are deleted, not ported.

## 4. Non-Goals

- Re-implementing Datasette's SQL/JSON/CSV surface.
- Adding write paths. The system remains read-only.
- Changing how databases are built, metadata is declared, or data is pushed to S3.
- Adding authentication, user accounts, or any multi-tenant concepts.
- A full visual redesign. V2 aesthetic (Inter + JetBrains Mono, CSS custom properties, editorial layout) is the target; this PRD is about structural delivery of that aesthetic, not re-scoping it.
- Mobile app, API versioning, rate limiting, or analytics rework.

## 5. Proposed Architecture

Three services behind a single reverse proxy. Only the proxy is exposed publicly.

```
                         ┌─────────────┐
                         │    Caddy    │   :80 / :443
                         └──────┬──────┘
                                │  routes by URL suffix
                ┌───────────────┴───────────────┐
                ▼                               ▼
        ┌───────────────┐              ┌───────────────┐
        │   frontend    │   internal   │   datasette   │
        │ FastAPI+Jinja │──── HTTP ───►│  read-only    │
        │    :8000      │              │    :8001      │
        └───────────────┘              └───────┬───────┘
                                               │
                                               ▼
                                          ./data (SQLite
                                          from S3 at boot)
```

### Key design decision: suffix-based routing

Caddy routes by URL ending, not path prefix. This is the single move that preserves the API contract without per-database configuration.

## 6. URL Routing Contract

| URL pattern | Routes to | Example |
|---|---|---|
| `*.json` | datasette | `/sglawwatch/headlines.json` |
| `*.csv` | datasette | `/sglawwatch/headlines.csv` |
| `*.db` | datasette | `/sglawwatch.db` |
| `/-/*` | datasette | `/-/sql`, `/-/versions.json`, `/-/search-all` |
| everything else | frontend | `/`, `/sglawwatch`, `/sglawwatch/headlines`, `/developers` |

**Consequence:** any existing script, scraper, or integration that uses `.json` or `.csv` URLs continues to work without change. HTML users get the new frontend. There is no URL migration for consumers.

## 7. Service Specifications

### 7.1 `datasette` service

Shrinks from its current form. Responsibilities narrow to serving data only.

- **Keeps:** `Dockerfile`, `scripts/download_from_s3.py`, `entrypoint.sh`, `metadata.json` (as authoritative data metadata — facets, sort, column descriptions, canned queries), the `--cors` flag, read-only mode.
- **Deletes:** `templates/` (all of it), `static/` (all of it), UI plugins (`developers_page.py`, `status_page.py`, `sources_page.py`, `string_manager.py`, `template_filters.py`). Self-hosted fonts also move to frontend.
- **Keeps as plugins:** `datasette-search-all` (used by cross-database search API), any FTS-enabling plugins, `datasette-matomo` (if analytics still wanted — though it may move to frontend).
- **Exposure:** internal only. Remove the `ports:` mapping from compose; Caddy reaches it over the Docker network.
- **Healthcheck:** `GET /-/versions.json` returns 200.
- **Startup:** S3 download of databases as today. Typical 10–30s boot window.

### 7.2 `frontend` service

New. Owns all HTML, CSS, JS, fonts, and UI logic.

- **Stack:** FastAPI + Jinja2 (for parity with existing Jinja templates), `httpx` for internal calls to the datasette service, `uv` for dependency management, `black`-formatted code.
- **Routes (target set, corresponds to existing URL structure):**
  - `/` — homepage (hero, stats, database cards)
  - `/{db}` — database overview (tables, row counts, schema link, SQL examples)
  - `/{db}/{table}` — table browse (paginated rows, facets, export links, inline query form)
  - `/{db}/{table}/{pk}` — single row view
  - `/-/search` — cross-database full-text search UI (calls datasette API)
  - `/developers` — developer portal (static content + a few live metadata queries)
  - `/status` — system status and changelog
  - `/sources` — data source attribution
  - `/about`, `/how-to-use` — static pages
  - `/llms.txt` — machine-readable description
- **Data access:** all via internal HTTP to `http://datasette:8001/...json`. No direct SQLite reads from the frontend. This preserves the "Datasette is the only thing that touches databases" discipline.
- **Caching:** in-memory TTL cache (seconds to minutes) on metadata endpoints. Row-level queries are not cached.
- **Templates:** `_header.html`, `_footer.html`, `base.html`, plus per-page templates. Per-database customisation via Jinja conditionals or `templates/database/{db_name}.html` overrides when they exist.
- **Assets:** Inter + JetBrains Mono (self-hosted `woff2`), single `zeeker.css` using CSS custom properties, small `zeeker.js`.

### 7.3 `caddy` service

Off-the-shelf Caddy image. One Caddyfile with the suffix routing rules above. Volume for auto-provisioned TLS certificates. Publishes `80:80` and `443:443`.

## 8. Data Flow

1. **Boot:** `datasette` downloads `.db` files from `s3://bucket/latest/` and optionally per-database metadata from `s3://bucket/assets/databases/{db}/`. Health check flips to healthy.
2. **Boot (frontend):** `frontend` starts. If the per-database UI overlay pattern is retained (see §9), it also pulls overlay templates/CSS from S3. Otherwise static assets are baked into the image.
3. **Request (HTML):** browser → Caddy → frontend. Frontend renders a Jinja template, which may call `datasette:8001/{db}/{table}.json?_size=...&_facet=...` one or more times for data. Response returned to browser.
4. **Request (API):** browser/script → Caddy → datasette. Byte-identical response to today.
5. **Refresh:** `zeeker deploy` (existing command) pushes a new `.db` to S3. `zeeker-refresh-cron.sh` runs the existing refresh script, which hash-checks and restarts the datasette service only if something changed. Frontend does not restart; it just sees fresh data on its next API call.

## 9. Impact on the zeeker Workspace

The `houfu/zeeker` uv workspace remains the home of CLI + deployment. Changes below.

| Package | Before | After |
|---|---|---|
| `packages/zeeker/` | CLI for init/add/build/deploy/assets | Unchanged for data commands. `zeeker assets generate` emits frontend-shaped overlays instead of Datasette-shaped ones. |
| `packages/zeeker-common/` | Shared utilities | Unchanged. |
| `packages/zeeker-datasette/` | Docker image with templates, static, UI plugins, and data scripts | Shrinks to `Dockerfile`, `metadata.json`, `scripts/`, `entrypoint.sh`. Templates, static, and UI plugins deleted. |
| `packages/zeeker-frontend/` | — | **New.** FastAPI + Jinja app, Dockerfile, templates, static, fonts. |
| `packages/zeeker-proxy/` or root `Caddyfile` | — | **New.** Caddy config. No package needed; a single Caddyfile at the repo root is sufficient. |

**Per-database UI overlays (optional simplification):** today, `zeeker assets generate/deploy` ships per-database CSS and templates to S3 so the Datasette container can hot-reload them. In the new frontend, per-database customisation is naturally expressed as Jinja conditionals or template overrides inside the repo. The S3 overlay mechanism can be retained for parity or retired for simplicity — this is a follow-up decision, not a blocker for the refactor.

## 10. Migration Plan

Each step is independently deployable. The site is never fully down; pages that haven't been ported yet fall back to the legacy Datasette HTML.

**Step 1 — Dual-service bring-up (no routing change).**
Add `frontend` and `caddy` services to `docker-compose.yml`. Frontend serves a placeholder `/frontend-test` route. Caddy is configured but routes everything to datasette as today. Verify locally. Deploy.

**Step 2 — Flip suffix-based routing.**
Update Caddyfile to route `*.json`, `*.csv`, `*.db`, `/-/*` → datasette and everything else → frontend. Frontend 404s on HTML routes because they don't exist yet. **Do not deploy yet** — test locally with `curl` against both `.json` and `.html` URLs to prove the contract.

**Step 3 — Port pages incrementally.**
Implement frontend routes one at a time, in order of user value: `/` → `/{db}` → `/{db}/{table}` → `/{db}/{table}/{pk}` → `/developers` → `/status` → `/sources` → static pages. Each port includes: handler, Jinja template, visual check against current design brief. Deploy after each (or batch of) pages.

**Step 4 — Remove datasette UI plugins.**
Once the corresponding frontend routes are live, delete `developers_page.py`, `status_page.py`, `sources_page.py` from the datasette service. Rebuild the datasette image. Deploy.

**Step 5 — Prune templates and static from zeeker-datasette.**
Delete `templates/`, `static/`, and now-orphaned plugin files from `packages/zeeker-datasette/`. The package becomes data-only.

**Step 6 — Decide on asset overlay retention.**
Evaluate whether `zeeker assets generate/deploy` should retarget to the frontend, or be retired. Make the call after 1–2 months of running the new architecture.

## 11. Risks and Open Questions

**R1 — Facet JSON parity.** Datasette's faceted browse produces HTML with embedded facet counts. The frontend must call `/{db}/{table}.json?_facet=col` and render counts itself. Risk: some facet edge cases (array columns, m2m) may need extra API calls. *Mitigation:* confirm with `curl` against a few tables before starting Step 3.

**R2 — Query UI.** Datasette's `/-/sql` HTML page with query editor, param binding, and canned query forms is non-trivial. The frontend needs a thin replacement. *Mitigation:* first version can be a `<textarea>` that POSTs to `/-/sql?format=json` and renders results as a table. Editor polish is a follow-up.

**R3 — Streaming CSV.** Large table CSV export streams from Datasette. Since the frontend doesn't touch `.csv` URLs (they route straight to datasette), this is preserved automatically. No risk — flagged only for verification.

**R4 — Cross-database search.** `/-/search` today uses `datasette-search-all`. Decision needed: does the frontend call that plugin's JSON output, or re-implement search by fanning out to each database's FTS? *Recommendation:* call the plugin's JSON output in v1 to avoid re-implementation.

**R5 — Per-database overlays (open question).** Retain the S3 overlay mechanism for the frontend, or retire it? Retain preserves the "deploy UI without rebuilding container" workflow; retire simplifies the system. *Decision deferred to Step 6.*

**R6 — Matomo analytics.** `datasette-matomo` injects tracking into Datasette HTML. If the frontend renders all HTML, Matomo moves to the frontend as a simple `<script>` include. Datasette's Matomo plugin can be removed.

**R7 — Time cost against project ROI.** Per the alt-counsel "When Institutions Enter Your Space" post, the project's continuation is itself in question. *Mitigation:* this PRD targets minimum viable change. Step 1 and Step 3's first page (`/`) together deliver >50% of the perceived "UI fix" in under a weekend of work, before committing to the full migration.

## 12. Success Criteria

- **API parity:** `diff` of `curl -s https://data.zeeker.sg/sglawwatch/headlines.json` before and after migration shows no meaningful changes (timestamps and Datasette version strings excepted).
- **UI consistency:** homepage, database page, table page, and row page share a single design language (V2 editorial, Inter + JetBrains Mono, CSS custom properties). No 2025/2026 footer mismatch. No `# (sglawwatch)` headings. No row data leaking into column labels.
- **Container simplicity:** `packages/zeeker-datasette/` contains no `templates/`, no `static/`, and zero UI plugins. `docker compose config` shows three services; only Caddy exposes ports.
- **Zero URL migrations for consumers:** any third-party script using the current API keeps working without change.
- **Plugin count reduction:** from 5+ UI-coupled plugins to 0 in the datasette service.

## 13. Out of Scope / Deferred

- Authentication or private databases.
- A full SQL editor with syntax highlighting (v1 uses a plain `<textarea>`).
- API versioning (`/v1/`, `/v2/`).
- A hosted SaaS version for others to deploy their own.
- Replacing Datasette entirely.

---

## Appendix A — Decision log

| # | Decision | Rationale |
|---|---|---|
| 1 | Keep Datasette as API backend, not rewrite | Re-implementing `.json`/`.csv`/`-/sql` is high-risk, low-value; the API is what works |
| 2 | Suffix-based routing over path-based | Preserves API URLs byte-for-byte; no per-database config |
| 3 | FastAPI + Jinja for frontend | Minimal stack, Python-native, reuses Jinja knowledge from existing templates |
| 4 | Caddy over nginx/Traefik | Simplest config for this scale; auto-TLS |
| 5 | Frontend accesses data via HTTP, not direct SQLite | Maintains "Datasette owns the database" discipline; makes frontend stateless |
| 6 | Incremental migration with fallback | De-risks a project already in "should I continue?" territory |

## Appendix B — What this PRD explicitly does not touch

- `fetch_data()` implementations in any data project
- `zeeker.toml` schema
- S3 bucket layout (`latest/`, `assets/databases/`, `archives/`)
- Refresh cron mechanics
- The data scraping projects that feed this system
