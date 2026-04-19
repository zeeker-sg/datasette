---
phase: 01-editorial-shell-home-inventory
plan: 06
subsystem: qa
tags:
  - qa
  - regression
  - playwright
  - visual-sweep
  - contact-sheet
  - human-checkpoint
  - operator-deferral

# Dependency graph
requires:
  - 01-01-theme-and-tokens
  - 01-02-shared-chrome
  - 01-03-home-editorial
  - 01-04-database-editorial-rows
  - 01-05-table-feed-partials
provides:
  - "`scripts/visual_qa.py` ROUTES list extended from 14 to 17 entries — adds one representative URL per production content type (`/SG-Government-Newsrooms/acra_news`, `/Zeeker-Judgements/judgments`, `/Sglawwatch/about_singapore_law`) so the sweep now covers all four sketch-findings patterns (shell chrome / home editorial / database editorial rows / table feed-cards)"
  - "Visual QA contact sheet at `tmp/qa/index.html` capturing 68 screenshots (17 routes × 2 browsers × 2 viewports) as of 2026-04-19 — evidence of cross-browser visual correctness + HTTP status for every instrumented route"
  - "Documented two-tier verification outcome: shell chrome + fixtures (always-on) vs production-data (operator-gated)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-tier visual QA: tier-1 always-on sweep against fixtures server (12 fixtures routes + 5 shell pages) — tier-2 operator-gated sweep against production-data server (3 content-type routes) once S3-backed DBs are attached"
    - "Sweep artifacts under `tmp/qa/` are .gitignored (`/tmp/` line in .gitignore) — the contact sheet + PNGs are evidence, not tracked code"
    - "Single-list ROUTES constant keeps the script invariant across environments — fixtures-only or production-only runs both produce a full sweep, with per-route HTTP status identifying coverage gaps visually (s404 = route not wired, s500 = template regression)"

key-files:
  created:
    - ".planning/phases/01-editorial-shell-home-inventory/01-06-visual-qa-sweep-SUMMARY.md"
  modified:
    - "scripts/visual_qa.py"

key-decisions:
  - "Sweep run was executed against `http://127.0.0.1:8002` (fixtures-only dev server, started with `--plugins-dir plugins`) rather than the user's existing `:8001` server which is `_memory`-only — :8001 with only the ephemeral memory DB cannot exercise `/fixtures` nor any production route, so it would yield 13 s404s instead of 12"
  - "Production content-type routes (`acra_news` / `judgments` / `about_singapore_law`) were added to ROUTES even though they 404 in this environment — the plan's intent is a script that is READY to sweep production the moment operator starts a prod-data-attached server; shipping the routes in the script now prevents a future churn of 'add the routes again'"
  - "Task 2's six functional-regression curl checks were run against BASE=http://127.0.0.1:8001 (the only running server at that moment) and recorded as 404/FAIL — NOT hidden, NOT skipped, NOT mocked. Per the plan's explicit environment_context (two-tier verification), these are deferred-pending-operator-attention rather than a fail gate. The operator must restart a prod-data server and rerun Task 2 for acceptance"
  - "Discovered a live regression on `/fixtures` (4× s500 in the contact sheet): `templates/database.html` line 22 calls `rejectattr('name','match','^_zeeker.*')` — the `match` Jinja test is Ansible-specific, not present in vanilla Jinja2 nor in any of the project's plugin filters. This is a bug introduced by Plan 01-04 ('canonical Jinja filter chain'). The bug does NOT affect `_memory` (no tables → `rejectattr` never iterates → no `match` call). It fires on every database page with ≥1 non-hidden table — i.e., every real prod database. Documented for operator as a blocker-level checkpoint finding; not self-fixed because `database.html` is outside this plan's `files_modified` scope"
  - "Skipped running a second sweep against `:8001` — the additional sweep would yield 17 s404s (everything, because `_memory` has no matching path for anything), no incremental signal, only wasted Playwright time"
  - "Did NOT commit `tmp/qa/*` — artifacts are excluded via `.gitignore` line `/tmp/` (root-level `tmp/` directory matches). The SUMMARY references paths but the files are local-only evidence for operator review"

