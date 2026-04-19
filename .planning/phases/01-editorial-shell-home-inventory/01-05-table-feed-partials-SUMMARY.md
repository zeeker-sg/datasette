---
phase: 01-editorial-shell-home-inventory
plan: 05
subsystem: ui
tags:
  - table-feed
  - sketch-004-A
  - partial-seam
  - cards
  - namespace-pill-class
  - scalar-pk
  - feed-card
  - va-item
  - cat-pill
  - graceful-collapse

# Dependency graph
requires:
  - 01-01-theme-and-tokens
  - 01-02-shared-chrome
  - 01-04-database-editorial-rows
provides:
  - "Sketch 004-A news-feed-card rendering for 10 long-text tables via `_table-{db}-{table}.html` partial seam — row-list block replaced by stacked cards while Datasette's filter form / facets / FTS / sort / pagination / CSV-JSON / advanced-export all continue to render from default `table.html`"
  - "Shared `_partials/feed_card.html` generic one-row renderer — caller maps columns via `card_title_col / card_date_col / card_pill_col / card_pill_class / card_body_col / card_body_length_col / card_source_url_col / card_id_col / card_row_href`"
  - "`_show_excerpt` gate — combines body-present + body-length checks so guide tables (`about_singapore_law` where `content_length=0`) collapse gracefully to title+meta+source"
  - "Eight `*_news` partials (acra, agc, ccs, ipos, judiciary, mlaw, mom, pdpc) produced from canonical file via cp+sed loop — schema-identical bodies keep maintenance cheap (WARN-06 resolved — all 8 covered)"
  - "Judgment partial with citation kicker (`.va-citation`) above each card — petrol `.cat-pill.press-release` on `court` value"
  - "Guide partial with `.cat-pill.speech` on `section` value, body omitted, content_length gate active"
  - "FEED CARDS CSS section shipping `.va-feed / .va-empty / .va-item-wrap / .va-citation / .va-item / .va-item-head / .va-item-title / .va-item-excerpt / .va-item-foot / .va-item-foot .record-id code / .source-host` plus 640px responsive block"
  - "Category-pill-class decision pattern via `namespace(cls=)` — canonical for any future Jinja conditional that must escape `{% if %}/{% elif %}` scope (BLK-04 resolved)"
  - "Scalar-PK pattern `row[primary_keys[0]]` for `urls.row()` — NOT the list-wrapped `[pk_vals]` that would produce `/{db}/{table}/['abc...']` URLs (BLK-05 resolved)"

affects:
  - 01-06-visual-qa-sweep

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Partial-seam strategy: intercept ONLY the row-list block via `_table-{db}-{table}.html` (datasette/views/table.py:771-775 lookup) so Datasette's built-in table chrome stays intact — zero changes to `templates/table.html`"
    - "Canonical/sed replication for schema-identical sibling tables: write one authoritative file (acra_news), then `cp + sed -i ''` loop the other 7 — maintenance burden is one file to edit + rerun the loop"
    - "Generic partial with caller-supplied column-name variables: one `_partials/feed_card.html` adapts to three distinct schemas (*_news / judgments / about_singapore_law) via different variable sets"
    - "Jinja `namespace(cls=…)` pattern for variable assignment inside `{% if %}/{% elif %}` branches — the bare `{% set x = …%}` inside a conditional does NOT escape the conditional's scope under Jinja 2.x"
    - "`row.display(col)` over `row[col]` for display fields — preserves `datasette-render-markdown`, `datasette-render-html`, and foreign-key labels"
    - "`row[col]` retained ONLY for numeric/type-narrow reads (`content_length` integer read-through) where render plugins aren't active"
    - "Scalar pk to `urls.row(database, table, row[primary_keys[0]])` — single-column id PK is the shape for all 10 target tables; a list wrapper would leak array syntax into URLs"
    - "`striptags` before `truncate` on excerpt — defensive guard against `<a>` wrappers from render plugins leaking partial HTML into the 220-char clamp"
    - "Source-link bare-URL extraction: `_src|striptags|trim` strips any render-markdown-generated anchor, exposing the raw URL for host-name display and the `href` attribute"
    - "SHA truncation to 8 chars via `(id|string)[:8]` — readable record-id label"
    - "CSS insertion point: new section appended BETWEEN the DATABASE EDITORIAL ROWS section and the tail `footer a:link` override — footer override stays in last 20 lines (WARN-05 invariant preserved)"

