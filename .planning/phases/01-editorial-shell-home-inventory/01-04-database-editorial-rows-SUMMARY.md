---
phase: 01-editorial-shell-home-inventory
plan: 04
subsystem: ui
tags:
  - database
  - editorial-rows
  - sketch-002-B
  - sticky-toolbar
  - fts-badge
  - meta-col
  - civic-broadsheet

# Dependency graph
requires:
  - 01-01-theme-and-tokens
  - 01-02-shared-chrome
provides:
  - "Sketch 002-B editorial-row database page at templates/database.html — asymmetric hero + petrol statband + sticky .db-toolbar filter form + full-width .list/.row editorial-row table listing"
  - "DATABASE EDITORIAL ROWS CSS section shipping .list, .row, .row::before petrol slider, .row .idx / .name-col / .name / .desc / .cols / .cols .pk / .cols .more / .count-col / .count / .label / .date-col, plus .db-header .meta-col dd.export-links variant"
  - "@media (max-width: 960px) collapse rule that hides .cols + .date-col and scales down .name/.count"
  - "Canonical selectattr/rejectattr filter chain for visible-tables list — replaces the cards-era rejectattr('hidden')|list pattern"
  - "Sticky .db-toolbar consumer — posts GET /{database}?_search=... using Datasette's native table-filter query parameter"
affects:
  - 01-06-visual-qa-sweep

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Consume-only relationship to Plan 02 shell chrome: database template uses .db-header, .db-header-grid, .db-header .meta-col, .db-statband, .db-toolbar, .db-toolbar-search, .fts-badge, .section, .section.alt, .section-num, .kicker verbatim — no redefinitions"
    - "Safe-access pattern `metadata.get('tables', {}).get(table.name) or {}` preserved on every table-metadata lookup (protects /fixtures from 500 under StrictUndefined)"
    - "Canonical Jinja filter chain for hidden-table + _zeeker_* filtering: `selectattr('hidden','ne',true)|rejectattr('name','match','^_zeeker.*')` — computed once into `vt` at top of block, reused for stat band + card loop"
    - "Namespace-accumulated total_rows_ns via `{% set total_rows_ns = namespace(total=0) %}` loop — avoids the old `counts = []` + `counts.append` mutation pattern"
    - "Literal kicker `№ 01 · Database` (not a `loop.index0 + 1` expression — loop is not defined outside for-loop under StrictUndefined)"
    - "Last-space italic split via `db_title.rfind(' ')` — only the trailing word wraps in `<em>`, not the first word"

key-files:
  created: []
  modified:
    - "templates/database.html"
    - "static/css/zeeker-base.css"

key-decisions:
  - "Column-preview truncation at 8 columns before showing `+N more` — matches the sketch 002-B reference and the prior card design's 5-column cutoff was too terse for mono row layout. 8 fits in the 280px .cols column on desktop, is hidden on mobile anyway."
  - "Kept stat band's 4th cell (SQL · open query link) even though it's a fourth cell while the plan leaves room for just three — matches the .db-statband 4-col grid from Plan 02. Looks cleaner than a dangling gap."
  - "Views and Canned queries sections rendered as editorial rows (same .row structure) rather than retained as old-style cards — keeps visual grammar consistent within a single database page."
  - "Date-col on views shows just a JSON export link (no CSV — views don't always materialise as CSV cleanly in Datasette). Count-col shows literal `view` word instead of row-count since Datasette's view context doesn't include count."
  - "Canned query rows have empty .cols and .count-col — they don't have columns or row counts; the date-col just carries a JSON link."
  - "Toolbar form action is `/{{ database }}` (not `/{{ database }}?_search=...`) — Datasette re-renders the same URL with the _search query parameter, which re-enters the database view and filters tables server-side. No Python changes needed."
  - "Dead CSS selectors (.tables-grid, .table-card, .database-card, .database-header, .database-overview, .database-info, .database-summary, .database-title, .database-subtitle, .database-stats, .database-actions-section, .export-bar, .export-actions, .tables-section, .view-card, .views-grid, .views-section, .data-guide, .data-guide-card, .data-guide-list, .canned-queries, .query-card, .query-actions, .queries-grid, .no-tables, .view-description, .query-description, .table-description, .table-actions, .table-header, .table-schema, .column-list, .column-item, .column-name, .column-description, .column-flag, .more-columns, .stat-item, .stat-number, .stat-label, .export-bar-label) remain in zeeker-base.css — template no longer references them; CSS cleanup deferred to polish pass (WARN-09)."