patterns-established:
  - "When the plan's `files_modified` list constrains scope and a pre-existing bug in an out-of-scope file blocks a must-have success criterion, surface it as a checkpoint finding — do NOT self-fix (respects plan boundaries) and do NOT hide it (operator needs the signal)"
  - "When production-data verification is operator-gated, record the actual `404`/`000`/`FAIL` outcomes against whatever server IS reachable rather than omitting the section — audit trail > clean green report"
  - "Running the sweep with `--plugins-dir plugins` matching the user's dev-server invocation is mandatory — missing it produces 500s on every non-home page (plugin filters like `pluralize`, `safe_format`, `s()` helper all fail under StrictUndefined)"

requirements-completed:
  - SC-01-visual-qa-green  # partial — 52/68 green; 12 s404 on unreachable prod routes (deferred), 4 s500 on /fixtures (regression — operator-decided)
  - SC-01-footer-contrast-check  # footer a:link override confirmed in CSS tail (last 20 lines of zeeker-base.css); contact sheet cells show paper-colored footers on every page
  - SC-01-fixtures-still-works  # NOT MET — /fixtures returns 500. Documented in Deviations section as a regression finding, awaiting operator decision
  - SC-01-no-regressions  # NOT MET — /fixtures 500 is a regression from before 01-04. Operator gates closure
  - SC-01-functional-regression  # DEFERRED — Task 2's six curl checks all returned 404 because `SG-Government-Newsrooms` DB is not attached to any running server. Requires operator-started prod server

# Metrics
duration: ~20min
completed: 2026-04-19
---

# Phase 1 Plan 06: Visual QA Sweep Summary

**Extended `scripts/visual_qa.py` ROUTES from 14 to 17 entries covering one representative URL per production content type (news / judgments / legal-guides). Ran the Playwright sweep against `http://127.0.0.1:8002` (fixtures-only dev server) producing `tmp/qa/index.html` with 52 s200 / 12 s404 (expected — production DBs not attached) / 4 s500 (REGRESSION on `/fixtures` — Jinja `match` test undefined, introduced by 01-04 `templates/database.html` line 22). Ran the six Task 2 functional-regression curls against `http://127.0.0.1:8001`; all returned 404 because no server in this environment has the `SG-Government-Newsrooms` database attached. Per the plan's environment_context, these are operator-gated deferrals, not auto-fixes — handed to the human checkpoint with explicit next-action commands.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3 completed (Task 1 edit + commit, Task 2 functional curl recording, Task 3 sweep run + contact sheet) + human checkpoint pending
- **Files modified:** 1 (`scripts/visual_qa.py`, +4 lines)
- **Files created:** 1 (this SUMMARY)
- **Artifacts created (gitignored):** 72 PNGs under `tmp/qa/{chromium,webkit}/{desktop,mobile}/` + 1 contact sheet `tmp/qa/index.html` (17568 bytes)

## Task Commits

1. **Task 1: Add three production content-type routes to scripts/visual_qa.py ROUTES** — `ab35354` (feat)
2. **Task 2: Run functional-regression curl checks** — no repo mutation (results recorded below)
3. **Task 3: Run the Playwright sweep and generate the contact sheet** — no repo mutation (artifacts under `tmp/qa/`, .gitignored)

_Plan metadata commit will be made at the end of this plan._

## Task 1 — Script Extension (committed)

`scripts/visual_qa.py` ROUTES list extended from 14 to 17 entries. New entries appended after the existing `query-sql` tuple:

```python
# Production content-type coverage (phase 01 editorial patterns)
("table-news-feed", "/SG-Government-Newsrooms/acra_news"),
("table-judgments", "/Zeeker-Judgements/judgments"),
("table-legal-guides", "/Sglawwatch/about_singapore_law"),
```

**Automated verifier:** `grep -q 'table-news-feed' … && python3 -c "ast.parse(open(...).read())"` → PASS. All existing 14 routes preserved in order. AST still parses under Python 3.12.

**Slug uniqueness check:** `table-news-feed`, `table-judgments`, `table-legal-guides` do not collide with any existing slug in the list (existing: `home / about / how-to-use / sources / status / developers / search-all / database / table-facetable / table-searchable-fts / table-sortable / table-roadside / row-view / query-sql`).

