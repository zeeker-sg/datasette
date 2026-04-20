# Requirements

> Synthesized from `prd-zeeker-frontend-split.md` via `/gsd-ingest-docs` on 2026-04-20. Each requirement traces to PRD source sections and a milestone phase. M1 (Editorial polish) predates this REQUIREMENTS.md and was scoped from sketch findings, not formal requirements.

## Milestone M2 — Frontend / API Split

### REQ-api-byte-parity — API contract preservation
**Source:** PRD §3, §6, §12
**Description:** Every `.json`, `.csv`, `.db`, and `/-/*` URL under `data.zeeker.sg` returns identical bytes before and after the refactor (timestamps and Datasette version strings excepted).
**Acceptance:** `diff` of `curl -s https://data.zeeker.sg/sglawwatch/headlines.json` pre and post migration shows no meaningful changes.
**Phase:** verified at every phase boundary; primary gate at Phase 03 (suffix-routing flip) and Phase 04 (first deploy with frontend HTML).

### REQ-suffix-routing-contract — Caddy URL routing
**Source:** PRD §6, Appendix A #2
**Description:** Caddy reverse proxy routes by URL suffix: `*.json`, `*.csv`, `*.db`, `/-/*` → datasette; everything else → frontend. Suffix matching only — no path-prefix routing.
**Acceptance:** local `curl` against both `.json` and HTML URLs proves both paths reach the correct backend.
**Phase:** Phase 03.

### REQ-eliminate-template-drift — Single HTML codebase
**Source:** PRD §3
**Description:** A single frontend codebase owns all HTML — no V1/V2 template drift, no two-eras-co-existing.
**Acceptance:** homepage, database page, table page, and row page share a single design language; no `# (sglawwatch)` heading bug; no row-data-leaking-into-column-labels bug; no 2025/2026 footer year mismatch.
**Phase:** Phases 04–06 (covered as each route ports).

### REQ-escape-datasette-template-surface — No more Datasette template overrides
**Source:** PRD §3, §7.1
**Description:** Frontend must not depend on Datasette's `database.html`/`table.html` template overrides or `app.css` specificity workarounds.
**Acceptance:** `packages/zeeker-datasette/` contains no `templates/` directory and no `static/` directory.
**Phase:** Phase 07.

### REQ-preserve-zeeker-cli — CLI investment preservation
**Source:** PRD §3, §9, Appendix B
**Description:** `zeeker init` / `add` / `build` / `deploy` and the S3 deployment pipeline continue to work unchanged. `zeeker.toml` schema, S3 bucket layout (`latest/`, `assets/databases/`, `archives/`), and refresh cron mechanics are not modified.
**Acceptance:** end-to-end `zeeker deploy` of a new database still produces a queryable result on the live site, with no CLI changes required by the consumer.
**Phase:** Verified at Phase 02 (initial split) and again at Phase 07 (after pruning).

### REQ-incremental-migration — No big-bang cutover
**Source:** PRD §3, §10
**Description:** Migration proceeds in independently-deployable steps; the site never goes fully down; un-ported pages fall back to the legacy Datasette HTML during the transition window.
**Acceptance:** each phase (02–08) is deployable on its own without breaking existing URLs.
**Phase:** Architectural property; verified at every deploy.

### REQ-reduce-plugin-count — Drop UI-coupled plugins
**Source:** PRD §3, §12, §7.1
**Description:** UI-only Datasette plugins are deleted, not ported. Datasette service ends with 0 UI-coupled plugins.
**Acceptance:** `developers_page.py`, `status_page.py`, `sources_page.py`, `string_manager.py`, `template_filters.py` removed from `packages/zeeker-datasette/`.
**Phase:** Phase 07.

### REQ-frontend-route-set — Frontend coverage
**Source:** PRD §7.2
**Description:** Frontend FastAPI service serves `/`, `/{db}`, `/{db}/{table}`, `/{db}/{table}/{pk}`, `/-/search`, `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`.
**Acceptance:** every route returns 200 with rendered HTML for at least one valid input.
**Phase:** Coverage builds across Phases 04 (`/`, `/{db}`), 05 (table + row), and 06 (auxiliary).

### REQ-frontend-data-via-http — Datasette owns the database
**Source:** PRD §7.2, Appendix A #5
**Description:** Frontend reads data exclusively via internal HTTP to `http://datasette:8001/...json`. No direct SQLite access from frontend.
**Acceptance:** frontend container has no SQLite client and no volume mount of `./data`.
**Phase:** Phase 02 (architectural; verified at every later phase).

### REQ-internal-only-datasette-exposure — Network isolation
**Source:** PRD §7.1, §7.3
**Description:** Datasette service is internal-only; only Caddy publishes `:80`/`:443`.
**Acceptance:** `docker compose config` shows datasette has no `ports:` mapping; only Caddy exposes ports.
**Phase:** Phase 02.

---

## References

- Source PRD: `prd-zeeker-frontend-split.md`
- Synthesis: `.planning/intel/SYNTHESIS.md`
- Decisions (DEC-1..DEC-6, all `Locked: false`): `.planning/intel/decisions.md`
- Constraints (CON-routing-table, CON-frontend-stack, CON-datasette-shrink, CON-healthcheck, CON-immutable-zeeker-surface): `.planning/intel/constraints.md`
- Context, risks (R1–R7): `.planning/intel/context.md`
- Conflict report (resolved by user as framing (b)): `.planning/INGEST-CONFLICTS.md`
- Datasette template constraints (existing): `.planning/notes/datasette-styling-limits.md`
