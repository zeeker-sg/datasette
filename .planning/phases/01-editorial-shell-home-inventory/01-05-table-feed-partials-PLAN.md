---
phase: 01-editorial-shell-home-inventory
plan: 05
type: execute
wave: 5
depends_on: ["01", "02", "04"]
files_modified:
  - templates/_partials/feed_card.html
  - templates/_table-SG-Government-Newsrooms-acra_news.html
  - templates/_table-SG-Government-Newsrooms-agc_news.html
  - templates/_table-SG-Government-Newsrooms-ccs_news.html
  - templates/_table-SG-Government-Newsrooms-ipos_news.html
  - templates/_table-SG-Government-Newsrooms-judiciary_news.html
  - templates/_table-SG-Government-Newsrooms-mlaw_news.html
  - templates/_table-SG-Government-Newsrooms-mom_news.html
  - templates/_table-SG-Government-Newsrooms-pdpc_news.html
  - templates/_table-Zeeker-Judgements-judgments.html
  - templates/_table-Sglawwatch-about_singapore_law.html
  - static/css/zeeker-base.css
autonomous: true
requirements:
  - SC-01-table-feed-cards
  - SC-01-feed-excerpt-conditional
  - SC-01-feed-category-pill
  - SC-01-no-datasette-regressions
must_haves:
  truths:
    - "All 8 *_news tables render as stacked feed cards (date + category pill + title + conditional excerpt + SHA + source link), NOT as an HTML <table>"
    - "judgments table renders with citation kicker + case-name title + court pill + decision_date"
    - "about_singapore_law renders as guide cards (title + section pill + source) with no excerpt block"
    - "Cards use `row.display(\"col\")` so foreign-key labels and datasette-render-markdown continue to work"
    - "Datasette's filter form, facets sidebar, FTS search, sort links, pagination, CSV/JSON export, and advanced-export pane all continue to render on every feed page (because we use `_table-{db}-{table}.html` partial seam, not `table.html` replacement)"
    - "Guide tables (content_length=0) collapse gracefully — excerpt block disappears, title+meta+source remain"
    - "Category pill color-codes by content type (petrol=press-release, ochre=speech, terracotta=announcement, muted=newsletter); falls back to petrol when category is unknown"
    - "No partial returns HTTP 500 — `curl http://127.0.0.1:8001/SG-Government-Newsrooms/acra_news` returns 200"
  artifacts:
    - path: "templates/_partials/feed_card.html"
      provides: "Shared feed-card partial using row.display() + conditional excerpt"
      contains: "row.display"
    - path: "templates/_table-SG-Government-Newsrooms-acra_news.html"
      provides: "News feed rendering for ACRA press releases (shape: *_news) — the canonical template copied to 7 sibling agencies"
      contains: "_partials/feed_card.html"
    - path: "templates/_table-Zeeker-Judgements-judgments.html"
      provides: "Judgment feed rendering (shape: case_name + court + decision_date + subject_tags)"
      contains: "_partials/feed_card.html"
    - path: "templates/_table-Sglawwatch-about_singapore_law.html"
      provides: "Legal-guide feed rendering (no body — title+meta+source only)"
      contains: "_partials/feed_card.html"
    - path: "static/css/zeeker-base.css"
      provides: ".va-feed / .va-item / .va-item-head / .va-item-title / .va-item-excerpt / .va-item-foot / .source-host CSS"
      contains: ".va-item"
  key_links:
    - from: "templates/_table-{db}-{table}.html"
      to: "Datasette's table.html partial lookup (datasette/views/table.py:771-775)"
      via: "file-name convention"
      pattern: "_table-"
    - from: "templates/_partials/feed_card.html"
      to: "row.display(col_name) — preserves foreign-key labels and render-markdown"
      via: "Jinja helper"
      pattern: "row\\.display"
---

<objective>
Implement the sketch 004-A news-feed-card pattern for long-text tables via Datasette's `_table-{database}-{table}.html` partial seam — which replaces ONLY the row-list block, keeping filter form / facets / FTS / sort / pagination / CSV-JSON export / advanced-export pane fully functional. Ship a shared `_partials/feed_card.html` rendering one card, and **ten** concrete per-table partials covering all 8 `*_news` tables in `SG-Government-Newsrooms` plus `judgments` and `about_singapore_law`. Append feed-card CSS to `zeeker-base.css`.

Purpose: HTML-table rendering of long-text rows (news bodies, judgments, guides) is the principal UX problem the sketch work targeted. Cards let the title + date + excerpt carry the page; Datasette's built-in machinery (facets, search, export) stays intact because we intercept at the partial level, not the template level. WARN-06: all 8 `*_news` tables share identical schema and must therefore ALL ship the feed-card partial — leaving 6 on the default HTML-table rendering would be a scope regression.

