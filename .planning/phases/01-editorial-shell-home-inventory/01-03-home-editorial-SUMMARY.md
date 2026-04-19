---
phase: 01-editorial-shell-home-inventory
plan: 03
subsystem: ui
tags:
  - home
  - editorial
  - card-grid
  - hero
  - statband
  - cta
  - rotating-accent
  - civic-broadsheet

# Dependency graph
requires:
  - 01-01-theme-and-tokens
  - 01-02-shared-chrome
provides:
  - "Sketch 001-D home template at templates/index.html — warm hero + petrol statband + numbered card grid + how-to + dark CTA"
  - "Home-specific CSS section (`HOME — phase 01` banner) with .cards / .card / .card .idx / .card-meta / .card-desc / .card-count / .chip / .how-grid / .home-header .hero-search"
  - "Rotating-accent card borders via .card:nth-child(3n+2) → ochre, .card:nth-child(3n+3) → terracotta"
  - "`.home-header .hero-search` inline petrol-bordered search pill (home-only; scoped via .home-header parent)"
affects:
  - 01-06-visual-qa-sweep

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Consume-only relationship to Plan 02 shell chrome: home template uses .db-header, .db-header-grid, .db-statband, .section, .section.alt, .section-num, .section-head, .kicker, .cta, .btn-primary, .btn-ghost verbatim — no overrides or redefinitions"
    - "Rotating accent via `:nth-child(3n+2)` / `:nth-child(3n+3)` structural selectors (no per-card class needed)"
    - "Home-specific search scoped under `.home-header .hero-search` so shared chrome layers don't need to know about it"
    - "String keys namespaced with `home_` prefix (home_hero_primary, home_hero_accent, home_hero_underline, home_section1_*, home_section2_*, home_cta_*) so strings.yaml updates don't collide with shared strings"
    - "`visible_dbs = databases|rejectattr('hidden')|list` filter applied once at hero-top so stat band and card grid use identical dataset"

key-files:
  created: []
  modified:
    - "templates/index.html"
    - "static/css/zeeker-base.css"

key-decisions:
  - "Filter `databases|rejectattr('hidden')|list` computed once into `visible_dbs` and reused for both the stat band count and the card grid iteration — avoids double-filtering and guarantees both surfaces render the same count"
  - "Stat band shows 4 cells: visible_dbs count, total_tables (only if > 0), SQL marker, export formats. Row count is NOT fabricated — Datasette's index context doesn't expose per-database row counts so we don't invent one"
  - "Two-digit mono corner numeral via `{{ '{:02d}'.format(loop.index) }}` rather than a zero-pad filter — matches Python's native str.format"
  - "Database title fallback: prefer metadata.databases[name].title → else `database.name|replace('-',' ')|replace('_',' ')|title` (so `SG-Government-Newsrooms` renders `Sg Government Newsrooms`)"
  - "HOME CSS section inserted BEFORE the tail `footer a:link` override using Edit tool's context-surround replacement — the override block moved from lines 3564-3580 to lines 3725-3740 but remains within the last 20 lines (plan's hard gate)"
  - "`.chip` uses rotation-aware color tinting: `.card:nth-child(3n+2) .chip:not(.chip-link)` paints the non-link chip ochre, matching the card's border accent — this creates a subtle 'the whole card is in this color key' feel"
  - "Ghost button (`.btn-ghost`) already defined in Plan 02 — reused without redefinition; the CTA actions wire them via `<a class=\"btn-primary\">` + `<a class=\"btn-ghost\">`"
  - "No `<link rel=\"canonical\">` tag emitted (BLK-01) — Datasette's default index view handles canonicalization and `request.url` raises under StrictUndefined in Datasette 0.65.1"