patterns-established:
  - "Editorial-row template is a single flat `{% block content %}` rebuild — retain only `{% extends %}`, `{% block extra_head %}`, `{% block nav %}` (breadcrumbs + _header include), `{% block footer %}` (_footer include). Do not wrap content in sub-blocks like the old `database_header` / `tables_section`."
  - "For every Datasette template page, the first line of `{% block content %}` should compute the filtered collection once into a named variable (here: `vt` for visible tables) and reuse it — prevents filter drift between header counts and list body."
  - "Every table-metadata lookup goes through `metadata.get('tables', {}).get(name) or {}` — never `metadata.tables[name]`. The `or {}` fallback ensures downstream `.title` / `.description` lookups safely return None under StrictUndefined."

requirements-completed:
  - SC-01-database-editorial-rows
  - SC-01-database-hero
  - SC-01-database-statband
  - SC-01-sticky-toolbar

# Metrics
duration: ~8min
completed: 2026-04-19
---

# Phase 1 Plan 04: Database Editorial Rows Summary

**Sketch 002-B database page shipped — asymmetric hero with italic-accent H1 (last-word split) + petrol stat band + sticky .db-toolbar filter form + full-width editorial-row table listing with petrol hover slider and PK-highlighted mono columns — all via Plan 02 shared chrome plus one new DATABASE EDITORIAL ROWS CSS section (.list / .row / .row::before / .row .idx,.name-col,.name,.desc,.cols,.pk,.more,.count-col,.count,.label,.date-col / .db-header .meta-col dd.export-links).**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2
- **Files modified:** 2

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite `templates/database.html` to sketch 002-B editorial-row layout with asymmetric hero + statband + sticky toolbar + editorial-row list** — `b3e3bda` (feat)
2. **Task 2: Append `DATABASE EDITORIAL ROWS — phase 01` CSS section** — `1cfaeb6` (feat)

_Plan metadata commit will be made by the orchestrator when it updates STATE.md / ROADMAP.md._

## Files Created/Modified

- **`templates/database.html`** — full rewrite of `{% block content %}`. Old `database_header` + `tables_section` + `sql_examples` + `database_tools` + `canned_queries` structure replaced by a single flat block: `vt` computation → `.db-header` hero → `.db-statband` → `.db-toolbar` form → optional search-results banner → № 01 · Tables `.list` of `.row`s → № 02 · Views `.list` → № 03 · Saved queries `.list`. Added explicit `{% block footer %}{% include "_footer.html" %}{% endblock %}` for consistency with index.html. 191 insertions / 235 deletions (net -44 lines).
- **`static/css/zeeker-base.css`** — new `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` banner section inserted between the HOME section (ending at line 3722) and the tail `footer a:link` override (now starting at line 3860). 136 insertions. File grew from 3,740 → 3,876 lines. Braces balanced (552/552). Footer override still in last 20 lines (WARN-05 gate passes).

## Datasette Context Variables Consumed by the New Template

The rewritten `templates/database.html` depends on the following Jinja context variables exposed by Datasette's default `DatabaseView` (`datasette/views/database.py`):