Output: One `_partials/feed_card.html` shared file that adapts to any `*_news` / `judgments` / `about_singapore_law` row shape via passed-in variables, ten `_table-*.html` stub partials that each `{% include %}` the shared card with the right field mapping, and a `/* =========== FEED CARDS — phase 01 ============ */` CSS section. ZERO changes to `templates/table.html` — Datasette's built-in table shell continues to provide the filter bar, sort, facets, pagination, CSV/JSON/advanced-export controls.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md
@.claude/skills/sketch-findings-zeeker-datasette/sources/004-table-as-news-archive/index.html
@.planning/notes/datasette-styling-limits.md
@.planning/phases/01-editorial-shell-home-inventory/01-02-shared-chrome-SUMMARY.md
@.planning/phases/01-editorial-shell-home-inventory/01-04-database-editorial-rows-SUMMARY.md
@templates/table.html

<interfaces>
**The partial seam — this is the entire reason the plan works:**

Datasette's default `table.html` (locally at `.venv/lib/python3.12/site-packages/datasette/templates/table.html:152`) includes the row-list block via:
```jinja
{% include custom_table_templates %}
```
where `custom_table_templates` is computed in `datasette/views/table.py:771-775` as:
```python
[
  f"_table-{database}-{table}.html",
  f"_table-table-{database}-{table}.html",
  "_table.html",
]
```

**This means:**
- Dropping `templates/_table-{database}-{table}.html` replaces ONLY the `<table class="rows-and-columns">` element. Everything else — filter form, facets sidebar, FTS search box, sort links, pagination, CSV/JSON export, advanced-export pane, table-actions menu, table-definition SQL pre — continues to render from the default table.html.
- The partial inherits `table.html`'s full Jinja scope: `display_rows`, `display_columns`, `rows`, `filtered_table_rows_count`, `next_url`, `filters`, `facet_results`, `sort`, `sort_desc`, `is_sortable`, `primary_keys`, `metadata`, `url_csv`, `renderers`, `request`, plus helpers `urls.row(db, table, pk)`, `path_with_replaced_args(request, {...})`, `append_querystring`, `fix_path`.
- **CRITICAL**: use `row.display("col_name")` (not `row["col_name"]`) so `datasette-render-markdown` / `datasette-render-html` / foreign-key labels continue to work. `row.display()` returns a Markup-wrapped HTML string when a render plugin is active; it's the row value otherwise.
- `display_rows` is the iteration target (what default table.html loops).

**Database name slugification in filenames:**

The database name portion of `_table-{database}-{table}.html` must match Datasette's route slug exactly. Real database names per planning_context:
- `SG-Government-Newsrooms` (exact, with capitals and hyphens)
- `Zeeker-Judgements`
- `Sglawwatch`

Tables within those databases (lowercase with underscores):
- `SG-Government-Newsrooms` → ALL 8 `*_news` tables: `acra_news`, `agc_news`, `ccs_news`, `ipos_news`, `judiciary_news`, `mlaw_news`, `mom_news`, `pdpc_news`
- `Zeeker-Judgements` → `judgments`
- `Sglawwatch` → `about_singapore_law`

File names must be literal: e.g. `_table-SG-Government-Newsrooms-acra_news.html`.

**Schema shapes (from planning_context):**

| Database.Table | Key columns | PK |
|---|---|---|
| `*_news` tables | `id` (SHA-256), `source_url`, `category`, `title`, `published_date`, `content` (body text), + 3 more | `id` (single) |
| `judgments` | 19 columns incl. `citation`, `case_name`, `case_numbers`, `decision_date`, `court`, `subject_tags` (array), `source_url`, `id` | `id` (single) |
| `about_singapore_law` | 8 columns: `id`, `item_url`, `title`, `section`, `home_page`, `last_scraped`, `content_length` (often 0) | `id` (single) |

**All four target tables use a single-column `id` primary key** — BLK-05 requires passing the scalar pk value (not a list) to `urls.row()`.

**The excerpt column for `*_news`:** the body column name is `content`. The `content_length` column on `about_singapore_law` is often 0 — excerpt MUST be omitted for those rows (title + meta + source only).

**Category pill classification (*_news):**
- `category` value (string). Map to pill class:
  - contains "press" or "release" → `.press-release` (petrol)
  - contains "speech" → `.speech` (ochre)
  - contains "announcement" → `.announcement` (terracotta)
  - contains "newsletter" → `.newsletter` (muted)
  - else → `.press-release` (default petrol)

For `judgments`: pill shows `court` value with class `.press-release` (petrol — courts are formal).
For `about_singapore_law`: pill shows `section` value with class `.speech` (ochre — guides).