patterns-established:
  - "Home template is a pure block-override of `default:index.html`: extra_head (super + meta description), nav (include _header.html), content (the full editorial stack), footer (include _footer.html). No custom blocks redefined inside content — it's a single flat block"
  - "Card grid pattern: `.cards` grid wrapper + `<article class=\"card\">` children. Each card carries: `.idx` corner numeral, `.card-meta` mono uppercase row, `<h3>` display-face title with `<a>` inside, optional `.card-desc` paragraph, optional `.card-count` big number with `<small>` unit, `.chips` cluster with mixed `<span class=\"chip\">` (non-linky) + `<a class=\"chip chip-link\">` (linky)"
  - "Kicker + H2-with-em + aside triad is the 'section head' formula used across № 01 and № 02 sections — reusable by Plan 04/05 for database/table page sections"

requirements-completed:
  - SC-01-home-hero-asymmetric
  - SC-01-home-statband
  - SC-01-home-card-grid-rotation
  - SC-01-home-cta-dark

# Metrics
duration: ~2min
completed: 2026-04-19
---

# Phase 1 Plan 03: Home Editorial Summary

**Sketch 001-D home page shipped — warm hero with italic-accent H1 + petrol stat band + numbered database card grid with rotating petrol/ochre/terracotta top-border accents + three-column how-to block + dark CTA, rendered entirely through Plan 02 shell-chrome classes plus one new HOME-specific CSS section (.cards / .card / .chip / .how-grid / .home-header .hero-search).**

## Performance

- **Duration:** ~2 min
- **Tasks:** 2
- **Files modified:** 2

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite `templates/index.html` as sketch 001-D (editorial hero + stat band + card grid + how-to + CTA)** — `281fc35` (feat)
2. **Task 2: Append `HOME — phase 01` CSS section (.cards / .card with nth-child accent rotation, .chip, .how-grid, .hero-search)** — `e199788` (feat)

_Plan metadata commit will be made by the orchestrator when it updates STATE.md / ROADMAP.md._

## Files Created/Modified

- **`templates/index.html`** — full replacement. Old `hero-section` + `stats-strip` + `databases-section` + `about-section` blocks gone. New structure: `{% block extra_head %}` (meta description), `{% block nav %}` (include `_header.html`), `{% block content %}` (db-header.home-header hero + db-statband + section № 01 databases card grid + section.alt № 02 how-to + cta block), `{% block footer %}` (include `_footer.html`). 151 insertions / 121 deletions.
- **`static/css/zeeker-base.css`** — new `/* =========== HOME — phase 01 ============ */` banner section appended AFTER the SHELL CHROME section from Plan 02 and BEFORE the tail `footer a:link` override block. 160 insertions. File grew from 3,580 → 3,740 lines. Braces balanced (524 open / 524 close). Footer override remains within last 20 lines (gate passes).

## Datasette Context Variables Consumed by the New Template

The rewritten `templates/index.html` depends on the following Jinja context variables exposed by Datasette's default `IndexView` (`datasette/views/base.py`):

| Variable | Type | Usage |
| --- | --- | --- |
| `metadata` | dict | `.description` (hero lede fallback), `.license` (meta-col Licence), `.source` (meta-col Source), `.databases[name].title` (card title), `.databases[name].description` (card description) |
| `databases` | list[dict] | Iterated after `|rejectattr('hidden')|list` filter; each item uses `.name`, `.path` (implicitly via `/{{ database.name }}`), `.table_count` (gate + statband sum + card count), `.size` (card meta; filesizeformat filter applied) |
| `current_year` | int | meta-col "Last refreshed" cell; injected by `plugins/string_manager.py extra_template_vars` hook |

No custom SQL queries via `datasette-template-sql` are needed for the home page — all data comes from the default index context.

## `s()` String Keys Referenced

All user-facing strings go through the `s('key', 'default')` helper so `plugins/strings.yaml` can later override them. The plan introduces the following new keys (all namespaced under `home_*`):