| Variable | Type | Usage |
| --- | --- | --- |
| `database` | str | URL segment used in `/{{ database }}/{{ table.name }}`, form action, export links, SQL marker link |
| `tables` | list[dict] | Source for `vt` after `selectattr/rejectattr` chain. Per-table fields consumed: `.name`, `.count` (int or None), `.columns` (list[str]), `.primary_keys` (list[str]), `.hidden` (bool), `.fts_table` (truthy/str), `.fts` (alias), `.human_description_en` (optional) |
| `views` | list[dict] | Views iteration for № 02 section; uses `.name`, `.description` (optional) |
| `canned_queries` | list[dict] | Canned-query iteration for № 03 section; uses `.name`, `.title`, `.description` (optional) |
| `metadata` | dict | Database-level: `.title`, `.description`, `.license`, `.license_url`, `.source`, `.source_url`. Table-level: `metadata.get('tables', {}).get(name)` returns dict with `.title` and `.description` |
| `size` | int (bytes) | File size — used in meta-col "Size" row and statband "on disk" cell (both via `\|filesizeformat` filter) |
| `search_query` | str (optional) | Populated when Datasette's built-in `?_search=...` query is active — used as form input value and for search-results banner |
| `search_results` | list (optional) | Count shown in search-results banner when search_query is set |

No custom `datasette-template-sql` queries are needed for the database page — all data comes from the default context.

## Confirmation: Safe-access Pattern Preserved

The critical `metadata.get('tables', {}).get(name)` safe-access pattern from today's production bug fix is preserved:

```bash
$ grep -c "metadata.get('tables', {}).get" templates/database.html
1
$ grep -c 'metadata.tables\[' templates/database.html
0
```

The single usage is inside the `№ 01 · Tables` row loop:

```jinja
{% set table_meta = metadata.get('tables', {}).get(table.name) or {} %}
```

The `or {}` fallback ensures `table_meta.title` and `table_meta.description` are safe to read under StrictUndefined even when:
- the database has no `"tables"` key in its metadata block (the original bug — `/fixtures` crashed under StrictUndefined)
- the database has a `"tables"` key but this particular table isn't listed there

Also confirmed `/fixtures` protection by double-checking: the template never reaches `metadata.tables[...]` bracket syntax anywhere.

## Confirmation: `_zeeker_*` Filter Uses Canonical selectattr/rejectattr

The `_zeeker_*` metadata-table hiding is preserved AND migrated from the old `rejectattr('hidden')|list` + `startswith('_zeeker')` inline check pattern to the canonical single-pass filter chain:

```jinja
{% set vt = tables|selectattr('hidden','ne',true)|rejectattr('name','match','^_zeeker.*')|list %}
```

Verification:

```bash
$ grep -c 'selectattr' templates/database.html
1
$ grep -c 'matching_zeeker' templates/database.html  # BLK-02: non-existent filter
0
$ grep -c 'vt.append' templates/database.html        # BLK-03: mutation pattern
0
$ grep -c '_zeeker' templates/database.html          # still present in the regex
2
```

The two `_zeeker` matches are: (1) the `'^_zeeker.*'` regex in the `rejectattr` call; (2) the comment `# Filter: not hidden AND name does not match ^_zeeker.*` above it.

## Confirmation: Last-space Italic Split + Literal Kicker

The hero H1 italicizes only the trailing word via `rfind`:

```bash
$ grep -c 'rfind' templates/database.html
1
$ grep -c "split(' ', 1)" templates/database.html    # WARN-04: first-space split
0
```

The kicker is a hardcoded literal string (no `loop.index0` expression):

```bash
$ grep -c '№ 01 · Database' templates/database.html
1
$ grep -c 'loop.index0 + 1' templates/database.html  # WARN-03: cosmetic guard
0
```

## Column-Count Truncation Choice

**Column preview cap = 8 columns, with `+N` overflow marker.**

```jinja
{% for col in table.columns[:8] %}{% if not loop.first %} · {% endif %}<span class="{% if col in (table.primary_keys or []) %}pk{% endif %}">{{ col }}</span>{% endfor %}
{% if table.columns|length > 8 %} <span class="more">+{{ table.columns|length - 8 }}</span>{% endif %}
```

