# Roadmap

## Milestone M1: Editorial polish

Transform the V2 light-theme shell into a civic-broadsheet editorial UI. Grounded in four sketch sessions; all design decisions pre-validated and captured in the `sketch-findings-zeeker-datasette` skill.

### Phases

#### Phase 1 — Implement editorial shell + home + inventory lists

**Goal:** Apply the validated sketch-findings design across the base templates so every page inherits the civic-broadsheet chrome, and the three most-visited surfaces (home, database, table) render in their winning editorial patterns.

**Scope — in:**
- Theme system: update `static/css/zeeker-base.css` with the paper/petrol/ochre/terracotta palette, Fraunces/Inter/Mono typography scale, and spacing/radius tokens from `references/theme-system.md`.
- Shell & chrome: `templates/_header.html`, `templates/_footer.html`, hero pattern, breadcrumb strip, petrol stat band, sticky toolbar. Fix the footer `a:link` specificity override against Datasette's `app.css`.
- Home (`templates/index.html`): sketch 001-D — dark nav + warm hero + stat band + card grid with rotating accent borders + dark CTA.
- Database page (`templates/database.html`): sketch 002-B — editorial full-width rows listing tables (no taxonomy).
- Table page as news feed (`templates/_table-{db}-{table}.html` per long-text table): sketch 004-A — reverse-chron feed cards + faceted sidebar, using the `_table-{db}-{table}.html` partial seam so Datasette's filters/facets/FTS/pagination/export stay intact.

**Scope — out:**
- Row detail page (sketch 003) — defer, no winner yet.
- Data Guide footer block (About / Licence / Source / Suggested Uses).
- Dark `petrol-ink` theme activation (defined but not wired).
- Mobile-only pass beyond the default responsive collapses already in sketches.

**Success criteria:**
- All four winning sketches render as production templates against the real databases (SG Government Newsrooms + Zeeker-Judgements + Sglawwatch).
- No regressions in existing Datasette functionality: filters, facets, FTS search, sort links, pagination, CSV/JSON export, advanced export pane all still work on `/{db}/{table}` pages.
- Visual QA sweep (`scripts/visual_qa.py`) returns all 200s across desktop + mobile and Chromium + WebKit.
- Footer links visible at proper contrast on every page.
- Italic-accent H1 with colored `<em>` visible on home / database / table pages.

**Plans:** 6 plans

Plans:
- [ ] 01-01-theme-and-tokens-PLAN.md — Replace :root tokens + body/heading/link base styles with civic-broadsheet palette + Fraunces/Inter/Mono typography + italic-accent-on-h1 signature.
- [ ] 01-02-shared-chrome-PLAN.md — Rewrite `_header.html` (dark nav + breadcrumb) and `_footer.html` (4-column paper footer); append SHELL CHROME CSS section with `.db-nav` / `.db-crumb` / `.db-header` / `.db-statband` / `.db-toolbar` / `.cta` / `.cat-pill` / `.fts-badge` / `.site-footer` classes.
- [ ] 01-03-home-editorial-PLAN.md — Rewrite `templates/index.html` as sketch 001-D (warm hero + petrol stat band + `№ 01 · Databases` card grid with rotating accent borders + `№ 02 · How to use` + dark CTA); append HOME CSS section with `.cards` / `.card` + nth-child accent rotation / `.chip` / `.how-grid` / `.hero-search`.
- [ ] 01-04-database-editorial-rows-PLAN.md — Rewrite `templates/database.html` as sketch 002-B (hero + stat band + editorial-row table list with mono columns + right-aligned row counts + FTS badge); append DATABASE EDITORIAL ROWS CSS. Preserves today's `metadata.get('tables', {}).get(name)` fix and `_zeeker_*` hidden-table filter.
- [ ] 01-05-table-feed-partials-PLAN.md — Create `templates/_partials/feed_card.html` + four `_table-{db}-{table}.html` partials (acra_news, judiciary_news, judgments, about_singapore_law) so long-text tables render as sketch 004-A feed cards. Uses Datasette's partial seam so filters/facets/FTS/pagination/export are untouched. Append FEED CARDS CSS.
- [ ] 01-06-visual-qa-sweep-PLAN.md — Extend `scripts/visual_qa.py` with three production content-type routes; run sweep; human checkpoint on contact sheet to confirm all 200s and no regressions.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 01-01 | — | yes |
| 2 | 01-02 | depends on 01-01 | yes |
| 3 | 01-03 | depends on 01-01 + 01-02 | yes |
| 4 | 01-04 | depends on 01-03 (CSS file chain) | yes |
| 5 | 01-05 | depends on 01-04 (CSS file chain) | yes |
| 6 | 01-06 | depends on 01-01..01-05 | no (human checkpoint) |