## Task 2 — Functional Regression Curl Checks (BLK-06)

**Server used:** `BASE=http://127.0.0.1:8001` (the running dev server in the user's shell session).

**Database attachment on `:8001`:** `_memory` only (confirmed via `curl -s http://localhost:8001/-/databases.json` → `[{"name":"_memory",...}]`). Neither `SG-Government-Newsrooms` nor any production DB is attached. Per the plan's `<environment_context>` block, production-data verification requires an operator-started server with the S3-backed databases attached.

| # | Check | Command | Expected | Actual | Verdict |
|---|-------|---------|----------|--------|---------|
| 1 | FTS search | `curl -s "$BASE/SG-Government-Newsrooms/acra_news?_search=budget" -o /dev/null -w '%{http_code}'` | `200` | `404` | **deferred — DB not attached** |
| 2 | Pagination size | `curl -s "$BASE/SG-Government-Newsrooms/acra_news?_size=10" -o /dev/null -w '%{http_code}'` | `200` | `404` | **deferred — DB not attached** |
| 3 | CSV export | `curl -s -o /dev/null -w '%{http_code}' "$BASE/SG-Government-Newsrooms/acra_news.csv"` | `200` | `404` | **deferred — DB not attached** |
| 4 | JSON export | `curl -s -o /dev/null -w '%{http_code}' "$BASE/SG-Government-Newsrooms/acra_news.json?_shape=array"` | `200` | `404` | **deferred — DB not attached** |
| 5 | Sort direction diff | `md5(DESC)` vs `md5(ASC)` on `?_sort_desc=published_date` vs `?_sort=published_date` | differ | both = `638e7738495576d59ab00d18417d1c38` (identical 404 page) | **deferred — DB not attached** |
| 6 | Facets present | `curl -s "$BASE/…/acra_news" \| grep -q 'class="facets"' \|\| grep -q 'facet'` | match | 0 matches | **deferred — DB not attached** |

All six checks returned **404** or the 404-page sentinel because the target database is not attached to any running server in this environment. These are NOT regression signals — they are operator-attention deferrals per the plan's explicit two-tier verification approach.

**Operator action to complete Task 2:** start a dev server with production DBs attached (see Operator Next-Actions section below), then re-run the six commands above. If any of the six return a non-200 status once the DB is present, that is the signal of a template regression in `_table-SG-Government-Newsrooms-acra_news.html` or the shared `_partials/feed_card.html`.

## Task 3 — Playwright Sweep (contact sheet)

**Server used:** `http://127.0.0.1:8002` (fixtures-only dev server started during this plan's execution).

**Exact command to start the sweep server (executor invoked):**
```bash
uv run datasette serve data/fixtures.db \
  -m metadata.json \
  --template-dir templates \
  --static static:static \
  --plugins-dir plugins \
  --cors \
  --port 8002
```

(Note: `--plugins-dir plugins` is MANDATORY. Without it, the `s()` template helper from `plugins/string_manager.py` raises `UndefinedError: 's' is undefined` on every page that uses it — i.e., every page.)

**Exact sweep command:**
```bash
uv run python scripts/visual_qa.py --base-url http://127.0.0.1:8002 --out tmp/qa
```

**Sweep result summary:**

| Status | Count | Routes |
|--------|-------|--------|
| `s200` | 52 | home, about, how-to-use, sources, status, developers, search-all, table-facetable, table-searchable-fts, table-sortable, table-roadside, row-view, query-sql (13 routes × 4 combos) |
| `s404` | 12 | table-news-feed, table-judgments, table-legal-guides (3 routes × 4 combos — **expected**; production DBs not attached to `:8002`) |
| `s500` | 4 | **database (`/fixtures`) × 4 combos — REGRESSION, see Deviations** |
| **Total** | **68** | 17 routes × 2 browsers × 2 viewports (chromium/webkit × desktop/mobile) |

Sum 52 + 12 + 4 = 68 ✓ matches 17 routes × 4 combos ✓.

**Contact sheet location:** `tmp/qa/index.html` (17568 bytes).

**INFO-03 acceptance check:** expected `s200 ≥ route-count × 4 = 68` — **NOT MET** (52 < 68). The deficit (16) splits as 12 expected-production-404 + 4 unexpected-`/fixtures`-500.

**stdout from sweep run:** every route printed a status code (no `ERR:` lines — no timeouts, no load failures, no network errors). The 404s and 500s are the target servers' authoritative responses, not client-side faults.

**Sample contact sheet grep:**
```bash
$ python3 -c "
html = open('tmp/qa/index.html').read()
print('s200 total:', html.count(\"class='status s200'\"))
print('s404 total:', html.count(\"class='status s404'\"))
print('s500 total:', html.count(\"class='status s500'\"))
"
s200 total: 52
s404 total: 12
s500 total: 4
```

## Deviations from Plan

### Rule 4 — Architectural / Scope Finding: `/fixtures` returns 500 (pre-existing regression from 01-04)

- **Found during:** Task 3 sweep run
- **Issue:** `/fixtures` returns HTTP 500 on all 4 browser/viewport combinations. The error body reads `No test named 'match'.` — Jinja2 does not register a `match` regex test. The offending line is `templates/database.html:22`:

  ```jinja
  {% set vt = tables|selectattr('hidden','ne',true)|rejectattr('name','match','^_zeeker.*')|list %}
  ```

  `match` is an Ansible-specific Jinja extension; it is NOT part of vanilla Jinja2 and is NOT registered by any of the project's plugins (`plugins/template_filters.py` adds `pluralize / safe_format / safe_int / filesizeformat` — no `match` test).
- **Why did it pass before?** The bug was introduced by Plan 01-04 (commit `b3e3bda` — "rewrite database.html as sketch 002-B editorial rows"). It does NOT fire on `_memory` (the `tables` list is empty, so `rejectattr` never iterates, so the `match` test is never evaluated). The user's `:8001` dev server runs with `_memory` only, which is why the regression slipped through 01-04's verification. This sweep, run against a server with a real DB (`fixtures`), is the first execution that actually exercises the broken filter.
- **Why NOT self-fixed:** `templates/database.html` is outside this plan's `files_modified` list (only `scripts/visual_qa.py` is in scope). Per the plan's success criteria: "No modifications to STATE.md, ROADMAP.md, or files outside the plan's `files_modified` list." Self-fixing would violate scope boundaries.
- **Impact:** Every real production database page (`/SG-Government-Newsrooms`, `/Zeeker-Judgements`, `/Sglawwatch`) will return 500 until this is fixed. This blocks must-have truth #3 from Plan 01-06: "`/fixtures` still returns 200 (today's `metadata.get('tables', {}).get(name)` fix intact)".
- **Proposed fix (for a follow-up plan):** replace the `|match` test with one of:
  1. `|rejectattr('name','startswith','_zeeker')` — fastest fix, passes the project invariant ("_zeeker_* names"), no regex needed.
  2. Register a custom `match` test via a new plugin hookimpl in `plugins/template_filters.py` (`@hookimpl def prepare_jinja2_environment(env): env.tests['match'] = lambda v, p: re.match(p, v) is not None`).
  3. Use a different Jinja construct: `|reject('equalto','_zeeker_schemas')|reject('equalto','_zeeker_updates')|…` — explicit, but couples to the list of known hidden tables.

  Option 1 is the minimum-diff, most defensive fix.
- **Alternative — consider patching in this plan:** the plan's `files_modified: [scripts/visual_qa.py]` is restrictive, but option 1 is a 1-line change to `templates/database.html` that fixes a must-have success criterion. The operator may direct either a scope expansion here or a new micro-plan (01-07?). Flagged as `[Rule 4 — architectural / scope escalation]`.

### Operator-gated deferral: Task 2 functional-regression curls

- **Found during:** Task 2 execution
- **Issue:** All 6 curls returned 404 because no running server in this environment has `SG-Government-Newsrooms` attached.
- **Why NOT self-fixed:** Spinning up a prod-data server requires S3 credentials and the `S3_BUCKET` env var (see `entrypoint.sh`) — operator responsibility, not executor responsibility, per `<environment_context>`.
- **Deferral documented:** see Operator Next-Actions section below.

## Authentication Gates

None. No S3 credentials accessed. No new API keys. No auth boundaries crossed.

## Known Stubs

None in the files modified by this plan. (The sweep discovered stub-adjacent issues in 01-04's output — see Deviations — but those are scope-external.)

## Threat Flags

None. `scripts/visual_qa.py` only performs read-only HTTP GETs via Playwright against a local dev server. No new network surface, no auth path, no file access pattern, no schema change.

## Self-Check: PASSED

- `.planning/phases/01-editorial-shell-home-inventory/01-06-visual-qa-sweep-SUMMARY.md` — FOUND (this file)
- `scripts/visual_qa.py` — FOUND (modified, +4 lines, 17 routes confirmed via AST)
- `tmp/qa/index.html` — FOUND (contact sheet, 17568 bytes)
- `tmp/qa/chromium/desktop/*.png` — FOUND (18 files including leftovers from prior runs)
- `tmp/qa/webkit/mobile/*.png` — FOUND (18 files)
- Commit `ab35354` (Task 1) — FOUND in git log: `feat(01-06): add production content-type routes to visual QA sweep`

## Operator Next-Actions (Checkpoint Preparation)

The plan has `autonomous: false` and a `checkpoint:human-verify` gate. Before approval/decision, the operator should perform:

### 1. Open the contact sheet in a browser
```bash
open /Users/houfu/Projects/zeeker-datasette/tmp/qa/index.html
```
Expected: 17 route sections, 4 cells per section, green `200` badges on 13 routes × 4 combos, red `404` badges on 3 routes × 4 combos (`table-news-feed`, `table-judgments`, `table-legal-guides`), red `500` badges on 4 cells for route `database` (/fixtures).

### 2. (Optional — for full production coverage) Start a server with S3-backed DBs attached
```bash
# Requires AWS credentials and S3_BUCKET env var
export S3_BUCKET=<your-zeeker-bucket>
./entrypoint.sh    # downloads *.db files from S3 and starts Datasette on :8001

# Then re-run the sweep against it:
uv run python scripts/visual_qa.py --base-url http://localhost:8001 --out tmp/qa-prod
open tmp/qa-prod/index.html
```
Expected after that: the three `table-news-feed / table-judgments / table-legal-guides` routes should flip from s404 to s200 (assuming the partials from 01-05 render correctly — which is exactly what the sweep is meant to verify).

### 3. (Optional — to pass Task 2) Re-run the six functional-regression curls against the prod server
```bash
export BASE=http://localhost:8001  # the prod-data server
curl -s "$BASE/SG-Government-Newsrooms/acra_news?_search=budget" -o /dev/null -w '%{http_code}\n'
curl -s "$BASE/SG-Government-Newsrooms/acra_news?_size=10" -o /dev/null -w '%{http_code}\n'
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/SG-Government-Newsrooms/acra_news.csv"
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/SG-Government-Newsrooms/acra_news.json?_shape=array"
DESC_MD5=$(curl -s "$BASE/SG-Government-Newsrooms/acra_news?_sort_desc=published_date" | md5)
ASC_MD5=$(curl -s "$BASE/SG-Government-Newsrooms/acra_news?_sort=published_date" | md5)
[ "$DESC_MD5" != "$ASC_MD5" ] && echo "C5: PASS" || echo "C5: FAIL"
curl -s "$BASE/SG-Government-Newsrooms/acra_news" | grep -q 'facet' && echo "C6: PASS" || echo "C6: FAIL"
```
Expected: all print `200` / `PASS`. Any non-200 / FAIL indicates a regression in 01-05's `_table-SG-Government-Newsrooms-acra_news.html` partial or `_partials/feed_card.html`.

### 4. Decide on the `/fixtures` s500 regression
Three options, operator chooses:

| Option | Action | Owner | Risk |
|--------|--------|-------|------|
| **A — Expand scope of 01-06** | Executor edits `templates/database.html` line 22 to use `|rejectattr('name','startswith','_zeeker')` (minimum-diff option 1). Re-run sweep. Commit + amend SUMMARY. | Re-invoke executor with explicit scope approval | Low — 1-line change, exact problem matches canonical fix from Plan 01-04's own SUMMARY: "Filter: not hidden AND name does not match ^_zeeker.*" which `startswith` satisfies fully |
| **B — Open a micro-plan 01-07** | Create `01-07-fix-database-match-test-PLAN.md` with the 1-line fix + re-run sweep. Keeps 01-06 scope clean. | Planner | Low — small plan, but adds phase-extension overhead |
| **C — Accept and defer** | Mark regression in phase SUMMARY, defer to phase 02 as a known-issue. | Operator | High — every production database page is broken; users hit 500s immediately after deploy. Not recommended |

## Human Checkpoint Prompt

Per the plan's final `<task type="checkpoint:human-verify" gate="blocking">`:

> **Phase 01 — Plan 06 — Visual QA Sweep: operator review required.**
>
> Current sweep status (against fixtures server on :8002):
> - **52 green** (s200) on 13 shell / fixtures / about / developers / status / sources / how-to-use / query-sql / row-view / searchable-FTS / facetable / sortable / roadside + chromium-mobile + webkit-desktop + webkit-mobile combinations.
> - **12 red 404** (expected) on the 3 production content-type routes — production DBs not attached locally. Operator must attach S3 DBs and re-sweep for full coverage.
> - **4 red 500** (UNEXPECTED REGRESSION) on `/fixtures` — `templates/database.html:22` uses a `|match` Jinja test that isn't registered. Introduced by Plan 01-04. Details: Deviations section above.
>
> **Commands:**
> - Open contact sheet: `open tmp/qa/index.html`
> - Start prod-data server (optional for full prod coverage): `export S3_BUCKET=... && ./entrypoint.sh`
> - Task 2 functional rerun (after prod server up): see section 3 above.
>
> **Decision required (on the /fixtures regression):**
> - [ ] `approve` with option A (expand 01-06 scope, 1-line fix to database.html)
> - [ ] `approve` with option B (new 01-07 micro-plan)
> - [ ] `approve` with option C (accept regression, defer to phase 02)
> - [ ] `re-run` (operator wants a specific re-test)
> - [ ] `abandon` (more fundamental rework needed)
>
> **Or if approving as-is with production gaps left for a later session:** `approved — production sweep deferred to operator session`.

## Follow-up Items Noticed (Not Done — Out of Scope)

- **`/fixtures` s500 regression from 01-04** — surface-level `|match` Jinja-test missing. Scope-external to this plan; operator-decided above.
- **Leftover `database-memory.png` from prior sweep runs** — 4 stale files under `tmp/qa/{browser}/{viewport}/` (slug `database-memory` is not in current ROUTES). Harmless, not referenced by the contact sheet. Cleanup is optional; `rm tmp/qa -rf && uv run python scripts/visual_qa.py …` would remove them.
- **Task 2 did not run against a prod-data server** — the plan's acceptance criteria require 6 × 200/PASS against `SG-Government-Newsrooms/acra_news`. Operator must complete this pass.
- **Contact sheet uses single-quoted `class='status sNNN'`** — no impact on the plan, but the original AST route-count recipe in the plan ast-walked `ast.Assign` and missed the `ROUTES: list[...] = [...]` annotated assignment (which is `ast.AnnAssign`). Counted manually via `grep -cE '^\s+\('` (returns 17) instead. Non-blocking.
- **Sweep didn't capture JS errors / console warnings** — `scripts/visual_qa.py` only records HTTP status and takes a screenshot. A future enhancement could `page.on("pageerror")` to capture client-side JS exceptions (e.g., if Prism highlighting or the `ZeekerEnhancer` class throws). Not in scope here.
- **No A/B comparison against pre-phase baseline** — this is a one-shot sweep against the current state. Git-bisectable screenshots aren't in scope; each sweep overwrites the previous PNGs.

## Next Phase Readiness

- **Plan 01-07 may be needed** to address the `/fixtures` regression (operator decision above).
- **No other blockers** for phase completion — the 3 new routes in `scripts/visual_qa.py` are in place; the operator has everything needed to re-sweep once production databases are attached.
- **Phase 01 declaration of done** must NOT be signed off until the /fixtures 500 is resolved and the 3 production routes return 200.

---
*Phase: 01-editorial-shell-home-inventory*
*Completed: 2026-04-19*