| Key | Default | Used in |
| --- | --- | --- |
| `home_hero_primary` | `Public data,` | Hero H1 lead |
| `home_hero_accent` | `rendered` | Hero H1 `<em>` petrol italic |
| `home_hero_underline` | `legible` | Hero H1 `<span class="und">` ochre underline |
| `home_section1_line1` | `Curated public data,` | № 01 head H2 lead |
| `home_section1_line2` | `ready to query` | № 01 head H2 `<em>` |
| `home_section1_aside` | `Every dataset ships with schema, source citation, and full SQL access.` | № 01 aside copy |
| `home_section2_line1` | `Three ways to` | № 02 head H2 first fragment |
| `home_section2_line2` | `spend` | № 02 head H2 `<em>` |
| `home_section2_line3` | `the data.` | № 02 head H2 trailing fragment |
| `home_cta_line1` | `Bring your questions,` | CTA H2 lead |
| `home_cta_line2` | `leave with data` | CTA H2 `<em>` ochre italic |
| `home_cta_body` | `Open, citable, machine-readable. CC-BY-4.0 unless noted otherwise.` | CTA body paragraph |
| `home_cta_primary` | `Start searching` | CTA primary button label |
| `home_cta_ghost` | `Read the guide` | CTA ghost button label |
| `howto_heading` | `How to use` | № 02 section-num tail |

Reused existing keys (from `plugins/string_manager.py` defaults): `site_tagline`, `search_placeholder`, `form_export`, `databases_heading`, `plural_database`, `plural_databases`, `plural_table`, `plural_tables`.

**Action for later phase:** a follow-up plan (or operator) can add these new keys to `plugins/strings.yaml` — until then, the defaults render, so the page never shows raw `home_hero_primary` text.

## Hardcoded Fallback Text (candidates for future i18n)

These strings are written literally in the template rather than going through `s()`:

| String | Location | Reason |
| --- | --- | --- |
| `Civic data, open access` | Hero kicker | One-off editorial tagline; negligible translation value |
| `SQL` / `full query access` | Stat band | Brand/technical marker |
| `CSV · JSON` / `export formats` (fallback only) | Stat band | Technical labels |
| `Search across all data →` | № 01 aside link | One-off copy |
| `Explore` / `Browse by database` / `Query` / `Write SQL` / `Export` / `Pull the data` | How-to column headers + descriptions | Three-column editorial copy; not parameterized |
| `Browse` | First chip inside each card | Trivial label |
| `CSV` / `JSON` | Chip-link labels | Format names, do not translate |
| `Licence` / `Source` / `Last refreshed` | Meta-col `<dt>` labels | Would benefit from i18n but kept literal for now |

**Action for later phase:** if i18n is a goal, these should migrate behind `s()` calls — they aren't currently gating localization work so they're left as-is.

## New CSS Classes Shipped

| Selector | Purpose |
| --- | --- |
| `.home-header .hero-search` | Inline petrol-bordered search pill (home-only) |
| `.home-header .hero-search input` | Search input styled transparent inside the pill |
| `.home-header .hero-search button` | Ochre submit button with hover state |
| `.cards` | Auto-fill grid (minmax 280px) wrapping card articles |
| `.card` | Individual card with petrol top border, hover lift |
| `.card:nth-child(3n+2)` | **Rotation slot 2:** border-top-color → `--color-ochre` |
| `.card:nth-child(3n+3)` | **Rotation slot 3:** border-top-color → `--color-terracotta` |
| `.card .idx` | Absolute-positioned mono corner numeral (top-right) |
| `.card .card-meta` | Mono uppercase row of table/size chips above title |
| `.card h3` | Fraunces display title inside card |
| `.card h3 a{,:link,:visited}` | Card title link colored `--color-ink`, no underline |
| `.card h3 a:hover` | Hover → `--color-accent` (petrol) |
| `.card .card-desc` | Secondary-color body paragraph inside card |
| `.card .card-count` | Big display-face row count with mono `<small>` unit |
| `.card .card-count small` | Mono uppercase unit label beside the big number |
| `.card .chips` | Flex-wrap chip cluster at card bottom |
| `.chip` | Soft-accent pill primitive (uppercase, 2xs, radius-full) |
| `.chip.chip-link:hover` | Chip-link hover → filled accent bg |
| `.card:nth-child(3n+2) .chip:not(.chip-link)` | Non-link chip tinted ochre inside rotation-2 card |
| `.card:nth-child(3n+3) .chip:not(.chip-link)` | Non-link chip tinted terracotta inside rotation-3 card |
| `.how-grid` | Three-column grid for the "How to use" block |
| `.how-item .kicker` | Kicker spacing inside a how-item column |
| `.how-item h3` | Fraunces display-face how-item title |
| `.how-item h3 em` | Italic petrol inside how-item title |
| `.how-item p` | Secondary-color paragraph inside how-item |
| `@media (max-width: 960px) .how-grid` | Collapse to single column on narrow viewports |