**Jinja scope note (BLK-04):** `{% set card_pill_class %}` assignments inside `{% if %}` / `{% elif %}` blocks do NOT escape the conditional's scope in Jinja — the outer block sees the variable as undefined. The correct pattern is the `namespace` object, which Jinja explicitly supports for cross-scope mutation. This plan requires ALL category-pill-class computations to use `namespace(cls='...')` (see Task 2).

**CSS classes from Plan 02 consumable without redefinition:**
- `.cat-pill`, `.cat-pill.press-release`, `.cat-pill.speech`, `.cat-pill.announcement`, `.cat-pill.newsletter`

Shell CSS classes from Plan 02 also present: `.container`, `.kicker`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create shared _partials/feed_card.html card template with conditional excerpt + category pill + source link + SHA</name>
  <files>templates/_partials/feed_card.html</files>
  <read_first>
    - .claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md (HTML Structures → "News-feed item (sketch 004)")
    - .claude/skills/sketch-findings-zeeker-datasette/sources/004-table-as-news-archive/index.html (variant A tab — `.va-item` markup)
    - .planning/notes/datasette-styling-limits.md (section 3 — Context available inside _table-*.html)
  </read_first>
  <action>
    Create new file `templates/_partials/feed_card.html` (creating the `_partials/` subdirectory as needed). This partial renders ONE card and is included by every `_table-*.html` partial in Task 2. It expects these variables to be set by the caller before `{% include %}`:

    - `card_row` — the Datasette row object (so `card_row.display("col")` works)
    - `card_title_col` — string, column name holding the title
    - `card_date_col` — string, column name holding the publication date (or empty)
    - `card_pill_col` — string, column name holding the category/court/section value (or empty)
    - `card_pill_class` — string, one of `press-release|speech|announcement|newsletter` (class-safe)
    - `card_body_col` — string, column name holding body/excerpt text (or empty to omit)
    - `card_body_length_col` — string, column name holding content-length int (or empty); if set and value is 0, excerpt is forced off even if `card_body_col` is populated
    - `card_source_url_col` — string, column name holding the external source URL (or empty)
    - `card_id_col` — string, column name holding the record SHA/id (or empty)
    - `card_row_href` — string, the row-detail URL (from `urls.row(database, table, pk)` — caller computes; BLK-05: single pk value, NOT a list)

    File contents:

    ```jinja
    {#
      Feed card — generic one-row renderer for news/judgment/guide tables.
      Expected variables (set by caller before include):
        card_row, card_title_col, card_date_col, card_pill_col, card_pill_class,
        card_body_col, card_body_length_col, card_source_url_col, card_id_col, card_row_href
    #}
    {% set _title = card_row.display(card_title_col) if card_title_col else '' %}
    {% set _date = card_row.display(card_date_col) if card_date_col else '' %}
    {% set _pill = card_row.display(card_pill_col) if card_pill_col else '' %}
    {% set _body = card_row.display(card_body_col) if card_body_col else '' %}
    {% set _body_len = card_row[card_body_length_col] if card_body_length_col else none %}
    {% set _src = card_row.display(card_source_url_col) if card_source_url_col else '' %}
    {% set _id = card_row.display(card_id_col) if card_id_col else '' %}

    {# Excerpt is shown iff we have a body column, AND its text is non-empty, AND (if a body-length column exists) the length is > 0 #}
    {% set _show_excerpt = _body and _body|striptags|trim|length > 0 and (card_body_length_col == '' or _body_len is none or _body_len > 0) %}

    <article class="va-item">
      <div class="va-item-head">
        {% if _date %}<span class="date">{{ _date }}</span>{% endif %}
        {% if _pill %}<span class="cat-pill {{ card_pill_class|default('press-release') }}">{{ _pill }}</span>{% endif %}
      </div>

      <h3 class="va-item-title">
        {% if card_row_href %}<a href="{{ card_row_href }}">{{ _title }}</a>{% else %}{{ _title }}{% endif %}
      </h3>

      {% if _show_excerpt %}
      <p class="va-item-excerpt">{{ _body|striptags|truncate(220, true, '…') }}</p>
      {% endif %}

      <div class="va-item-foot">
        {% if _id %}<span class="record-id">Record <code>{{ (_id|string)[:8] }}</code></span>{% endif %}
        {% if _src %}
          {# _src may be HTML-rendered (anchor) by render-markdown; strip tags to get bare URL for host parsing #}
          {% set _src_bare = _src|striptags|trim %}
          <a class="source-host" href="{{ _src_bare }}" rel="noopener" target="_blank">
            Source: {{ _src_bare|replace('https://','')|replace('http://','')|truncate(40, true, '…') }} ↗
          </a>
        {% endif %}
      </div>
    </article>
    ```

    Notes:
    - Uses `row.display(col)` per Datasette convention so render plugins continue to work.
    - `striptags` before truncate guards against included `<a>` wrappers from render plugins leaking into the excerpt.
    - Bare-value access `card_row[col]` is used only for `content_length` (a numeric), not for display — this is fine because numerics don't need render plugins.
    - The `_show_excerpt` gate is the core "graceful collapse" behavior: `about_singapore_law` rows with `content_length=0` omit the excerpt block entirely.
    - SHA truncation: `(_id|string)[:8]` gives a short hash label like `7f3a9c2e`.
  </action>
  <verify>
    <automated>test -f templates/_partials/feed_card.html && grep -q 'row\.display' templates/_partials/feed_card.html && grep -q 'va-item' templates/_partials/feed_card.html && grep -q 'cat-pill' templates/_partials/feed_card.html && grep -q '_show_excerpt' templates/_partials/feed_card.html && grep -q 'card_body_length_col' templates/_partials/feed_card.html && grep -q 'striptags' templates/_partials/feed_card.html</automated>
  </verify>
  <acceptance_criteria>
    - File `templates/_partials/feed_card.html` exists
    - File contains `row.display` (not `row[col]` for display fields)
    - File contains literal `class="va-item"`
    - File contains literal `class="cat-pill"` with the `card_pill_class` interpolation
    - File contains literal `class="va-item-excerpt"` inside a conditional
    - File contains logic `_show_excerpt` combining body-present + body-length check
    - File contains literal `class="va-item-foot"` with `class="source-host"` branch
    - File uses `striptags` before `truncate` on the excerpt
  </acceptance_criteria>
  <done>Shared feed-card partial exists and handles all three row shapes via caller-supplied variable mapping.</done>