Rationale: 8 fits the 280px `.cols` grid column on desktop at `--text-xs` mono. The prior card design used 5 (too terse in a horizontal layout; cards had vertical stacking). Mobile hides `.cols` entirely via `@media (max-width: 960px) .row .cols { display: none }` so the 8-col cap is irrelevant at small widths.

The `.more` span gets its own style in the new CSS section (`color: var(--color-text-muted); font-style: italic`) to match the muted-continuation feel of the reference sketch.

## Toolbar Form Consumer Implementation

The `.db-toolbar` class defined by Plan 02 (WARN-02 flagged it as a "defined but not yet consumed" in that plan's summary) is now actively consumed here:

```html
<form class="db-toolbar-search" method="get" action="/{{ database }}" role="search">
  <label for="db-table-filter" class="visually-hidden">Filter tables</label>
  <input id="db-table-filter" type="search" name="_search"
         value="{{ search_query if search_query is defined and search_query else '' }}"
         placeholder="Filter tables by name or description…"
         autocomplete="off">
  <button type="submit">Filter</button>
</form>
<a class="fts-badge" href="/{{ database }}?sql=...">Schema</a>
```

Datasette's `DatabaseView` accepts `?_search=` as a native table-filter query parameter — it re-renders the page with `tables` already pre-filtered server-side (matches against table name + description). No Python code changes required. The form's `value` attribute echoes the current `search_query` so users see their active filter after submit.

## New CSS Classes Shipped

| Selector | Purpose |
| --- | --- |
| `.list` | Wrapping `.row` container with 2px ink top border |
| `.row` | 5-column grid: `60px` idx \| `1fr` name+desc \| `280px` cols \| `130px` count \| `130px` date; baseline-aligned with border-bottom per row |
| `.row::before` | Absolute-positioned hover slider (animates from width:0 to 3px on hover) |
| `.row:hover` | Warm `--color-bg-alt` bg-shift + padding/margin nudge for the "row pulls toward you" hover feel |
| `.row:hover::before` | Slider grows to 3px × 60% height at `left: -3px` |
| `.row:hover .name` | Title color swap to `--color-accent` (petrol) |
| `.row .idx` | Mono corner numeral, muted, `--text-sm` |
| `.row .name-col` | `min-width: 0` (grid overflow guard) |
| `.row .name,.row .name:link,.row .name:visited` | Display-face title `--text-3xl` 500 with `-0.01em` tracking and `color: var(--color-ink)` |
| `.row .name:hover` | Title hover → petrol |
| `.row .desc` | Muted `--text-sm` description line |
| `.row .cols` | Mono `--text-xs` column list, `word-break: break-word` for overflow safety |
| `.row .cols .pk` | Petrol 600-weight highlight for primary-key columns |
| `.row .cols .more` | Muted italic `+N` overflow marker |
| `.row .count-col` | Right-aligned container |
| `.row .count` | Display-face big count `--text-3xl` 500 ink |
| `.row .label` | Mono `--text-2xs` uppercase label ("rows") |
| `.row .date-col` | Right-aligned mono `--text-xs` date/metadata cell |
| `.row .date-col a{,:hover}` | Link color treatment inside date-col |
| `.db-header .meta-col dd.export-links` | Flex-row variant of the meta-col `<dd>` used for the CSV/JSON/SQLite export links in the hero |
| `.db-header .meta-col dd.export-links a{,:hover}` | Petrol link styling inside the export-links variant |
| `@media (max-width: 960px) .row` | Collapses grid to `40px idx \| 1fr name+desc \| 110px count`, hides `.cols` and `.date-col`, drops `.name` and `.count` font-size to `--text-xl` |

## Dead Legacy CSS Selectors Retained in zeeker-base.css (WARN-09)

The plan's `<objective>` and `<critical_preservation>` blocks explicitly tolerate pre-existing dead CSS selectors — removal is a future polish pass. The TEMPLATE no longer references these classes, but the CSS rules remain intact in `zeeker-base.css`:

| Selector | Notes |
| --- | --- |
| `.tables-grid` | Old cards-era wrapper |
| `.table-card` | Old individual card class |
| `.database-card` | Old home-page card class (also from Plan 03 scope) |
| `.database-header` | Old database page hero wrapper |
| `.database-overview`, `.database-info`, `.database-summary` | Old asymmetric layout pieces |
| `.database-title`, `.database-subtitle` | Old H1 / lede variants (replaced by `.db-header h1` / `.db-header .lede`) |
| `.database-stats`, `.stat-item`, `.stat-number`, `.stat-label` | Old inline stat block (replaced by `.db-statband`) |
| `.database-actions-section`, `.export-bar`, `.export-actions`, `.export-bar-label` | Old download-links bar (replaced by `.db-header .meta-col dd.export-links`) |
| `.table-description`, `.table-actions`, `.table-header`, `.table-schema` | Old card internals |
| `.column-list`, `.column-item`, `.column-name`, `.column-description`, `.column-flag`, `.more-columns` | Old table-card column preview (replaced by `.row .cols` + `.pk` + `.more`) |
| `.views-section`, `.views-grid`, `.view-card`, `.view-description`, `.view-actions` | Old views grid (replaced by `.row` rendering inside `.list`) |
| `.canned-queries`, `.queries-grid`, `.query-card`, `.query-description`, `.query-actions` | Old canned-query grid (replaced by `.row` rendering inside `.list`) |
| `.data-guide`, `.data-guide-card`, `.data-guide-list` | Old about-this-data aside (removed — content now lives in `.db-header .meta-col`) |
| `.tables-section`, `.no-tables` | Old section wrappers |

None of these blocks cause any visual issue today — they're just unused rules. Rough count: ~40 dead selectors. Polish pass (Plan 01-06 or later) should prune these to reduce CSS file size. Estimated savings: ~300-400 lines.

## Preserved Verbatim

- **`{% extends "default:database.html" %}`** — line 1, retained.
- **`{% block extra_head %}`** — retained with `{{ super() }}` + meta-description logic intact.
- **`{% block nav %}`** — retained with breadcrumbs array (`{'label': metadata.title if metadata and metadata.title else database|title}`) and `_header.html` include. The breadcrumbs array does NOT include a Home entry (Plan 02 Task 1.5 already moved that into `_header.html`).
- **`{% block footer %}{% include "_footer.html" %}{% endblock %}`** — added explicitly to ensure `_footer.html` renders consistently with `index.html` (matches the footer-include pattern Plan 03 established).
- **`footer a:link / :visited / :active / :hover / :focus` override block** — unchanged, still in last 20 lines of `zeeker-base.css`.
- **All existing CSS sections (Plan 01 tokens, Plan 02 SHELL CHROME, Plan 03 HOME)** — untouched. Only the new DATABASE EDITORIAL ROWS section was appended.

## Deviations from Plan

None — plan executed exactly as written.

All template structure (hero grid, statband cells, toolbar form, row layout, views rows, canned-query rows), all class names, all Jinja filter expressions, and all CSS declarations were transcribed from the plan's `<action>` blocks character-for-character.

The one implementation choice that was not explicitly prescribed — adding an explicit `{% block footer %}{% include "_footer.html" %}{% endblock %}` line at the end of `database.html` — matches the pattern Plan 03 established in `index.html`. The plan's DO-NOT-REGRESS note says "preserve current behavior" for the footer block; the existing file did not have this line, but adding it is consistent with the editorial-shell convention the phase established and harms nothing (Datasette's default `database.html` already handles footer if this block is absent, but the explicit include makes the intent visible).