Note: Plans 03/04/05 all append to `static/css/zeeker-base.css`; they run sequentially to avoid file conflict rather than in parallel.

**References:**
- Skill: `sketch-findings-zeeker-datasette` (auto-loads)
- Sources: `.claude/skills/sketch-findings-zeeker-datasette/sources/`
- Constraints: `.planning/notes/datasette-styling-limits.md`

---

## Milestone M2: Frontend / API Split

Split `data.zeeker.sg` into a read-only Datasette API + a FastAPI/Jinja frontend behind a Caddy suffix-routing proxy. Preserve API byte-for-byte, eliminate Datasette template-override debt, reduce UI-coupled plugins to zero. Supersedes M1's strategy of patching the Datasette template surface — M1's V2 templates and editorial CSS become reference material harvested by M2 phases that re-implement them in FastAPI/Jinja.

Driven by `prd-zeeker-frontend-split.md` (PRD, Status: Draft) ingested via `/gsd-ingest-docs` on 2026-04-20. PRD-level decisions (DEC-1..DEC-6 in `.planning/intel/decisions.md`) are not yet ratified ADRs — promote to `Status: Accepted` ADRs to lock them.

### Phases

#### Phase 2: Dual-service bring-up

**Goal:** Add `frontend` (FastAPI placeholder) and `caddy` (off-the-shelf) services to `docker-compose.yml`. Caddy still routes everything to datasette; frontend serves a single `/frontend-test` route. Site behavior unchanged.

**Scope — in:**
- New `packages/zeeker-frontend/` package (FastAPI + Jinja2 + httpx + uv, black-formatted) with placeholder route.
- New root `Caddyfile` (transparent proxy → datasette only).
- `docker-compose.yml` updated: 3 services (datasette, frontend, caddy); only Caddy publishes ports.
- Datasette service `ports:` mapping removed (internal-only, network-reachable from Caddy).

**Success criteria:**
- `docker compose up` brings all 3 services healthy.
- All existing URLs (`/`, `/{db}`, `*.json`, `/-/sql`, etc.) still resolve byte-for-byte through Caddy → datasette.
- `GET /frontend-test` returns 200 from the new frontend service.
- Datasette healthcheck (`/-/versions.json`) returns 200 over the internal Docker network.

**Plans:** 5 plans

Plans:
- [x] 02-01-PLAN.md — Wave-0 validation infrastructure: capture_baseline.sh, verify_api_parity.sh, verify_phase_02.sh, and committed pre-mutation baselines in .planning/baselines/phase-02/.
- [x] 02-02-PLAN.md — Scaffold packages/zeeker-frontend/ (FastAPI placeholder, uv-managed, pinned deps, Dockerfile with no sqlite, pytest smoke tests).
- [x] 02-03-PLAN.md — Author root Caddyfile: single site on :80, reverse_proxy zeeker-datasette:8001, auto_https off, admin bound to localhost:2019, Phase-3 forward-compat commented.
- [x] 02-04-PLAN.md — Mutate docker-compose.yml into three-service topology: remove datasette ports, add frontend + caddy services, caddy depends_on service_healthy for both backends, named volumes for cert storage.
- [x] 02-05-PLAN.md — Local bring-up + verify_phase_02.sh + verify_api_parity.sh; human checkpoint with ship/no-ship decision; finalize 02-VALIDATION.md.