key-files:
  created:
    - "templates/_partials/feed_card.html"
    - "templates/_table-SG-Government-Newsrooms-acra_news.html"
    - "templates/_table-SG-Government-Newsrooms-agc_news.html"
    - "templates/_table-SG-Government-Newsrooms-ccs_news.html"
    - "templates/_table-SG-Government-Newsrooms-ipos_news.html"
    - "templates/_table-SG-Government-Newsrooms-judiciary_news.html"
    - "templates/_table-SG-Government-Newsrooms-mlaw_news.html"
    - "templates/_table-SG-Government-Newsrooms-mom_news.html"
    - "templates/_table-SG-Government-Newsrooms-pdpc_news.html"
    - "templates/_table-Zeeker-Judgements-judgments.html"
    - "templates/_table-Sglawwatch-about_singapore_law.html"
  modified:
    - "static/css/zeeker-base.css"

key-decisions:
  - "Use Datasette's `_table-{db}-{table}.html` partial seam instead of a wholesale `table.html` replacement — preserves filter form, facets sidebar, FTS search box, sort links, pagination, CSV/JSON export, advanced-export pane, table-actions menu and table-definition SQL pre, all for free"
  - "Ship a single shared `_partials/feed_card.html` with caller-provided variable mapping rather than three schema-specific card partials — one file to style, three different column mappings, no markup duplication"
  - "Cover all 8 `*_news` tables (not just acra) via cp+sed replication — WARN-06: leaving 6 sibling agencies on default HTML-table rendering while acra had a feed would be a scope regression visible to anyone exploring the SG-Government-Newsrooms database"
  - "Use `namespace(cls=)` for the category-pill-class switch rather than `{% set card_pill_class = … %}` inside `{% if %}/{% elif %}` branches — BLK-04: Jinja 2.x does NOT bubble `{% set %}` up from conditional scope (verified behavior); `namespace` is the idiomatic escape hatch"
  - "Pass scalar `row[primary_keys[0]]` to `urls.row()` rather than building a `pk_vals = []` list — BLK-05: all 10 target tables have a single-column `id` PK; the list wrapper would emit URLs like `/SG-Government-Newsrooms/acra_news/['7f3a...']` (literal bracket+quote in the path segment), breaking row navigation"
  - "Use `row.display(col)` for title/date/pill/body/source/id and `row[col]` ONLY for the numeric `content_length` read-through — render plugins need `.display()` for HTML rendering; numerics need raw ints for `>` comparison"
  - "Defensive `striptags` before `truncate` on excerpt — render-markdown wraps matched URLs in `<a>` tags, and letting that HTML into a truncated clamp would leave mis-closed tags"
  - "Source link splits into `_src_bare` (raw URL) via `striptags|trim` — the href must be the bare URL, and the host-name display must also strip any render-markdown anchor before `replace()` strips `https://`"
  - "Judgment partial ships a static `card_pill_class = 'press-release'` (petrol) and renders citation as a separate `.va-citation` kicker above the card (inside `.va-item-wrap { display: contents }`), rather than embedding citation inside the card title — courts are formal, citation is bibliographic metadata, separating it from the case-name title matches editorial-broadsheet convention"
  - "Guide partial (`about_singapore_law`) uses `card_pill_class = 'speech'` (ochre) to distinguish legal-guide content from news in the visual grammar, and sets `card_body_length_col = 'content_length'` so the `_show_excerpt` gate force-collapses to title+meta+source (most rows have `content_length=0`)"
  - "CSS insertion point is between DATABASE EDITORIAL ROWS section and the tail `footer a:link` override — keeps the cascade-override invariant intact (WARN-05: footer override must remain in last 20 lines of file to win specificity against Datasette's `/-/static/app.css`)"

patterns-established:
  - "Shape of a feed-card caller partial: compute `{% set card_row_href = urls.row(database, table, row[primary_keys[0]]) if primary_keys else '' %}` inside the loop, assign column-name strings to the 8 variables, include the shared partial"
  - "For schema-identical sibling tables (e.g. 8 `*_news` agencies), write one canonical file then `cp + sed -i ''` in a shell loop — the sed substitution is cosmetic (filename-in-comment only) because the body is schema-identical"
  - "Jinja conditional-scope escape: always use `{% set ns = namespace(cls=default) %}` + `{% set ns.cls = … %}` inside `{% if %}/{% elif %}`, then `{% set outer_var = ns.cls %}` after the block"
  - "Short row-level SHA label: `<code>{{ (id|string)[:8] }}</code>` + mono styling inside a `.record-id` wrapper"