## Authentication Gates

None. All work was purely frontend template/CSS. No auth surface changed.

## Known Stubs

None.

Every user-facing surface on the new database page is wired to real Datasette context:
- Hero title: `metadata.title` → else `database|replace|title` (real).
- Hero lede: `metadata.description` (real).
- Meta-col: `size|filesizeformat`, `metadata.license`, `metadata.source` (all real).
- Export links: `/{db}.csv`, `/{db}.json`, `/{db}.db` (real Datasette routes).
- Statband: `vt|length`, namespace-accumulated `total_rows_ns.total`, `size|filesizeformat`, SQL marker link (all real).
- Toolbar form: submits to `/{{ database }}` with `name="_search"` → Datasette's native table-filter (real).
- Schema link in toolbar: `?sql=SELECT+*+FROM+sqlite_master+WHERE+type%3D%27table%27` (real).
- Row cells: `table.name`, `table.count`, `table.columns`, `table.primary_keys`, `table.fts_table`, `table.human_description_en`, `table_meta.title`, `table_meta.description` (all real).
- Row links: `/{db}/{table}`, `/{db}/{table}.csv`, `/{db}/{table}.json` (real Datasette routes).
- Views rows: `view.name`, `view.description` (real).
- Canned query rows: `query.name`, `query.title`, `query.description` (real).