## Preserved Verbatim

- **`footer a:link / :visited / :active / :hover / :focus` override block** — re-positioned exactly as it was in the file after the HOME section append, preserving every line and the comment banner. `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` still returns 0 (the plan's hard gate).
- **`{% extends "default:index.html" %}` top line** — retained.
- **`{% block extra_head %} {{ super() }} {% if metadata and metadata.description %}<meta name="description"…>{% endif %} {% endblock %}`** — retained verbatim (with `{{ super() }}` preserving whatever the default template injects).
- **`{% block nav %}{% include "_header.html" %}{% endblock %}` and `{% block footer %}{% include "_footer.html" %}{% endblock %}`** — retained so Plan 02's shared chrome wires through.

## Deviations from Plan

None — plan executed exactly as written.

The plan specified the template structure verbatim in its `<action>` block, and it was followed character-for-character. All `s()` keys, fallback defaults, class attribute values, `visible_dbs` filter logic, `loop.index` corner numeral, and the № 01 / № 02 / CTA block order were transcribed from the plan spec. Same for the CSS block — selectors and declarations were copied exactly as specified.

## Confirmation: No Canonical Link Emitted

Per the critical preservation contract and BLK-01 (from the plan-checker note):

```bash
$ grep -c 'request.url' templates/index.html
0
$ grep -c 'rel="canonical"' templates/index.html
0
```

Datasette 0.65.1 does NOT expose `request.url` in Jinja context (raises under StrictUndefined). Datasette's default index view emits its own canonical link where appropriate; we do not override or supplement this. The home page at `/` has a single trivial canonical shape and does not need a custom tag.

## Known Stubs

None.

The template wires every user-facing surface to real data or to `s()` keys with sensible defaults:
- Hero lede → `metadata.description` first, then `s('site_tagline', default)`.
- Meta-col → `metadata.license` / `metadata.source` first, then hardcoded `'CC-BY-4.0'` / `'Various curated sources'` fallbacks.
- Stat band → `visible_dbs|length` and `ns.total_tables` (real Datasette data).
- Cards → iterate `visible_dbs` via `{% for database in visible_dbs %}` — `database.name`, `database.table_count`, `database.size`, `metadata.databases[name].title`, `metadata.databases[name].description` all real.
- How-to columns have hardcoded copy (documented above under "Hardcoded Fallback Text") — deliberate, not a stub.
- CTA buttons point at `/-/search` and `/how-to-use` — real Datasette routes.

If the site is deployed with zero attached databases, `{% if visible_dbs %}` guards the card grid so the page still renders cleanly (stat band shows `0 databases`, card grid section shows the head text without cards).

## Verification Results

All automated acceptance criteria pass:

**Task 1 (`templates/index.html`):**
- `grep -q '№ 01'` → present ✓
- `grep -q '№ 02'` → present ✓
- `grep -q 'class="db-header home-header"'` → present (literal) ✓
- `grep -q 'class="db-statband"'` → present ✓
- `grep -q 'class="cards"'` → present ✓
- `grep -q 'class="cta"'` → present ✓
- `grep -q 'for database in visible_dbs'` → present ✓
- `grep -q 'btn-primary'` → present ✓
- `grep -q 'btn-ghost'` → present ✓
- `! grep -q 'hero-section'` → absent ✓ (old class gone)
- `! grep -q 'stats-strip'` → absent ✓ (old class gone)
- `! grep -q 'request.url'` → absent ✓ (BLK-01)
- `! grep -q 'rel="canonical"'` → absent ✓ (BLK-01)
- Jinja syntax parse test → PASS ✓

**Task 2 (`static/css/zeeker-base.css`):**
- `grep -q 'HOME — phase 01'` → present ✓
- `grep -q '\.cards {'` → present ✓
- `grep -q '\.card {'` → present ✓
- `grep -q '\.card:nth-child(3n+2)'` → present (2 occurrences) ✓
- `grep -q '\.card:nth-child(3n+3)'` → present (2 occurrences) ✓
- `grep -q 'border-top-color: var(--color-ochre)'` → present ✓
- `grep -q 'border-top-color: var(--color-terracotta)'` → present ✓
- `grep -q '\.how-grid'` → present ✓
- `grep -q '\.chip {'` → present ✓
- `grep -q 'hero-search'` → present ✓
- `grep -q 'footer a:link'` → present ✓
- `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` → present (passes the critical preservation gate) ✓
- CSS braces balanced: 524 open / 524 close ✓
- SHELL CHROME section from Plan 02 still present ✓
- All CSS tokens referenced in HOME section (`--color-accent-soft`, `--color-accent-hover`, `--text-2xs`, `--color-text-inverse`, `--color-ochre`, `--color-terracotta`, `--radius-full`, `--tracking-wide`, `--shadow-md`, etc.) confirmed declared in `:root` (from Plan 01) ✓

**Plan-level success criteria:**
- `grep -c '\.card' static/css/zeeker-base.css` → 28 (>0 required) ✓
- `grep -c 'nth-child(3n+2)' static/css/zeeker-base.css` → 2 (>=1 required) ✓
- `grep -c 'nth-child(3n+3)' static/css/zeeker-base.css` → 2 (>=1 required) ✓
- No modifications to `.planning/STATE.md` or `.planning/ROADMAP.md` ✓
- No modifications to files outside `files_modified` list (`git status --short` clean after commits) ✓
- Only 2 atomic commits for this plan (`281fc35`, `e199788`) ✓

Manual browser verifications (items 1-8 in plan's `<verification>` block) require the dev server running — not executed automatically. These are deferred to Plan 01-06 visual-qa-sweep or manual QA.

## Self-Check: PASSED

- `.planning/phases/01-editorial-shell-home-inventory/01-03-home-editorial-SUMMARY.md` — FOUND (this file)
- `templates/index.html` — FOUND (modified, 151+/121-)
- `static/css/zeeker-base.css` — FOUND (modified, +160 lines)
- Commit `281fc35` (Task 1) — FOUND in git log
- Commit `e199788` (Task 2) — FOUND in git log

## Next Phase Readiness

- **Home page is now production-shape.** It renders real databases from Datasette's default context, shows rotating accent borders on card tops, has the italic-accent H1 signature, petrol stat band, and dark CTA. No dev-server smoke test was run in this plan — Plan 01-06 (visual-qa-sweep) should validate the eight visual checks in the plan's `<verification>` block.
- **Plan 01-04 (database-editorial-rows):** Independent of this plan — both consume Plan 02 shared chrome and Plan 01 tokens. Safe to execute in parallel with 01-05.
- **Plan 01-05 (table-feed-partials):** Independent. Consumes `.cat-pill.*` from Plan 02.
- **Plan 01-06 (visual-qa-sweep):** Should include the eight items from this plan's `<verification>` block (curl 200, H1 typography, statband render, № 01/02 rendering, CTA block, footer contrast, view-source checks for canonical/request.url).
- **Follow-up:** Adding the new `home_*` string keys to `plugins/strings.yaml` would surface them to any future per-locale overrides — currently the defaults render just fine.

---
*Phase: 01-editorial-shell-home-inventory*
*Completed: 2026-04-19*