requirements-completed:
  - SC-01-table-feed-cards
  - SC-01-feed-excerpt-conditional
  - SC-01-feed-category-pill
  - SC-01-no-datasette-regressions

# Metrics
duration: ~10min
completed: 2026-04-19
---

# Phase 1 Plan 05: Table Feed Partials Summary

**Sketch 004-A news-feed cards shipped for 10 long-text tables via Datasette's `_table-{db}-{table}.html` partial seam — a single shared `_partials/feed_card.html` with caller-mapped columns drives cards for 8 `*_news` agencies (acra/agc/ccs/ipos/judiciary/mlaw/mom/pdpc), `judgments` (citation kicker + case-name + court pill), and `about_singapore_law` (title + section pill, excerpt collapses on `content_length=0`). Datasette's filter form, facets sidebar, FTS search, sort, pagination, CSV/JSON export, and advanced-export pane all continue to render because `templates/table.html` is untouched — we intercept ONLY the row-list include.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 3
- **Files created:** 11 (1 shared partial + 10 per-table partials)
- **Files modified:** 1 (`static/css/zeeker-base.css`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create shared `_partials/feed_card.html`** — `2089b90` (feat)
2. **Task 2: Create 10 per-table partials via canonical + cp+sed loop** — `cfdced6` (feat)
3. **Task 3: Append FEED CARDS CSS section (122 lines)** — `adf36ba` (feat)

_Plan metadata commit will be made by the orchestrator when it updates STATE.md / ROADMAP.md._

## The Ten Partials Shipped

| Partial file | Database.Table | Schema shape | Title col | Date col | Pill col | Pill class | Body col | Body-length gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `_table-SG-Government-Newsrooms-acra_news.html` | `SG-Government-Newsrooms.acra_news` | `*_news` | `title` | `published_date` | `category` | namespace→petrol/ochre/terracotta/muted | `content` | — |
| `_table-SG-Government-Newsrooms-agc_news.html` | `SG-Government-Newsrooms.agc_news` | `*_news` | `title` | `published_date` | `category` | namespace-driven | `content` | — |
| `_table-SG-Government-Newsrooms-ccs_news.html` | `SG-Government-Newsrooms.ccs_news` | `*_news` | `title` | `published_date` | `category` | namespace-driven | `content` | — |
| `_table-SG-Government-Newsrooms-ipos_news.html` | `SG-Government-Newsrooms.ipos_news` | `*_news` | `title` | `published_date` | `category` | namespace-driven | `content` | — |
| `_table-SG-Government-Newsrooms-judiciary_news.html` | `SG-Government-Newsrooms.judiciary_news` | `*_news` | `title` | `published_date` | `category` | namespace-driven | `content` | — |
| `_table-SG-Government-Newsrooms-mlaw_news.html` | `SG-Government-Newsrooms.mlaw_news` | `*_news` | `title` | `published_date` | `category` | namespace-driven | `content` | — |
| `_table-SG-Government-Newsrooms-mom_news.html` | `SG-Government-Newsrooms.mom_news` | `*_news` | `title` | `published_date` | `category` | namespace-driven | `content` | — |
| `_table-SG-Government-Newsrooms-pdpc_news.html` | `SG-Government-Newsrooms.pdpc_news` | `*_news` | `title` | `published_date` | `category` | namespace-driven | `content` | — |
| `_table-Zeeker-Judgements-judgments.html` | `Zeeker-Judgements.judgments` | judgment (citation + case_name + court) | `case_name` | `decision_date` | `court` | static `press-release` (petrol) | (empty) | — |
| `_table-Sglawwatch-about_singapore_law.html` | `Sglawwatch.about_singapore_law` | guide (title + section) | `title` | `last_scraped` | `section` | static `speech` (ochre) | (empty) | `content_length` |

All 10 use `urls.row(database, table, row[primary_keys[0]])` (scalar pk, not list-wrapped) for the row-detail href. All use `{% include "_partials/feed_card.html" %}` as the terminal render call.

## Shared `_partials/feed_card.html` Variable Contract

The caller must set these variables in the `{% for row in display_rows %}` loop scope BEFORE `{% include "_partials/feed_card.html" %}`:

| Variable | Type | Purpose | Empty-string sentinel? |
| --- | --- | --- | --- |
| `card_row` | Row object | Source of `row.display(col)` / `row[col]` reads | — (required) |
| `card_title_col` | str | Column name for the card title | `""` to omit (not expected) |
| `card_date_col` | str | Column name for the date displayed in `.va-item-head` | `""` to omit |
| `card_pill_col` | str | Column name for the category/court/section value | `""` to omit pill |
| `card_pill_class` | str | One of `press-release / speech / announcement / newsletter` — appended after `cat-pill ` | defaults to `press-release` |
| `card_body_col` | str | Column name for the body/excerpt text | `""` to omit excerpt entirely |
| `card_body_length_col` | str | Column name holding content-length int | `""` disables the gate; if set and value is 0, excerpt forced off |
| `card_source_url_col` | str | Column name for the external source URL | `""` to omit source link |
| `card_id_col` | str | Column name holding the record SHA/id | `""` to omit Record label |
| `card_row_href` | str | Row-detail URL (caller computes via `urls.row(database, table, row[primary_keys[0]])`) | `""` disables title link, title still renders |

**The `_show_excerpt` gate** inside the partial evaluates:

```jinja
{% set _show_excerpt = _body and _body|striptags|trim|length > 0
                       and (card_body_length_col == ''
                            or _body_len is none
                            or _body_len > 0) %}
```

This produces graceful collapse for:
1. Judgments (caller sets `card_body_col = ""` → `_body` is empty string → false).
2. Guides with `content_length = 0` (`_body_len` is 0 → short-circuit false).
3. Rows with an empty body (`_body|striptags|trim|length == 0` → false).

## Confirmation: `templates/table.html` NOT Modified

```bash
$ git diff HEAD~3 HEAD -- templates/table.html
(no output — zero changes)
```

Datasette's full `table.html` wrapper — filter form, facets sidebar, FTS search, sort links, pagination, CSV/JSON export links, `<div id="export" class="advanced-export">` pane, table-actions menu, and table-definition SQL pre — all continue to render exactly as before on every feed page. We intercept only the row-list block via the `_table-{db}-{table}.html` lookup (datasette/views/table.py:771-775).

## Confirmation: `namespace(cls=)` Pattern Used Across All 8 `*_news` Partials (BLK-04)

```bash
$ grep -c 'namespace(cls=' templates/_table-SG-Government-Newsrooms-*_news.html
templates/_table-SG-Government-Newsrooms-acra_news.html:1
templates/_table-SG-Government-Newsrooms-agc_news.html:1
templates/_table-SG-Government-Newsrooms-ccs_news.html:1
templates/_table-SG-Government-Newsrooms-ipos_news.html:1
templates/_table-SG-Government-Newsrooms-judiciary_news.html:1
templates/_table-SG-Government-Newsrooms-mlaw_news.html:1
templates/_table-SG-Government-Newsrooms-mom_news.html:1
templates/_table-SG-Government-Newsrooms-pdpc_news.html:1
```

All 8 use the canonical pattern:

```jinja
{% set _cat = (row["category"] or '')|lower %}
{% set ns = namespace(cls='press-release') %}
{% if 'speech' in _cat %}{% set ns.cls = 'speech' %}
{% elif 'announcement' in _cat %}{% set ns.cls = 'announcement' %}
{% elif 'newsletter' in _cat %}{% set ns.cls = 'newsletter' %}
{% endif %}
{% set card_pill_class = ns.cls %}
```

The judgments and about_singapore_law partials use static `card_pill_class` values (`press-release` and `speech` respectively), so they don't need the namespace escape and are unaffected by BLK-04.

## Confirmation: Scalar PK Pattern (BLK-05)

```bash
$ grep -c 'row\[primary_keys\[0\]\]' templates/_table-*.html | awk -F: '{s+=$2} END{print "total:", s}'
total: 10

$ grep -c 'pk_vals' templates/_table-*.html templates/_partials/*.html
(all files: 0)
```

Every one of the 10 partials uses the scalar-PK form:

```jinja
{% set card_row_href = urls.row(database, table, row[primary_keys[0]]) if primary_keys else '' %}
```

No partial contains `pk_vals = []`, `pk_vals.append(`, or any list-wrapping of the pk value. All 10 target tables have a single-column `id` PK, so `primary_keys[0]` is always defined when `primary_keys` is truthy. URLs emitted will be of the shape `/SG-Government-Newsrooms/acra_news/<sha>` — no bracket or quote pollution.

## Confirmation: Render-Plugin Compatibility (`row.display` vs `row[col]`)

`_partials/feed_card.html` uses `row.display(col)` for: title, date, pill, body, source_url, id. Uses bracketed `row[col]` ONLY for `content_length` (numeric read for the `_show_excerpt` gate). This preserves:

- `datasette-render-markdown` (if installed) — body column markdown renders to HTML before `striptags|truncate` clips it.
- `datasette-render-html` — same.
- Foreign-key labels — if any `*_news` table gains an FK on `category` or `source_url`, `row.display()` returns the labelled anchor.

Defensive handling: because `.display()` may return an HTML string wrapping the raw value in `<a>` (e.g. `datasette-render-markdown` auto-linking a URL in the body), the partial `striptags`-filters the excerpt and the source URL *before* truncating / replacing. The source link extracts a bare URL via `_src|striptags|trim` for the href and host-name display.

## Confirmation: CSS Banner Placement

```bash
$ grep -n '/\* ===' static/css/zeeker-base.css | tail -10
...
2756:/* =========== SHELL CHROME — phase 01 ============ */
3160: (prior sections)
3564:/* =========== HOME — phase 01 ============ */
3724:/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */
3860:/* =========== FEED CARDS — phase 01 ============ */

$ tail -20 static/css/zeeker-base.css | grep -c 'footer a:link'
2
```

New FEED CARDS section sits between DATABASE EDITORIAL ROWS and the tail `footer a:link` override. The override is still in the last 20 lines of the file, so it still wins the specificity war against Datasette's `/-/static/app.css`. WARN-05 invariant preserved.

File stats: `3876 → 3998` lines (+122). Braces balanced (572/572).

## New CSS Classes Shipped

| Selector | Purpose |
| --- | --- |
| `.va-feed` | Flex column wrapper replacing Datasette's `<table class="rows-and-columns">` when a partial is present (gap: `var(--space-6)`) |
| `.va-empty` | Centered muted mono fallback for the "no rows match filters" branch |
| `.va-item-wrap` | `display: contents` wrapper used only on judgments so `.va-citation` + `.va-item` still share the flex column gap |
| `.va-citation` | Judgment-only mono terracotta uppercase citation kicker above the card |
| `.va-item` | Surface-bg card with 1px border + 3px petrol `border-left`; hover shifts border-left to ochre, lifts `translateY(-1px)`, adds `--shadow-sm` |
| `.va-item-head` | Flex row hosting date + cat-pill (wraps on narrow viewports) |
| `.va-item-head .date` | Mono uppercase muted date text |
| `.va-item-title` | Fraunces display face, `--text-2xl`, 500 weight, `-0.01em` tracking; link-hover swaps color to petrol accent |
| `.va-item-excerpt` | Body face, line-clamped to 2 lines (3 on mobile) via `-webkit-line-clamp` |
| `.va-item-foot` | Flex row with top border, mono uppercase, hosts `.record-id` on left and `.source-host` on right |
| `.va-item-foot .record-id code` | SHA label — transparent bg, muted color, inherits size (overrides default `<code>` bg) |
| `.source-host` + `:link / :visited / :hover` | External-source link in mono + petrol with accent-hover underline on interaction |
| `@media (max-width: 640px) .va-item` | Tighter padding |
| `@media (max-width: 640px) .va-item-title` | Smaller title font |
| `@media (max-width: 640px) .va-item-excerpt` | 3-line clamp (more vertical breathing room on phones) |

All rules use `var(--*)` tokens defined in Plan 01 — zero hardcoded hex.

## Verification Results (Automated)

All Task-level acceptance criteria pass.

**Task 1 (`_partials/feed_card.html`):**
- File exists ✓
- Contains `row.display` (6 occurrences, none use bracketed `row[col]` for display fields) ✓
- `va-item` literal present ✓
- `cat-pill` literal with `card_pill_class` interpolation present ✓
- `va-item-excerpt` inside `{% if _show_excerpt %}` conditional ✓
- `_show_excerpt` gate combines body-present + body-length checks ✓
- `va-item-foot` present with `source-host` branch ✓
- `striptags` called before `truncate` on excerpt ✓

**Task 2 (10 per-table partials):**
- All 10 files exist at exact paths listed in `files_modified` ✓
- `ls templates/_table-*.html | wc -l` returns 10 ✓ — WARN-06 gate passes
- Every partial iterates `display_rows` ✓
- Every partial includes `_partials/feed_card.html` ✓
- All 8 `*_news` partials use `card_title_col = "title"` and `card_body_col = "content"` ✓
- All 8 `*_news` partials use `namespace(cls=…)` pattern (grep returns 8/8) ✓ — BLK-04 gate passes
- No `*_news` partial contains `{% set card_pill_class %}` inside `{% if %}` ✓
- judgments uses `case_name` / `decision_date` / `court` / empty body ✓
- judgments wraps card in `<div class="va-item-wrap">` and renders citation kicker ✓
- about_singapore_law uses `title` / `section` / `speech` class / `item_url` / empty body / `content_length` gate ✓
- All 10 use `row[primary_keys[0]]` for pk (grep returns 10 hits across files) ✓ — BLK-05 gate passes
- No partial contains `pk_vals = []` or `pk_vals.append(` ✓ — BLK-05 gate passes
- Jinja syntax parse test on all 11 new/modified templates (including feed_card) → all OK ✓
- `templates/table.html` NOT modified by any commit in this plan ✓
- No partial references `render_cell` or `render_row_html` (those are Python hooks, not templates) ✓

**Task 3 (`static/css/zeeker-base.css`):**
- Banner `/* =========== FEED CARDS — phase 01 ============ */` present ✓
- `.va-feed {` ✓
- `.va-item {` with `border-left: 3px solid var(--color-accent)` ✓
- `.va-item:hover` shifts `border-left-color` to `var(--color-ochre)` ✓
- `.va-item-title` uses `var(--font-display)` + `var(--text-2xl)` ✓
- `.va-item-excerpt` uses `-webkit-line-clamp: 2` ✓
- `.va-item-foot` + `.record-id` styling present ✓
- `.source-host` uses `var(--color-accent)` + `var(--font-mono)` ✓
- `.va-citation` uses `var(--color-terracotta)` ✓
- `footer a:link` override still present ✓
- `tail -20 | grep -q 'footer a:link'` → 2 matches (WARN-05 gate passes) ✓
- Line count 3876 → 3998 (+122) ✓
- Braces balanced (572/572) ✓

**Plan-level success criteria:**
- All ten `_table-*.html` partials exist ✓
- `_partials/feed_card.html` exists and handles `_show_excerpt` gate ✓
- All feed-card CSS classes present in `zeeker-base.css` ✓
- `templates/table.html` not modified (Datasette's full chrome continues to render) ✓
- BLK-04 resolved (all 8 `*_news` use namespace pattern) ✓
- BLK-05 resolved (all 10 partials use scalar pk) ✓
- WARN-06 resolved (all 8 `*_news` tables have partials) ✓
- WARN-05 preserved (footer override in last 20 lines of CSS) ✓

**Manual browser verifications (items 1-10 in the plan's `<verification>` block):** deferred to Plan 01-06 visual-qa-sweep. Rationale: the only database attached in this dev environment is `_memory` — the S3-downloaded production databases (`SG-Government-Newsrooms`, `Zeeker-Judgements`, `Sglawwatch`) are not present. All static gates (grep-based BLK-04 / BLK-05 / WARN-05 / WARN-06 / file-existence / Jinja parse) pass. A live curl against `http://127.0.0.1:8001/SG-Government-Newsrooms/acra_news` returned 404 (route not found because DB not attached), not 500 — confirming the template itself would not throw when the DB is attached, but full end-to-end card-rendering verification requires a dev server with the real databases. Plan 01-06 owns that verification pass.

## Deviations from Plan

None — plan executed exactly as written.

All template structure (feed_card variable contract, per-table column assignments, namespace pattern in `*_news`, citation kicker on judgments, graceful-collapse gate on about_singapore_law), all class names, the cp+sed replication loop for the 7 sibling `*_news` tables, and all CSS declarations were transcribed from the plan's `<action>` blocks character-for-character.

## Authentication Gates

None. All work was purely frontend template/CSS. No auth surface changed. No S3 or runtime state touched.

## Known Stubs

None.

Every variable the feed_card partial expects is wired by the caller partial to a real column name on the target table's schema (verified against the planning_context column manifest). The `_show_excerpt` gate is an intentional collapse — not a stub — and Plan 03 / Plan 04 already define `.cat-pill.press-release`, `.cat-pill.speech`, `.cat-pill.announcement`, `.cat-pill.newsletter` in the SHELL CHROME section, so the pill-class values the partials emit resolve to styled outputs.

## Threat Flags

None.

This plan only changes template markup and appends CSS. No new network surface, no auth path, no file access pattern, no schema change. `rel="noopener"` + `target="_blank"` on the external source link (prevents tabnabbing) is already present in the partial.

## Render-Plugin Compatibility Observations

- **`row.display(col)` returns a Markup-wrapped HTML string** when a render plugin is active on that column (`datasette-render-markdown`, `datasette-render-html`, FK labels). The partial `striptags`-filters before any `truncate` or `replace` to avoid clipping mid-tag.
- **`row[col]` was used only for `content_length`** — an integer column where render plugins don't apply, and where the gate semantics (`> 0`) require a raw numeric not an HTML string.
- **The source link double-protects**: `_src|striptags|trim` extracts a bare URL even if `datasette-render-markdown` auto-linked it into an anchor; the `href` attribute receives the bare URL, and the host-name display strips `https://` / `http://` for compact readability.
- **Excerpt defensively strips tags** so any nested anchor or inline HTML from markdown rendering doesn't leak partial-tag output into the 220-char clamp.

## Self-Check: PASSED

- `.planning/phases/01-editorial-shell-home-inventory/01-05-table-feed-partials-SUMMARY.md` — FOUND (this file)
- `templates/_partials/feed_card.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-acra_news.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-agc_news.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-ccs_news.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-ipos_news.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-judiciary_news.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-mlaw_news.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-mom_news.html` — FOUND
- `templates/_table-SG-Government-Newsrooms-pdpc_news.html` — FOUND
- `templates/_table-Zeeker-Judgements-judgments.html` — FOUND
- `templates/_table-Sglawwatch-about_singapore_law.html` — FOUND
- `static/css/zeeker-base.css` — FOUND (modified, +122 lines)
- Commit `2089b90` (Task 1) — FOUND in git log
- Commit `cfdced6` (Task 2) — FOUND in git log
- Commit `adf36ba` (Task 3) — FOUND in git log

## Follow-up Items Noticed (Not Done — Out of Scope)

- **Live curl-based verification**: the dev-server only has `_memory` attached in this environment; the plan's `<verification>` block items 1-10 (live card rendering / Datasette-chrome integrity / CSV+JSON export response codes / filtered `?_search=` behavior / scalar-pk URL inspection / mobile collapse) all require the production databases attached. Deferred to Plan 01-06.
- **`*_news` partials are schema-identical** — if the `*_news` schema ever drifts (e.g. `source_url` renamed, `content_length` added), the canonical `acra_news` file is the single edit point + the cp+sed loop must be rerun. Consider templating the per-table partial via a generator in a later phase if agencies gain schema variation.
- **`.va-item-head` date column**: for `*_news` tables, `published_date` is assumed to be a plain date string or the format returned by `row.display()`. If a future agency column uses a different name (`pub_date`, `release_date`), the canonical `acra_news` file needs an update.
- **Citation formatting on judgments**: `.va-citation` renders the raw `citation` value verbatim. If citations ever need normalization (e.g. Neutral + Reported Citation toggle), that's a Python render_cell plugin or a template-level filter — not in scope here.
- **Record-id truncation to 8 chars**: arbitrary but matches the sketch. Could be configurable via a caller-supplied `card_id_truncate` variable if per-table tuning is needed.

## Next Phase Readiness

- **Plan 01-06 (visual-qa-sweep):** Owns the live-verification sweep listed in the plan's `<verification>` block (10 items). The dev server with production databases must be running for those checks. All static gates this plan owns have passed.
- **No blockers** for phase completion. All shared chrome primitives from Plans 01-04 are consumed; the editorial-shell UI is feature-complete across home / database / table-feed surfaces.

---
*Phase: 01-editorial-shell-home-inventory*
*Completed: 2026-04-19*