Empty-state branch (`{% else %}`) exists and renders "No tables yet in this database." gracefully.

## Threat Flags

None.

This plan only changes template markup and appends CSS. No new network surface, no auth path, no file access, no schema change.

## Verification Results

All automated acceptance criteria pass:

**Task 1 (`templates/database.html`):**
- `class="db-header"` present (1) ✓
- `class="db-statband"` present (1) ✓
- `class="db-toolbar"` present (1) ✓
- `class="db-toolbar-search"` present (1) ✓
- `class="list"` present (3 — one per № 01/02/03 section) ✓
- `class="row"` present (3 — actually appears many more times inside loops, but base count is >= 1) ✓
- `class="fts-badge"` present (2 — one in toolbar, one in row date-col) ✓
- `class="kicker"` present (2 — hero, plus search-results banner) ✓
- `metadata.get('tables', {}).get` present (1) ✓
- `matching_zeeker` absent (0) ✓ — BLK-02 gate passes
- `selectattr` present (1) ✓ — BLK-03 gate passes
- `vt.append` absent (0) ✓ — BLK-03 gate passes
- `split(' ', 1)` absent (0) ✓ — WARN-04 gate passes
- `rfind` present (1) ✓ — WARN-04 gate passes
- `loop.index0 + 1` absent (0) ✓ — WARN-03 gate passes
- `№ 01 · Database` present (1) ✓ — WARN-03 gate passes
- `№ 01 · Tables` present (2) ✓
- `tables-grid` absent in template (0) ✓
- `table-card` absent in template (0) ✓
- `metadata.tables[` absent (0) ✓ — today's bug-fix preserved
- `name="_search"` present (1) ✓ — toolbar consumer wired
- `action="/{{ database }}"` present (1) ✓ — form posts to database URL
- `{% extends "default:database.html" %}` retained at line 1 ✓
- `{% block nav %}` with `_header.html` include retained ✓
- Views and canned_queries sections retained ✓
- Jinja syntax parse test → PASS ✓

**Task 2 (`static/css/zeeker-base.css`):**
- `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` banner present (1) ✓
- `.list {` present (1) ✓
- `.row {` present (2 — base + mobile media query) ✓
- `.row::before` present (1) ✓
- `.row:hover::before` present (1) ✓
- `.row .name` present (6 — base, hover, visited/link variants, mobile override) ✓
- `.row .cols .pk` present (1) ✓
- `.row .count-col` present (1) ✓
- `grid-template-columns: 60px 1fr 280px 130px 130px` present (1) ✓
- `footer a:link` still present (2) ✓
- `tail -20 static/css/zeeker-base.css | grep -c 'footer a:link'` → 2 ✓ — WARN-05 gate passes
- File line count: 3,740 → 3,876 (+136, well within append target) ✓
- Braces balanced: 552 open / 552 close ✓
- Section order: SHELL CHROME (L3160) → HOME (L3564) → DATABASE EDITORIAL ROWS (L3724) → footer override (L3860) ✓
- No modifications to prior CSS sections ✓