**Status:** SHIPPED 2026-04-21. All 5 plans complete; topology change ships zero behavioral regressions. Parity drifts triaged (host base URL, S3 metadata refresh, datasette 0.65.1→0.65.2, daily import drift) — all environmental/non-topology. See `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` for details.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 02-01 | — (sequential prereqs; includes human checkpoint after baseline capture) | no (checkpoint) |
| 2 | 02-02, 02-03 | parallel (no files_modified overlap: packages/zeeker-frontend/** vs Caddyfile) | yes |
| 3 | 02-04 | depends on 02-02 (build.context) + 02-03 (Caddyfile) | yes |
| 4 | 02-05 | depends on 02-01 (scripts + baselines) + 02-04 (compose ready) | no (human checkpoint) |

**References:** PRD §10 Step 1, §7.1, §7.3.

---

#### Phase 3: Flip suffix-based routing

**Goal:** Update Caddyfile so `*.json`, `*.csv`, `*.db`, `/-/*` route to datasette and everything else routes to frontend. Frontend will 404 on HTML routes that aren't ported yet — this is intentional and tested locally before deploy.

**Scope — in:**
- Caddyfile suffix-router (`@datasette { path *.json *.csv *.db /-/* }` + default to frontend).
- Local `curl` parity tests: every existing `.json`/`.csv`/`.db`/`/-/*` URL returns identical bytes to pre-flip baseline.
- Test plan documented for repeatable post-flip verification.

**Success criteria:**
- `diff` of curl-captured `.json` responses (timestamps and version strings excepted) shows no meaningful changes pre vs post flip.
- HTML routes that aren't yet ported return 404 from frontend (NOT silent fallthrough to datasette HTML).

**Out:** Production deploy. Phase 3 is local-validation-only; deploy waits for Phase 4's homepage port so HTML users see the new look.

**Plans:** 4 plans

Plans:
- [x] 03-01-PLAN.md — Parameterize scripts/capture_baseline.sh + scripts/verify_api_parity.sh via ZEEKER_BASELINE_DIR env var (default phase-03-pre); smoke-test parity against current pre-flip stack.
- [x] 03-02-PLAN.md — Replace transparent reverse_proxy in Caddyfile with named @datasette matcher (path *.json *.csv *.db + path /-/*) + matched-handler + catch-all reverse_proxy frontend:8000; validate with caddy validate; single-file commit (rollback = git revert).
- [x] 03-03-PLAN.md — Author scripts/verify_phase_03.sh: positive routing + negative routing with body-content fallthrough sniff for zeeker-base.css + frontend reachability + edge cases (multi-dot, HEAD/GET, case-insensitivity, CORS) + parity wrap; delegates to verify_phase_02.sh for topology invariants. NOT executed against live stack in this plan.
- [x] 03-04-PLAN.md — docker compose restart caddy + wait healthy + run verify_phase_03.sh + standalone verify_api_parity.sh against phase-03-pre; capture forensic logs (bringup-log + parity-log); author 03-TEST-PLAN.md repeatable recipe; HUMAN CHECKPOINT for ship/no-ship using Phase-2 four-category triage (A/B/C/D); on ship → update STATE/ROADMAP/REQUIREMENTS atomically; on no-ship → git revert Plan-02 + restart caddy + verify rollback via verify_phase_02.sh.

**Status:** SHIPPED 2026-04-21. Suffix routing live; 11/11 negative + 7/7 positive routing checks pass; 12/12 byte-parity baselines clean. Also retired `verify_phase_02.sh` stale checks #3 (EXPOSE-only port jq filter) and #10 (polarity-inverted post-Phase-3). See `.planning/phases/03-flip-suffix-based-routing/03-04-SUMMARY.md`.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 03-01 | — (sequential prereq for parity baseline pointer) | yes |
| 2 | 03-02 | depends on 03-01 (uses parameterized parity script downstream) | yes |
| 3 | 03-03 | depends on 03-01 (script param prerequisite); parallel-safe with 03-02 (no files_modified overlap: scripts/verify_phase_03.sh vs Caddyfile) | yes |
| 4 | 03-04 | depends on 03-02 + 03-03 (needs both Caddyfile flip and verifier in place) | no (human checkpoint) |

**Depends on:** Phase 2.
**References:** PRD §10 Step 2, §6.

---

#### Phase 4: Port home + database pages

**Goal:** Implement frontend routes `/` (homepage with hero, stats, database cards) and `/{db}` (database overview with tables, row counts, schema link, SQL examples). Deploy together with the suffix-routing flip from Phase 3.

**Scope — in:**
- Frontend handlers + Jinja templates for `/` and `/{db}`.
- Internal HTTP calls to `http://datasette:8001/...json` for live data; in-memory TTL cache on metadata endpoints.
- Harvest M1 V2 designs: `templates/index.html` (sketch 001-D) and `templates/database.html` (sketch 002-B) as visual reference.
- Self-hosted Inter + JetBrains Mono moved to frontend; `static/css/zeeker-base.css` ported as `zeeker.css`.
- Production deploy.

**Success criteria:**
- `https://data.zeeker.sg/` and `https://data.zeeker.sg/{db}` render the V2 editorial design from the frontend service.
- All `.json` API URLs continue to return identical bytes (REQ-api-byte-parity holds).
- No 2025/2026 footer year mismatch.

**Depends on:** Phase 3 (routing must be flipped before deploy).
**References:** PRD §10 Step 3 (first tranche), §7.2.

> Per PRD §11 R7, **Phases 2 + 4 together deliver >50% of the perceived UI fix**. Subsequent phases (5–8) are optional continuation if project ROI justifies the work.

**Requirements:** REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http

**Plans:** 5 plans

Plans:
- [x] 04-01-PLAN.md — Scaffold main.py lifespan/mount plumbing + filters.py (3 Jinja filters + s/plural helpers) + datasette_client.py (httpx wrapper + 60s TTL cache on /-/metadata.json) + base.html shell (combines M1 _header+_footer) + pytest-httpx dev dep + fixtures + unit tests.
- [x] 04-02-PLAN.md — Harvest CSS from M1 zeeker-base.css (lines 1-163 + 164-350 + 3160-3862 + 4097-4116 = ~2,300 lines) into packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css; copy 3 woff2 fonts (Inter + JetBrains Mono + Fraunces); structural validation (balanced braces, no undefined var tokens, no Phase-5 leak).
- [x] 04-03-PLAN.md — Implement GET / (home) — routes_home.py handler + index.html port (with Jinja binding replacements for default: prefix, s()/plural() stubs, tables_count field fix, wildcard `*` metadata filter) + 5 MockTransport route tests.
- [x] 04-04-PLAN.md — Implement GET /{db} (database) — routes_database.py handler + database.html port + hidden-table filter using `t["hidden"]` flag (covers `_zeeker_*` AND FTS internals via single predicate) + 7 MockTransport route tests including the load-bearing FTS-not-leaked assertion.
- [x] 04-05-PLAN.md — Author scripts/verify_phase_04.sh (inherits verify_phase_03.sh + adds structural HTML + CSS/font + hidden-filter assertions) + docker-compose.prod.yml (minimal Caddy overlay) + Caddyfile.prod (data.zeeker.sg site block with auto-HTTPS + Phase-3 suffix matcher preserved) + 04-05-DEPLOY.md runbook (deploy + four-category A/B/C/D triage + three-layer rollback) + HUMAN CHECKPOINT for production deploy ship/no-ship decision.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 04-01 | — (foundational scaffolding) | yes |
| 2 | 04-02 | depends on 04-01 (base.html references /static/css/zeeker.css) | yes |
| 3 | 04-03 | depends on 04-01 + 04-02; edits main.py | yes |
| 4 | 04-04 | depends on 04-03 (serialized to avoid main.py merge race) | yes |
| 5 | 04-05 | depends on 04-03 + 04-04; production deploy + human checkpoint | no (checkpoint) |

Note: originally planned Wave 3 as parallel 04-03 + 04-04, but both append `include_router` to `main.py` — serialized to avoid worktree merge conflict risk. Adds ~5 min wall time; buys merge safety.

---

#### Phase 5: Port table browse + row view

**Goal:** Implement frontend routes `/{db}/{table}` (paginated rows, facets, export links, inline query form) and `/{db}/{table}/{pk}` (single row view).

**Scope — in:**
- Frontend handlers + Jinja templates for table and row pages.
- Faceted browse via calls to `/{db}/{table}.json?_facet=col` (validate edge cases: array columns, m2m — see PRD R1).
- Harvest M1 sketch 004-A feed-card design and the row-reading layouts.
- Pagination, sort, FTS query forwarding to datasette JSON.

**Success criteria:**
- Table page renders with working facets, pagination, sort, FTS, and export links (CSV/JSON download links route directly to datasette).
- Row page renders single-record view consistent with M1 row-reading layouts.

**Depends on:** Phase 4.
**References:** PRD §10 Step 3 (second tranche), §7.2, R1.

**Requirements:** REQ-frontend-route-set, REQ-frontend-data-via-http, REQ-api-byte-parity, REQ-eliminate-template-drift

**Plans:** 5 plans

Plans:
- [x] 05-01-PLAN.md — Foundation: extend datasette_client.py with fetch_table + fetch_row + querystring allowlist; new urls.py module (port datasette path_with_*_args + tilde_encode + row_url helpers); register Jinja globals + both new routers in main.py up-front (avoids 05-02/05-03 main.py merge race); Wave 0 fixtures (headlines_table, about_singapore_law_table, headlines_row, judgments_row) + extended conftest + 22+ unit tests + stub routes_table.py / routes_row.py with hidden-table prefix+suffix guard active.
- [x] 05-02-PLAN.md — GET /{db}/{table}: full handler (fetch_table allowlist consumer, next_url Pitfall-2 rewrite, Cache-Control, 503/404 contracts) + table.html mode-dispatch shell + 6 partials (table_feed.html sketch 004-A, table_tabular.html sketch 002-B / D-04 default, table_longform_list.html, facet_sidebar.html, applied_facets.html, pagination.html) + 18+ ASGI integration tests (feed mode, tabular fallback, facets, applied chips, pagination relative-href, export-direct D-05, hidden-table 404, FTS no-results, rowid-PK fallback, Cache-Control, italic-H1).
- [x] 05-03-PLAN.md — GET /{db}/{table}/{pk}: full handler with row_mode dispatch (article/judgment/longform/tabular), pk_label truncation to 12 chars + ellipsis, 3-segment breadcrumb + row.html shell + 4 row partials (row_article.html sketch 003-A magazine, row_judgment.html sketch 003-B broadsheet with .dateline + .tag-chip + .coda, row_longform.html article-without-aside, row_tabular.html with native <details>/<summary> long-text expand for >200-char fields) + 15+ ASGI integration tests across all 4 row_modes.
- [x] 05-04-PLAN.md — Append /* === TABLE BROWSE + ROW VIEW — phase 05 === */ section to zeeker.css (~390 lines: 121 direct M1 harvest for .va-feed/.va-item; ~270 newly authored from sketch references for .feed-layout, .facets, .filter-chip, .pagination, .data-table, .article-grid + .article-body Fraunces opsz 11 + drop cap, .aside, .dateline + .tag-chip + .coda double-rule, .row-dl + .row-dd-long). Insert before existing FOOTER LINK OVERRIDE block — preserves WARN-05 cascade tail. NO new design tokens. (completed 2026-04-25)
- [x] 05-05-PLAN.md — metadata.json display.* hints for 11 in-scope tables (sglawwatch.headlines feed/article, sglawwatch.about_singapore_law longform-list/longform, Zeeker-Judgements.judgments tabular/judgment, 8 sg-gov-newsrooms.*_news feed/article); scripts/verify_phase_05.sh authored mirroring verify_phase_04.sh (sections A-O: feed mode, tabular fallback, facets, applied chip, pagination relative href, FTS, sort, export direct via Caddy, row article + tabular, hidden-table 404 at table+row routes, Phase-6 boundary asserts for 8 routes, API parity wrap); 05-DEPLOY-NOTES.md captures three-option deploy decision matrix; HUMAN CHECKPOINT runs verifier + four-category triage + ship-or-no-ship.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 05-01 | — (foundation: urls.py + datasette_client extension + main.py wiring + Wave 0 tests + stub routers) | yes |
| 2 | 05-02, 05-03, 05-04 | parallel-safe (no files_modified overlap; main.py edit was lifted into 05-01 to serialize) | yes (yes, yes) |
| 3 | 05-05 | depends on 05-02 + 05-03 + 05-04 (verifier needs templates + CSS + handlers in place); production deploy decision human checkpoint | no (checkpoint) |

Note: main.py shared edit between 05-02 and 05-03 was factored into Plan 05-01 (option (a) from plan_split_recommendation) so 05-02 and 05-03 are file-disjoint and parallel-safe in Wave 2. Plan 05-04 (CSS append) is also Wave-2 parallel-safe — only zeeker.css is modified, which 05-02/05-03 do not touch.

---

#### Phase 6: Port auxiliary pages

**Goal:** Implement remaining frontend HTML routes — `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/robots.txt` (1:1 ports of M1 plugin pages) plus two new user-facing surfaces: `/search` (cross-database FTS UI fanning out via `asyncio.gather(return_exceptions=True)` over a boot-time-discovered FTS table cache, replacing M1's `/-/search`) and `/sql` + `/sql/{db}` (thin SQL editor with `<textarea>` POST → `execute_sql` against Datasette's read-only mode + 3s ms_limit + 1000-row cap, with canned-queries listing from `/-/metadata.json`). Caddy `/-/*` matcher remains untouched per D-01/D-02 — Datasette's native `/-/search` and `/-/sql` stay reachable as developer-facing surfaces. After Phase 6, every public HTML surface on `data.zeeker.sg` is rendered by the frontend service.

**Scope — in:**
- Frontend handlers + Jinja templates for all 9 surfaces (`/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/search`, `/sql`, `/sql/{db}`) + `/robots.txt` static.
- New `datasette_client.py` helpers: `discover_searchable_tables` (one-shot at lifespan boot — cache lives on `app.state.searchable_tables`), `search_table`, `execute_sql` (handles HTTP-400-with-body per RESEARCH Pitfall 1).
- New `changelog.py` module loading `data/changelog.yaml` (port from M1 `plugins/strings.yaml recent_updates`).
- Append-only Phase-6 CSS section in `zeeker.css` (body-class scoped: `.page-developers`, `.page-status`, `.page-sources`, `.page-about`, `.page-how-to-use`, `.page-search`, `.page-sql`, `.page-sql-db`); NO new design tokens.
- `pyyaml>=6.0,<7.0` added to `packages/zeeker-frontend/pyproject.toml` (RESEARCH Pitfall 12).
- `base.html` one-line edits: `<body class="{{ page_class or '' }}">` binding + nav `Search` link re-pointed from `/-/search` to `/search` (D-01).
- New `scripts/verify_phase_06.sh` extending Phase 4 verifier; flips Phase-5 boundary asserts (aux routes 404 → 200 + civic-broadsheet body); negative-asserts `/-/search` and `/-/sql` STILL reach Datasette via Caddy (D-01); wraps `verify_api_parity.sh` against `phase-03-pre/` baseline.

**Scope — out:**
- Inline query form on `/{db}/{table}` page (D-10 keeps Phase 5 D-06 deferred — `/sql/{db}` is the single SQL surface).
- Cross-database SQL JOINs (Datasette doesn't support them; v1 is per-db only).
- `/-/search` redirect to `/search` (would require Caddyfile carve-out; contradicts D-01).
- SQL syntax highlighting (PRD Appendix B; D-09 keeps deferred).
- Recent / popular searches on empty `/search` (Discretion default: omit; no telemetry).
- A11y audit pass on auxiliary pages (Phase 8 follow-up).
- Production deploy decision (lives at the verifier checkpoint or Phase 7 prep, not in this phase).

**Success criteria:**
- All 9 user-facing routes (`/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/search`, `/sql`, `/sql/{db}`) plus `/robots.txt` return 200 with rendered HTML/text per Content-Type.
- Italic-accent `<em>` H1 on every aux page; civic-broadsheet shell inherited from `base.html`; `/static/css/zeeker.css` referenced (no `zeeker-base.css` leak).
- `/search?q=...` fans out across `app.state.searchable_tables`; partial failure (one mocked-fail table) does NOT empty results; reflected XSS on `q` echoed in response body is HTML-escaped (`<script>` → no raw `<script>` in body).
- `/sql/{db}` POST executes via `execute_sql`; 400 errors render as inline `.sql-error` block (HTTP 200, NOT 503); truncated=true renders banner with CSV deep-link routed direct via Caddy suffix; param-binding via `_param_<name>=<value>` URL keys (NOT string concat); querystring allowlist drops every form field outside `sql` + `_sql_param_<valid_name>`.
- `/llms.txt` returns `Content-Type: text/plain; charset=utf-8`; body starts with `# data.zeeker.sg`; `_zeeker_*` tables filtered out.
- Hidden-table dual predicate (`t.get("hidden") or t.get("name", "").startswith("_zeeker")`) applied on `/sources`, `/developers`, `/llms.txt`, and `/sql/{db}` canned-queries listing (D-15).
- `Cache-Control: public, max-age=60, stale-while-revalidate=300` on every aux GET; `Cache-Control: no-store` on POST `/sql/{db}`.
- main.py router order: `home_router → aux_router → search_router → sql_router → database_router → table_router → row_router` (Phase-6 routers all precede the catch-all `/{db}` per RESEARCH Pitfall 3).
- `bash scripts/verify_phase_06.sh` exits 0; `bash scripts/verify_api_parity.sh` (against `phase-03-pre/`) exits 0.
- All Phase 4-5 + new Phase-6 unit tests green; no regressions.

**Depends on:** Phase 5.
**References:** PRD §10 Step 3 (remainder), §7.2, R2, R4.

**Requirements:** REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http, REQ-api-byte-parity

**Plans:** 6 plans

Plans:
- [x] 06-01-PLAN.md — Wave-0 scaffolding: declare `pyyaml>=6.0,<7.0` in `packages/zeeker-frontend/pyproject.toml`; port M1 `plugins/strings.yaml recent_updates` block verbatim into `packages/zeeker-frontend/src/zeeker_frontend/data/changelog.yaml`; create 4 test fixtures (`searchable_databases.json`, `headlines_search_results.json`, `metadata_with_canned_queries.json`, `sql_error_400.json`); author 5 collectable test stub files (test_routes_aux, test_routes_search, test_routes_sql, test_datasette_client_phase06, test_changelog) — every test pytest.skips with the implementing plan number cited. Wave 0 BLOCKING for all subsequent plans. SHIPPED 2026-04-26 (`6f57d73`, `8794947`, `c3e9b0f`).
- [ ] 06-02-PLAN.md — Extend `datasette_client.py` with `discover_searchable_tables` (uses live-verified `fts_table` field; applies dual hidden+_zeeker filter), `search_table`, `execute_sql` (handles HTTP-400-with-body BEFORE raise_for_status — Pitfall 1; `_param_<name>` URL binding, NEVER string concat); create `changelog.py` module (yaml.safe_load only; degrades to empty list on missing/invalid file); extend `main.py` lifespan to populate `app.state.searchable_tables` (via `await discover_searchable_tables`) and `app.state.changelog` (via `load_changelog()`); fill in 9 unit tests in test_datasette_client_phase06.py + 4 in test_changelog.py.
- [ ] 06-03-PLAN.md — Author `routes_aux.py` with 7 GET handlers (`/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/robots.txt`); 5 HTML templates + 1 .txt template (port M1 `templates/pages/*` 1:1 with `{% extends "base.html" %}`, `{% block nav/footer %}` includes DROPPED, italic-accent H1 hard-coded per UI-SPEC §Copywriting Contract, `/-/metadata` link in about.html re-pointed to `/developers`, `/-/search` references in how-to-use.html re-pointed to `/search`); copy `templates/pages/robots.txt` verbatim into `static/robots.txt`; register `aux_router` in main.py BEFORE `database_router`; 9 integration tests including 503-on-upstream-error + Cache-Control coverage + `_zeeker_` leak negative.
- [ ] 06-04-PLAN.md — Author `routes_search.py` (GET /search with State A empty-q + State B fan-out via `asyncio.gather(*tasks, return_exceptions=True)` — NEVER TaskGroup per RESEARCH Pitfall 2; `_safe_search_one` converts httpx.HTTPError + ValueError to None sentinel; 503 when empty cache + non-empty q per Pitfall 10; results grouped by (db, table) alphabetically with count + top-10 + see-all link); `templates/pages/search.html` (two-state) + `templates/_partials/search_result.html`; register `search_router` in main.py after `aux_router` and before `database_router`; 6 integration tests including the load-bearing partial-failure-tolerance + Reflected-XSS-via-q-echo + 503-empty-cache + State-A-renders-when-cache-empty assertions.
- [ ] 06-05-PLAN.md — Author `routes_sql.py` (GET /sql landing, GET /sql/{db} editor, POST /sql/{db} execution); `_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")` + `_detect_params` dedup + querystring allowlist (only `sql` + `_shape=objects` + `_param_<name>` for detected params reach upstream — RESEARCH Pitfall 7); POST handler renders 400-with-body as inline `.sql-error` block (HTTP 200, NOT 503 — Pitfall 1); truncation banner + URL-encoded export anchors `/{db}.csv?sql=...` + `/{db}.json?sql=...` route via Caddy suffix; `templates/pages/sql_landing.html` + `sql_db.html` (with canned-queries `<details>` block + textarea + results/error/truncation states); register `sql_router` in main.py after `search_router` and before `database_router`; Cache-Control: no-store on POST; 10 integration tests including SQL-injection-via-param-binding-prevention + querystring-smuggling-allowlist + 400-handled-as-200 + truncation-banner + export-link-URL-encoding assertions.
- [ ] 06-06-PLAN.md — Append Phase-6 CSS section to `zeeker.css` BEFORE the FOOTER LINK OVERRIDE block; harvest from M1 `static/css/zeeker-base.css` lines 700-2900 per UI-SPEC §CSS Harvest with token substitution (M1 `--color-bg-surface` → frontend `--color-surface`, etc.); body-class-scoped (`.page-developers .api-table`, etc.); NO `:root` edits, NO new tokens; brace balance preserved. base.html one-line edits: `<body class="{{ page_class or '' }}">` binding + `href="/-/search"` → `href="/search"`. Author `scripts/verify_phase_06.sh` (delegates to verify_phase_04.sh; flips Phase-5 boundary asserts; positive structural asserts on every aux route — italic H1 + zeeker.css link + no _zeeker_ leak; D-01 negative asserts that `/-/search` + `/-/sql` STILL reach Datasette; main.py router-order line-number invariant; wraps verify_api_parity.sh against phase-03-pre baseline). Phase-6 ready for HUMAN UAT.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 0 | 06-01 | — (Wave-0 scaffolding: deps + fixtures + test stubs; BLOCKING) | yes |
| 1 | 06-02, 06-03 | parallel-safe (file-disjoint: 06-02 owns datasette_client.py + changelog.py + main.py lifespan; 06-03 owns routes_aux.py + aux templates + robots.txt + main.py router include for aux_router); both depend on 06-01 | yes (yes) |
| 2 | 06-04, 06-05 | parallel-safe (file-disjoint: 06-04 owns routes_search.py + search.html + search partial; 06-05 owns routes_sql.py + sql_landing.html + sql_db.html); both depend on 06-02 (need datasette_client extensions + app.state.searchable_tables); each adds its own include_router line in main.py — file-shared but line-disjoint, low merge risk | yes (yes) |
| 3 | 06-06 | depends on 06-03 + 06-04 + 06-05 (verifier asserts every Phase-6 route 200 + structural; CSS append + base.html nav re-point; main.py router-order audit) | yes |

Note: Plans 06-02 and 06-03 both touch `main.py`, but 06-02 edits the lifespan block and 06-03 adds an `include_router(aux_router)` line — disjoint regions of the file. Likewise 06-04 and 06-05 each add one `include_router(...)` line. Merge-safe in practice; if a worktree merge race surfaces, the affected plan re-applies its single-line edit. No need to serialize.

---

#### Phase 7: Prune zeeker-datasette

**Goal:** Delete UI-coupled plugins and template/static directories from `packages/zeeker-datasette/`. The package becomes data-only: `Dockerfile`, `metadata.json`, `scripts/`, `entrypoint.sh`.

**Scope — in:**
- Delete `developers_page.py`, `status_page.py`, `sources_page.py`, `string_manager.py`, `template_filters.py`.
- Delete `templates/` (all of it) and `static/` (all of it) from `packages/zeeker-datasette/`.
- Rebuild datasette image, deploy.

**Success criteria:**
- `packages/zeeker-datasette/` contains 0 UI plugins, no `templates/`, no `static/`.
- All HTML routes still render correctly (frontend owns them now).
- All API routes still return identical bytes.

**Depends on:** Phase 6 (all HTML routes must be live in frontend before pruning).
**References:** PRD §10 Steps 4 + 5, §7.1, §12.

---

#### Phase 8: Overlay decision + Matomo migration

**Goal:** Resolve the deferred per-database overlay question (PRD R5) and migrate Matomo analytics from datasette plugin to frontend `<script>` include (PRD R6).

**Scope — in:**
- Decide: retain S3 overlay mechanism for frontend (preserves "deploy UI without rebuilding container" workflow) vs retire (simpler system). Document decision as ADR.
- Move Matomo to frontend; remove `datasette-matomo` plugin from datasette service.
- Update `zeeker assets generate` if overlay mechanism is retained.

**Success criteria:**
- Matomo analytics functioning from frontend.
- Overlay decision documented; if retained, `zeeker assets generate` produces frontend-shaped overlays.

**Depends on:** Phase 7.
**References:** PRD §10 Step 6, §9, R5, R6.

---

### Cross-Milestone Notes

- **Critical path is short:** PRD §11 R7 calls out project-ROI uncertainty. Phases 2 + 4 alone deliver the bulk of the user-facing UI fix in roughly a weekend; everything beyond is optional follow-through.
- **Out-of-scope fences (PRD Appendix B):** This milestone does NOT modify `fetch_data()`, `zeeker.toml`, S3 bucket layout, refresh cron, or the data-scraping projects.
- **Decision lock state:** PRD Appendix A's 6 architectural choices (DEC-1..DEC-6) are PRD-level proposals, not ratified ADRs. Promote to `docs/adr/0001-suffix-routing.md` etc. with `Status: Accepted` to lock them before phases that depend on them ship.

**References:**
- Source PRD: `prd-zeeker-frontend-split.md`
- Synthesis entry: `.planning/intel/SYNTHESIS.md`
- Requirements: `.planning/REQUIREMENTS.md`
- Per-type intel: `.planning/intel/{decisions,requirements,constraints,context}.md`
- Conflicts report (resolved): `.planning/INGEST-CONFLICTS.md`
- Datasette template constraints (existing): `.planning/notes/datasette-styling-limits.md`