</task>

<task type="auto">
  <name>Task 2: Create ten per-table partials — all 8 *_news tables via copy+sed loop, plus judgments and about_singapore_law</name>
  <files>templates/_table-SG-Government-Newsrooms-acra_news.html, templates/_table-SG-Government-Newsrooms-agc_news.html, templates/_table-SG-Government-Newsrooms-ccs_news.html, templates/_table-SG-Government-Newsrooms-ipos_news.html, templates/_table-SG-Government-Newsrooms-judiciary_news.html, templates/_table-SG-Government-Newsrooms-mlaw_news.html, templates/_table-SG-Government-Newsrooms-mom_news.html, templates/_table-SG-Government-Newsrooms-pdpc_news.html, templates/_table-Zeeker-Judgements-judgments.html, templates/_table-Sglawwatch-about_singapore_law.html</files>
  <read_first>
    - templates/_partials/feed_card.html (created in Task 1 — confirm variable names)
    - .planning/notes/datasette-styling-limits.md (section 3 — partial lookup order and full Jinja scope)
    - .claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md (Content-agnostic mapping table)
  </read_first>
  <action>
    **Step A — Create the canonical `*_news` partial (acra_news):**

    Write `templates/_table-SG-Government-Newsrooms-acra_news.html` with the following contents. Note the three bug fixes embedded:

    - **BLK-04 (category pill class via `namespace`)**: computed as `ns.cls` set inside a `namespace(cls=...)` object, then assigned to `card_pill_class` in the outer scope. Do NOT use the `{% set card_pill_class %}` inside `{% if %}/{% elif %}` pattern — that variable does not survive the conditional's scope in Jinja.
    - **BLK-05 (scalar pk to `urls.row`)**: `urls.row(database, table, row[primary_keys[0]])` — pass the scalar pk value. Do NOT wrap in a list. Do NOT build a `pk_vals = []` and append.

    ```jinja
    {#
      _table-SG-Government-Newsrooms-acra_news.html
      Canonical news-feed partial — replaces Datasette's <table class="rows-and-columns"> for *_news tables.
      Keeps filter form, facets, FTS search, sort, pagination, and export pane intact (default table.html still wraps).
    #}
    <div class="va-feed">
      {% for row in display_rows %}
        {% set card_row = row %}
        {% set card_title_col = "title" %}
        {% set card_date_col = "published_date" %}
        {% set card_pill_col = "category" %}

        {# BLK-04: use namespace so cls survives the if/elif scope. #}
        {% set _cat = (row["category"] or '')|lower %}
        {% set ns = namespace(cls='press-release') %}
        {% if 'speech' in _cat %}{% set ns.cls = 'speech' %}
        {% elif 'announcement' in _cat %}{% set ns.cls = 'announcement' %}
        {% elif 'newsletter' in _cat %}{% set ns.cls = 'newsletter' %}
        {% endif %}
        {% set card_pill_class = ns.cls %}

        {% set card_body_col = "content" %}
        {% set card_body_length_col = "" %}
        {% set card_source_url_col = "source_url" %}
        {% set card_id_col = "id" %}

        {# BLK-05: acra_news has a single-column `id` PK. Pass the scalar, NOT a list. #}
        {% set card_row_href = urls.row(database, table, row[primary_keys[0]]) if primary_keys else '' %}

        {% include "_partials/feed_card.html" %}
      {% endfor %}
    </div>

    {% if not display_rows %}
    <p class="va-empty">No rows match the current filters.</p>
    {% endif %}
    ```

    **Step B — Replicate the canonical partial to the other 7 `*_news` tables via a shell loop (WARN-06):**

    Run this exact loop from the repository root AFTER writing the acra_news file above. It duplicates the canonical partial into seven sibling files, substituting `acra` → each agency slug in the comment line only (the partial body is schema-identical, so no body substitutions are required):

    ```bash
    for agency in agc ccs ipos judiciary mlaw mom pdpc; do
      cp templates/_table-SG-Government-Newsrooms-acra_news.html \
         templates/_table-SG-Government-Newsrooms-${agency}_news.html
      # Update the comment header only — body is schema-identical
      # macOS sed (BSD) requires the empty '' after -i
      sed -i '' "s/acra_news/${agency}_news/g" \
         templates/_table-SG-Government-Newsrooms-${agency}_news.html
    done
    ```

    This produces eight total `*_news` partials. All eight share the same canonical body — cheap to maintain, and if the schema changes the executor updates the acra file then re-runs the loop.

    **Step C — Write the judgments partial (`_table-Zeeker-Judgements-judgments.html`):**

    Judgments use a static pill class (`press-release` — petrol — because courts are formal), so the `namespace` pattern is not needed here, but the BLK-05 scalar-pk rule still applies.

    ```jinja
    {#
      _table-Zeeker-Judgements-judgments.html
      Judgment-feed partial — case-name title, court pill, decision_date; citation shown above each card.
    #}
    <div class="va-feed">
      {% for row in display_rows %}
        {% set card_row = row %}
        {% set card_title_col = "case_name" %}
        {% set card_date_col = "decision_date" %}
        {% set card_pill_col = "court" %}
        {% set card_pill_class = "press-release" %}
        {% set card_body_col = "" %}
        {% set card_body_length_col = "" %}
        {% set card_source_url_col = "source_url" %}
        {% set card_id_col = "id" %}

        {# BLK-05: judgments has a single-column `id` PK. Pass the scalar, NOT a list. #}
        {% set card_row_href = urls.row(database, table, row[primary_keys[0]]) if primary_keys else '' %}

        <div class="va-item-wrap">
          {% if row["citation"] %}<div class="va-citation">{{ row.display("citation") }}</div>{% endif %}
          {% include "_partials/feed_card.html" %}
        </div>
      {% endfor %}
    </div>

    {% if not display_rows %}
    <p class="va-empty">No judgments match the current filters.</p>
    {% endif %}
    ```

    **Step D — Write the about_singapore_law partial (`_table-Sglawwatch-about_singapore_law.html`):**

    ```jinja
    {#
      _table-Sglawwatch-about_singapore_law.html
      Legal-guide partial — title + section pill + source; no excerpt block (content_length commonly 0).
    #}
    <div class="va-feed">
      {% for row in display_rows %}
        {% set card_row = row %}
        {% set card_title_col = "title" %}
        {% set card_date_col = "last_scraped" %}
        {% set card_pill_col = "section" %}
        {% set card_pill_class = "speech" %}
        {% set card_body_col = "" %}
        {% set card_body_length_col = "content_length" %}
        {% set card_source_url_col = "item_url" %}
        {% set card_id_col = "id" %}

        {# BLK-05: about_singapore_law has a single-column `id` PK. Pass the scalar, NOT a list. #}
        {% set card_row_href = urls.row(database, table, row[primary_keys[0]]) if primary_keys else '' %}

        {% include "_partials/feed_card.html" %}
      {% endfor %}
    </div>

    {% if not display_rows %}
    <p class="va-empty">No guides match the current filters.</p>
    {% endif %}
    ```

    DO NOT create `table.html` or `_table.html` (the generic fallback) — for tables that have no matching `_table-{db}-{table}.html` partial, Datasette falls back to its default HTML-table rendering, which is correct for short-string/numeric tables and remains out of scope.

    **Post-creation sanity:** After all 10 partials exist, `ls templates/_table-*.html | wc -l` must be >= 10.
  </action>
  <verify>
    <automated>test -f templates/_table-SG-Government-Newsrooms-acra_news.html && test -f templates/_table-SG-Government-Newsrooms-agc_news.html && test -f templates/_table-SG-Government-Newsrooms-ccs_news.html && test -f templates/_table-SG-Government-Newsrooms-ipos_news.html && test -f templates/_table-SG-Government-Newsrooms-judiciary_news.html && test -f templates/_table-SG-Government-Newsrooms-mlaw_news.html && test -f templates/_table-SG-Government-Newsrooms-mom_news.html && test -f templates/_table-SG-Government-Newsrooms-pdpc_news.html && test -f templates/_table-Zeeker-Judgements-judgments.html && test -f templates/_table-Sglawwatch-about_singapore_law.html && grep -q '_partials/feed_card.html' templates/_table-SG-Government-Newsrooms-acra_news.html && grep -q 'card_title_col = "title"' templates/_table-SG-Government-Newsrooms-acra_news.html && grep -q 'card_title_col = "case_name"' templates/_table-Zeeker-Judgements-judgments.html && grep -q 'card_source_url_col = "item_url"' templates/_table-Sglawwatch-about_singapore_law.html && grep -q 'card_body_col = ""' templates/_table-Zeeker-Judgements-judgments.html && grep -q 'display_rows' templates/_table-SG-Government-Newsrooms-acra_news.html && grep -q 'urls.row' templates/_table-SG-Government-Newsrooms-acra_news.html && [ "$(ls templates/_table-*.html 2>/dev/null | wc -l | tr -d ' ')" -ge 10 ] && [ "$(grep -c 'namespace(cls=' templates/_table-SG-Government-Newsrooms-acra_news.html)" -ge 1 ] && ! grep -q 'pk_vals.append' templates/_table-SG-Government-Newsrooms-acra_news.html && ! grep -q 'pk_vals = \[\]' templates/_table-SG-Government-Newsrooms-acra_news.html && curl -s -o /dev/null -w '%{http_code}' "${BASE:-http://127.0.0.1:8001}/SG-Government-Newsrooms/acra_news" | grep -q '^200$'</automated>
  </verify>
  <acceptance_criteria>
    - All ten files exist at the exact paths listed in `files_modified`
    - `ls templates/_table-*.html | wc -l` returns >= 10 (WARN-06)
    - Each file iterates `display_rows` (Datasette's post-filter/facet/sort row set)
    - Each file includes `_partials/feed_card.html`
    - All 8 `*_news` partials use `card_title_col = "title"` and `card_body_col = "content"`
    - All 8 `*_news` partials compute `card_pill_class` from the `category` value via the **`namespace(cls=…)` pattern** — `grep -c 'namespace(cls=' templates/_table-SG-Government-Newsrooms-*_news.html` returns >= 8 (BLK-04)
    - No `*_news` partial contains the `{% set card_pill_class %}` inside `{% if %}/{% elif %}` pattern (BLK-04)
    - judgments uses `card_title_col = "case_name"`, `card_date_col = "decision_date"`, `card_pill_col = "court"`, `card_body_col = ""`
    - judgments renders `citation` above the card via `.va-citation` wrapper
    - about_singapore_law uses `card_title_col = "title"`, `card_pill_col = "section"`, `card_pill_class = "speech"`, `card_source_url_col = "item_url"`, `card_body_col = ""`, `card_body_length_col = "content_length"`
    - **BLK-05**: every partial uses `urls.row(database, table, row[primary_keys[0]])` — `grep -c 'row\[primary_keys\[0\]\]' templates/_table-*.html` returns >= 10
    - **BLK-05**: NO partial contains `pk_vals = []` or `pk_vals.append(` — `grep -c 'pk_vals' templates/_table-*.html` returns 0
    - **BLK-04 functional check**: `curl -s -o /dev/null -w '%{http_code}' "${BASE:-http://127.0.0.1:8001}/SG-Government-Newsrooms/acra_news"` returns `200` (not 500) — template renders without UndefinedError
    - NO file creates or modifies `templates/table.html` — the full `table.html` wrapper continues to be Datasette's default
    - NO file references `render_cell` or `render_row_html` (those hooks are Python plugin hooks, not templates)
  </acceptance_criteria>
  <done>Ten partials exist; each configures the shared card correctly for its schema; category-pill-class uses the canonical `namespace` pattern; row href passes scalar pk; live curl against acra_news returns 200. Datasette's built-in filter/facet/FTS/sort/pagination/export chrome is untouched.</done>
</task>

<task type="auto">
  <name>Task 3: Append FEED CARDS CSS section to static/css/zeeker-base.css</name>
  <files>static/css/zeeker-base.css</files>
  <read_first>
    - static/css/zeeker-base.css — read the TAIL of the file; anchor by `grep 'footer a:link'` to locate the override block, and confirm the `DATABASE EDITORIAL ROWS` section from Plan 04 ends cleanly just before it.
    - .claude/skills/sketch-findings-zeeker-datasette/sources/004-table-as-news-archive/index.html (variant A CSS — `.va-feed`, `.va-item`, `.va-item-head`, `.va-item-title`, `.va-item-excerpt`, `.va-item-foot`, `.source-host`)
  </read_first>
  <action>
    Append this section AFTER the `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` block from Plan 04 and BEFORE the `footer a:link` override. Exact selectors/properties mandatory:

    ```css
    /* =========== FEED CARDS — phase 01 ============ */

    /* Outer feed (replaces Datasette's <table class="rows-and-columns"> when a _table-* partial is present) */
    .va-feed {
      display: flex;
      flex-direction: column;
      gap: var(--space-6);
      margin: var(--space-6) 0 var(--space-12);
    }
    .va-empty {
      padding: var(--space-8) 0;
      font-family: var(--font-mono);
      color: var(--color-text-muted);
      font-size: var(--text-sm);
      text-align: center;
    }

    /* Judgment citation line (sits above a card) */
    .va-item-wrap { display: contents; }
    .va-citation {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--color-terracotta);
      text-transform: uppercase;
      letter-spacing: var(--tracking-caps);
      margin-bottom: -1px; /* nudge closer to the card that follows */
    }

    /* News/judgment/guide card */
    .va-item {
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-left: 3px solid var(--color-accent);
      padding: var(--space-5) var(--space-6);
      transition: border-left-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
    }
    .va-item:hover {
      border-left-color: var(--color-ochre);
      transform: translateY(-1px);
      box-shadow: var(--shadow-sm);
    }

    .va-item-head {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      margin-bottom: var(--space-3);
      flex-wrap: wrap;
    }
    .va-item-head .date {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--color-text-muted);
      text-transform: uppercase;
      letter-spacing: var(--tracking-wide);
    }

    .va-item-title {
      font-family: var(--font-display);
      font-size: var(--text-2xl);
      font-weight: 500;
      color: var(--color-ink);
      letter-spacing: -0.01em;
      line-height: 1.2;
      margin: 0 0 var(--space-3);
    }
    .va-item-title a,
    .va-item-title a:link,
    .va-item-title a:visited {
      color: var(--color-ink);
      text-decoration: none;
    }
    .va-item-title a:hover { color: var(--color-accent); text-decoration: none; }

    .va-item-excerpt {
      font-family: var(--font-body);
      font-size: var(--text-base);
      color: var(--color-text-secondary);
      line-height: 1.55;
      margin: 0 0 var(--space-4);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .va-item-foot {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: var(--space-3);
      flex-wrap: wrap;
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--color-text-muted);
      text-transform: uppercase;
      letter-spacing: var(--tracking-wide);
      border-top: 1px solid var(--color-border);
      padding-top: var(--space-3);
    }
    .va-item-foot .record-id code {
      background: transparent;
      padding: 0;
      color: var(--color-text-muted);
      font-family: inherit;
      font-size: inherit;
    }
    .source-host,
    .source-host:link,
    .source-host:visited {
      color: var(--color-accent);
      text-decoration: none;
      font-family: var(--font-mono);
    }
    .source-host:hover { color: var(--color-accent-hover); text-decoration: underline; }

    @media (max-width: 640px) {
      .va-item { padding: var(--space-4); }
      .va-item-title { font-size: var(--text-xl); }
      .va-item-excerpt { -webkit-line-clamp: 3; }
    }
    ```

    Constraints:
    - Place AFTER the DATABASE EDITORIAL ROWS section and BEFORE the `footer a:link` override.
    - The `footer a:link` override MUST remain in the last 20 lines of the file after this edit (WARN-05).
    - Do not modify other sections.
  </action>
  <verify>
    <automated>grep -q 'FEED CARDS — phase 01' static/css/zeeker-base.css && grep -q '\.va-feed {' static/css/zeeker-base.css && grep -q '\.va-item {' static/css/zeeker-base.css && grep -q '\.va-item-head' static/css/zeeker-base.css && grep -q '\.va-item-title' static/css/zeeker-base.css && grep -q '\.va-item-excerpt' static/css/zeeker-base.css && grep -q '\.va-item-foot' static/css/zeeker-base.css && grep -q '\.source-host' static/css/zeeker-base.css && grep -q '\.va-citation' static/css/zeeker-base.css && grep -q 'border-left: 3px solid var(--color-accent)' static/css/zeeker-base.css && grep -q 'footer a:link' static/css/zeeker-base.css && tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'</automated>
  </verify>
  <acceptance_criteria>
    - Banner `/* =========== FEED CARDS — phase 01 ============ */` present
    - `.va-feed` with `display: flex; flex-direction: column` present
    - `.va-item` with `border-left: 3px solid var(--color-accent)` present
    - `.va-item:hover` shifts `border-left-color` to `var(--color-ochre)`
    - `.va-item-title` uses `font-family: var(--font-display)`, `font-size: var(--text-2xl)`
    - `.va-item-excerpt` uses `-webkit-line-clamp: 2` for 2-line truncation
    - `.va-item-foot` includes `.record-id` styling
    - `.source-host` uses `color: var(--color-accent)` and `font-family: var(--font-mono)`
    - `.va-citation` uses `color: var(--color-terracotta)` (judgment-specific kicker)
    - `footer a:link` override block still present at end of file
    - `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` returns 0 (WARN-05)
  </acceptance_criteria>
  <done>Feed card CSS appended; partials render as cards without touching table.html wrapper; footer override still in last 20 lines.</done>
</task>

</tasks>

<verification>
Using a dev server with the real databases attached (or fixtures for the no-real-data path). Set `$BASE` default to `http://127.0.0.1:8001`; allow override via env var.

1. Load `$BASE/SG-Government-Newsrooms/acra_news` — cards render (not HTML table); each has date + category pill + title + excerpt (if body present) + SHA + Source ↗ link. HTTP 200 not 500 (BLK-04 resolved).
2. Repeat for all 8 `*_news` tables (agc, ccs, ipos, judiciary, mlaw, mom, pdpc): same visual pattern, 200 response.
3. Confirm Datasette's chrome is intact:
   - Filter form at top — still renders
   - Facets sidebar on right — still renders
   - FTS search box (if FTS enabled) — still renders and works (`?_search=term` filters)
   - Pagination — `.next` link visible at bottom; click paginates
   - Export links — `.csv` / `.json` / advanced-export pane all still render
4. Load `$BASE/SG-Government-Newsrooms/acra_news?_search=budget` — filtered card list still rendered as cards.
5. Load `$BASE/Zeeker-Judgements/judgments` — card list with citation mono line above each card, case-name title, court pill, decision_date.
6. Load `$BASE/Sglawwatch/about_singapore_law` — cards with title + section pill + source link; NO excerpt block (content_length is 0 for all or most rows, which triggers `_show_excerpt = false`).
7. Load a table WITHOUT a partial (e.g. `/fixtures/facetable`) — default Datasette HTML-table row rendering preserved; no regression.
8. **BLK-05 URL check**: `curl -s $BASE/SG-Government-Newsrooms/acra_news | grep -oE 'href="/SG-Government-Newsrooms/acra_news/[^"]+"' | head -3` — the extracted row URLs must NOT contain `[` or `]` brackets. Expect values like `/SG-Government-Newsrooms/acra_news/7f3a9c2e...`, NOT `/SG-Government-Newsrooms/acra_news/['7f3a9c2e...']`.
9. `curl -s $BASE/SG-Government-Newsrooms/acra_news.csv -o /dev/null -w '%{http_code}'` returns 200 (CSV export still works).
10. `curl -s "$BASE/SG-Government-Newsrooms/acra_news.json?_shape=array" -o /dev/null -w '%{http_code}'` returns 200.
</verification>

<success_criteria>
- All ten `_table-*.html` partials exist at the exact paths listed.
- `_partials/feed_card.html` exists and handles `_show_excerpt` gate.
- All feed-card CSS classes present in `zeeker-base.css`.
- Datasette's filter / facet / FTS / sort / pagination / CSV / JSON / advanced-export machinery all continue to render and function on feed pages.
- Guide table (content_length=0) renders cards without excerpt block.
- News tables render cards WITH excerpt.
- `templates/table.html` itself was NOT modified.
- BLK-04: curl against acra_news returns 200 (no UndefinedError from pill-class scope bug).
- BLK-05: row URLs contain no `[` or `]` in the path component (scalar pk in use).
- WARN-06: all 8 `*_news` tables have partials (wc -l >= 10).
- WARN-05: footer override still within final 20 lines of CSS file.
</success_criteria>

<output>
Create `.planning/phases/01-editorial-shell-home-inventory/01-05-table-feed-partials-SUMMARY.md` documenting:
- The ten partials shipped and which schema each targets.
- The shared `_partials/feed_card.html` variable contract (names + types).
- Confirmation that `table.html` was not modified.
- Confirmation that filter/facet/FTS/sort/pagination/export machinery still functions (document the manual verification steps run).
- Confirmation that every `*_news` partial uses the `namespace(cls=…)` pattern (BLK-04) and the scalar-pk pattern (BLK-05).
- Any render-plugin compatibility observations (`row.display` vs `row[col]` correctness).
</output>
</content>