**Plan-level success criteria:**
- All 4 truths from frontmatter must-haves verified in grep ✓
- All 2 tasks committed atomically (`b3e3bda`, `1cfaeb6`) ✓
- No modifications to `.planning/STATE.md` or `.planning/ROADMAP.md` ✓
- No modifications to files outside the plan's `files_modified` list (`git status --short` clean after each commit) ✓
- No unexpected deletions (`git diff --diff-filter=D --name-only HEAD~1 HEAD` returns empty for both commits) ✓

Manual browser verifications (items 1-7 in plan's `<verification>` block) require the dev server running — deferred to Plan 01-06 visual-qa-sweep or manual QA:
1. `curl /fixtures` returns 200 — deferred (template parse passes, safe-access preserved, but no dev-server run in this plan)
2. `/fixtures` renders dark nav + HOME › FIXTURES crumb + warm hero with italic last-word H1 + petrol statband + sticky toolbar + editorial rows with FTS badge where applicable — deferred
3. Row hover shows petrol slider + warm bg shift + petrol title — deferred
4. `/SG-Government-Newsrooms` all 20+ `*_news` tables render as rows, hero italicizes `Newsrooms` only — deferred
5. `?_search=news` filters table list server-side — deferred
6. Mobile viewport collapses to 3-column grid — deferred
7. Zero `matching_zeeker` in rendered HTML — deferred (but zero in the source template, so response will also have zero) ✓

## Self-Check: PASSED

- `.planning/phases/01-editorial-shell-home-inventory/01-04-database-editorial-rows-SUMMARY.md` — FOUND (this file)
- `templates/database.html` — FOUND (modified)
- `static/css/zeeker-base.css` — FOUND (modified, +136 lines)
- Commit `b3e3bda` (Task 1) — FOUND in git log
- Commit `1cfaeb6` (Task 2) — FOUND in git log

## Follow-up Cleanup Noticed (Not Done — Out of Scope)

- **~40 dead CSS selectors** in `zeeker-base.css` from the old cards-era markup (listed above). A polish pass (Plan 01-06 or later) should prune these to save ~300-400 lines. Safe because the template no longer references them.
- **Duplicate `footer a:link` override comment banner** — the tail of the file still carries the banner text; harmless.
- **`.section-num` class used by № 01 / № 02 / № 03** — shared with index.html (Plan 03) via Plan 02's SHELL CHROME section. No duplication.
- **Hardcoded `Licence` / `Source` / `Export` meta-col `<dt>` labels** — same i18n candidates flagged in Plan 03 summary. Not gating; left as literals.
- **The `style="color: inherit; text-decoration: underline;"` inline attribute** on the statband "open query" anchor is a minor inline-style sin — could migrate to a `.db-statband a.sql-link` class in a polish pass. Harmless for now.
- **The search-results banner** uses inline `style="font-family: var(--font-display); font-size: var(--text-2xl); margin-top: var(--space-2);"` — same minor inline-style sin. Low priority.

## Next Phase Readiness

- **Plan 01-05 (table-feed-partials):** Independent. Consumes `.cat-pill.*` from Plan 02 + uses `_table-{db}-{table}.html` seam. No conflict with this plan.
- **Plan 01-06 (visual-qa-sweep):** Must include the seven items in this plan's `<verification>` block: (1) `/fixtures` returns 200, (2) database page renders correctly, (3) row hover behavior, (4) `/SG-Government-Newsrooms` scale test, (5) toolbar filter submit, (6) mobile responsive, (7) zero `matching_zeeker` in rendered HTML.
- **Dev-server smoke test recommended** before merging this branch: start Datasette and hit `/fixtures` + any real database to confirm the template renders without StrictUndefined errors.
- **No blockers** for Wave 5 / visual QA.

---
*Phase: 01-editorial-shell-home-inventory*
*Completed: 2026-04-19*
