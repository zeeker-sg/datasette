---
phase: 01-editorial-shell-home-inventory
plan: 04
type: execute
wave: 4
depends_on: ["01", "02", "03"]
files_modified:
  - templates/database.html
  - static/css/zeeker-base.css
autonomous: true
requirements:
  - SC-01-database-editorial-rows
  - SC-01-database-hero
  - SC-01-database-statband
  - SC-01-sticky-toolbar
must_haves:
  truths:
    - "`/{db}` renders the asymmetric hero (italic H1 + meta-col) + petrol stat band + sticky `.db-toolbar` + editorial-row list of tables"
    - "Each table row shows: mono index, display-serif title, mono column list with PK highlighted, right-aligned display-serif row count, FTS badge when table has FTS"
    - "Row hover shifts background to `--color-bg-alt` and a petrol left-edge slider appears"
    - "`/fixtures` still returns 200 (no regression of today's `metadata.get('tables', {}).get(name)` fix)"
    - "The sticky `.db-toolbar` renders a table-filter search form that POSTs via GET to the current `/{database}` page (uses Datasette's built-in `_search=` query parameter if available, else a simple `?q=` filter the template reads)"
  artifacts:
    - path: "templates/database.html"
      provides: "Sketch 002-B editorial-row database page with sticky sub-toolbar"
      contains: "class=\"list\""
    - path: "static/css/zeeker-base.css"
      provides: ".list / .row / .row .idx / .name / .desc / .cols / .count-col / .count / .label / .date-col CSS"
      contains: ".row::before"
  key_links:
    - from: "templates/database.html"
      to: "metadata.get('tables', {}).get(name) safe-access pattern (today's bug fix)"
      via: "Jinja expression"
      pattern: "metadata.get\\('tables', \\{\\}\\)\\.get"
    - from: ".row:hover"
      to: ".row::before (petrol left-edge slider)"
      via: "sibling pseudo-element transition"
      pattern: "\\.row:hover::before"
    - from: "templates/database.html .db-toolbar"
      to: "Datasette's table-filter query string"
      via: "GET form on /{database}"
      pattern: "class=\"db-toolbar\""
---

<objective>
Replace the grid-of-cards table listing in `templates/database.html` with the sketch 002-B full-width editorial-row pattern, and append the editorial-row CSS to `static/css/zeeker-base.css`. Each table renders as one row with display-serif title, mono column list, right-aligned row count, and optional FTS badge — scales to 20+ tables without visual clutter. Adds the sticky `.db-toolbar` (defined in Plan 02) with a table-filter search input so the component Plan 02 shipped actually has a consumer on this page.

Purpose: The current database page uses stacked cards that collapse into unreadable mush past 6-8 tables. `SG-Government-Newsrooms` has 20+ `*_news` tables, making the cards pattern unusable at that scale. Editorial rows solve that: one vertical column the eye scans by title, with right-edge row counts as the second anchor. The sticky toolbar keeps search/filter controls on-screen while the user scrolls a long list.

Output: Rewritten `templates/database.html` main content using `.db-header` + `.db-statband` + `.db-toolbar` (from Plan 02 shell) + new `.list` + `.row` editorial-row pattern. All editorial-row CSS appended to `zeeker-base.css` in a `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` banner section. No regression of today's `metadata.get('tables', {}).get(name)` safe-access pattern. Retain Datasette's built-in views list and canned queries sections.

Note on dead CSS (WARN-09): Dead CSS selectors such as `.tables-grid`, `.table-card`, `.database-card` may remain in `static/css/zeeker-base.css` — removal is a future polish pass. This plan only requires the TEMPLATES to be purged of those class references; dead rules in the CSS file are tolerated.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md
@.claude/skills/sketch-findings-zeeker-datasette/references/shell-and-chrome.md
@.claude/skills/sketch-findings-zeeker-datasette/sources/002-database-table-grid/index.html
@.planning/phases/01-editorial-shell-home-inventory/01-02-shared-chrome-SUMMARY.md
@.planning/phases/01-editorial-shell-home-inventory/01-03-home-editorial-SUMMARY.md
@.planning/notes/datasette-styling-limits.md
@templates/database.html
@templates/_header.html

<interfaces>
Datasette's `database.html` view passes this Jinja context (`datasette/views/database.py`):

- `database`: string (the database route slug — used in URL construction like `/{{ database }}/{{ table.name }}`)
- `tables`: list of dicts with:
  - `name` (table name)
  - `count` (int, row count; may be `None` for very large tables before count finishes)
  - `columns` (list of column name strings)
  - `primary_keys` (list of column names)
  - `hidden` (bool)
  - `fts_table` (truthy when FTS is enabled, string name of FTS shadow table)
  - `fts` (alias)
  - `human_description_en` (optional description string)
- `views`: list of dicts (similar shape, without `count`)
- `canned_queries`: list with `name`, `title`, `description`
- `metadata`: dict with database-level `title`, `description`, `license`, `source`, and possibly `tables: {table_name: {title, description, columns: {...}}}`
- `size`: int bytes (database file size)
- `search_query` / `search_results`: optional search-over-tables feature — if set, Datasette is already filtering `tables` server-side by name/description match

SAFE-ACCESS PATTERN (critical — protects `/fixtures` from 500):
```jinja
{% set table_meta = metadata.get('tables', {}).get(table.name) or {} %}
```
Do NOT revert to `metadata.tables[table.name]` (raises under StrictUndefined when `tables` key is absent).

Shell CSS classes from Plan 02 consumable:
- `.db-nav`, `.db-crumb` — rendered by `_header.html` when breadcrumbs set
- `.db-header`, `.db-header-grid`, `.db-header h1 em`, `.db-header .lede`, `.db-header .meta-col` / `dt` / `dd`
- `.db-statband`, `.db-statband .stat-num`, `.db-statband .stat-label`
- `.db-toolbar`, `.db-toolbar-search` — the sticky sub-toolbar (WARN-02: this plan consumes it)
- `.kicker`, `.fts-badge`

Hidden tables to skip: `{% if not table.hidden and not table.name.startswith('_zeeker') %}` (retain this pattern — `_zeeker_*` metadata tables are explicitly hidden per CLAUDE.md).

The existing `metadata.json` sets `allow_sql: true`, `allow_facet: true`, `allow_download: true` on `"*"` — so CSV/JSON/SQLite download links on the hero meta-col can rely on those being allowed.

**Table-filter search in the toolbar:** Datasette's `/{database}` view accepts a `?_search=...` query parameter which filters the tables list server-side (matches against table name + description). Forms can submit `method="get" action="/{{ database }}"` with `<input name="_search">`; Datasette re-renders the page with `tables` already pre-filtered. This is the simplest consumer for `.db-toolbar-search` and requires NO Python changes.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite templates/database.html main content to sketch 002-B hero + statband + sticky toolbar + editorial-row list</name>
  <files>templates/database.html</files>
  <read_first>
    - templates/database.html (current — cards-based tables section with today's bug fix at line 109)
    - .claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md (full — especially "Database row (sketch 002)" HTML structure)
    - .claude/skills/sketch-findings-zeeker-datasette/sources/002-database-table-grid/index.html (variant B HTML — search for `vb-` prefixed class names)
    - .planning/notes/datasette-styling-limits.md (section 1 — Jinja StrictUndefined)
  </read_first>
  <action>
    Rewrite `templates/database.html` main content (the `{% block content %}` body), preserving:
    - `{% extends "default:database.html" %}` at top
    - `{% block extra_head %}` (keep as-is or update meta-description)
    - `{% block nav %}` set-breadcrumbs + include `_header.html` (already updated in Plan 02 Task 1.5 — breadcrumbs should NOT include a Home entry)
    - `{% block footer %}` include `_footer.html`

    Replace `{% block content %}` with this structure (exact class names mandatory).

    **BLK-03 fix — compute `vt` once at the top of `{% block content %}` using Jinja's canonical `selectattr`/`rejectattr` chain. Do NOT use the mutation-through-reference pattern (`vt = []` + `vt.append`). Do NOT reference a nonexistent `matching_zeeker` filter.**

    ```jinja
    {% block content %}
    {# --- Compute the visible-tables list ONCE (BLK-02, BLK-03) ------- #}
    {# Filter: not hidden AND name does not match ^_zeeker.* #}
    {% set vt = tables|selectattr('hidden','ne',true)|rejectattr('name','match','^_zeeker.*')|list %}

    {# --- Editorial hero ------------------------------------------- #}
    <header class="db-header">
      <div class="container">
        <div class="db-header-grid">
          <div>
            <div class="kicker">№ 01 · Database</div>
            <h1>
              {% set db_title = metadata.title if metadata and metadata.title else (database|replace('-', ' ')|replace('_', ' ')|title) %}
              {# WARN-04: split on the LAST space so only the trailing word gets italicized #}
              {% if ' ' in db_title %}
                {% set idx = db_title.rfind(' ') %}
                {{ db_title[:idx] }} <em>{{ db_title[idx+1:] }}</em>
              {% else %}
                <em>{{ db_title }}</em>
              {% endif %}
            </h1>
            {% if metadata and metadata.description %}
            <p class="lede">{{ metadata.description }}</p>
            {% endif %}
          </div>
          <dl class="meta-col">
            {% if size is defined and size %}
            <dt>Size</dt>
            <dd>{{ size|filesizeformat }}</dd>
            {% endif %}
            {% if metadata and metadata.license %}
            <dt>Licence</dt>
            <dd>
              {% if metadata.license_url %}<a href="{{ metadata.license_url }}">{{ metadata.license }}</a>
              {% else %}{{ metadata.license }}{% endif %}
            </dd>
            {% endif %}
            {% if metadata and metadata.source %}
            <dt>Source</dt>
            <dd>
              {% if metadata.source_url %}<a href="{{ metadata.source_url }}">{{ metadata.source }}</a>
              {% else %}{{ metadata.source }}{% endif %}
            </dd>
            {% endif %}
            <dt>Export</dt>
            <dd class="export-links">
              <a href="/{{ database }}.csv">CSV</a>
              <a href="/{{ database }}.json">JSON</a>
              <a href="/{{ database }}.db">SQLite</a>
            </dd>
          </dl>
        </div>
      </div>
    </header>

    {# --- Petrol stat band ---------------------------------------- #}
    {% set total_rows_ns = namespace(total=0) %}
    {% for t in vt %}
      {% if t.count is not none %}
        {% set total_rows_ns.total = total_rows_ns.total + t.count %}
      {% endif %}
    {% endfor %}
    <div class="db-statband">
      <div class="container">
        <div>
          <div class="stat-num">{{ vt|length }}</div>
          <span class="stat-label">{{ plural(vt|length, 'plural_table', 'plural_tables') }}</span>
        </div>
        {% if total_rows_ns.total > 0 %}
        <div>
          <div class="stat-num">{{ "{:,}".format(total_rows_ns.total) }}</div>
          <span class="stat-label">total rows</span>
        </div>
        {% endif %}
        {% if size is defined and size %}
        <div>
          <div class="stat-num">{{ size|filesizeformat }}</div>
          <span class="stat-label">on disk</span>
        </div>
        {% endif %}
        <div>
          <div class="stat-num">SQL</div>
          <span class="stat-label">
            <a href="/{{ database }}?sql=SELECT+name+FROM+sqlite_master+WHERE+type%3D%27table%27" style="color: inherit; text-decoration: underline;">open query</a>
          </span>
        </div>
      </div>
    </div>

    {# --- Sticky sub-toolbar (WARN-02 — consumes .db-toolbar from Plan 02) --- #}
    <div class="db-toolbar">
      <div class="container">
        <form class="db-toolbar-search" method="get" action="/{{ database }}" role="search">
          <label for="db-table-filter" class="visually-hidden">Filter tables</label>
          <input id="db-table-filter" type="search" name="_search"
                 value="{{ search_query if search_query is defined and search_query else '' }}"
                 placeholder="Filter tables by name or description…"
                 autocomplete="off">
          <button type="submit">Filter</button>
        </form>
        <a class="fts-badge" href="/{{ database }}?sql=SELECT+*+FROM+sqlite_master+WHERE+type%3D%27table%27">Schema</a>
      </div>
    </div>

    {# --- Search-results banner (retained from existing) ---------- #}
    {% if search_query %}
    <div class="container" style="padding-top: var(--space-8);">
      <div class="kicker">Search results</div>
      <h2 style="font-family: var(--font-display); font-size: var(--text-2xl); margin-top: var(--space-2);">
        {% if search_results %}
          {{ search_results|length }} match{% if search_results|length != 1 %}es{% endif %} for “{{ search_query }}”
        {% else %}
          No tables match “{{ search_query }}”
        {% endif %}
      </h2>
    </div>
    {% endif %}

    {# --- № 01 · Tables (editorial rows) -------------------------- #}
    {% if vt %}
    <section class="section">
      <div class="container">
        <div class="section-num">№ 01 · Tables</div>
        <div class="list">
          {% for table in vt %}
            {% set table_meta = metadata.get('tables', {}).get(table.name) or {} %}
            <div class="row">
              <div class="idx">{{ "{:02d}".format(loop.index) }}</div>
              <div class="name-col">
                <a href="/{{ database }}/{{ table.name }}" class="name">
                  {% if table_meta.title %}{{ table_meta.title }}{% else %}{{ table.name|replace('_', ' ')|title }}{% endif %}
                </a>
                {% if table_meta.description %}
                <div class="desc">{{ table_meta.description }}</div>
                {% elif table.human_description_en %}
                <div class="desc">{{ table.human_description_en }}</div>
                {% endif %}
              </div>
              <div class="cols">
                {% if table.columns %}
                  {% for col in table.columns[:8] %}{% if not loop.first %} · {% endif %}<span class="{% if col in (table.primary_keys or []) %}pk{% endif %}">{{ col }}</span>{% endfor %}
                  {% if table.columns|length > 8 %} <span class="more">+{{ table.columns|length - 8 }}</span>{% endif %}
                {% endif %}
              </div>
              <div class="count-col">
                {% if table.count is not none %}
                <span class="count">{{ "{:,}".format(table.count) }}</span>
                <span class="label">rows</span>
                {% else %}
                <span class="count">—</span>
                <span class="label">rows</span>
                {% endif %}
              </div>
              <div class="date-col">
                {% if table.fts_table or table.fts %}<span class="fts-badge">FTS</span><br>{% endif %}
                <a href="/{{ database }}/{{ table.name }}.csv">CSV</a> ·
                <a href="/{{ database }}/{{ table.name }}.json">JSON</a>
              </div>
            </div>
          {% endfor %}
        </div>
      </div>
    </section>
    {% else %}
    <section class="section">
      <div class="container">
        <p>No tables yet in this database.</p>
      </div>
    </section>
    {% endif %}

    {# --- Views (retained) --------------------------------------- #}
    {% if views %}
    <section class="section alt">
      <div class="container">
        <div class="section-num">№ 02 · Views</div>
        <div class="list">
          {% for view in views %}
          <div class="row">
            <div class="idx">{{ "{:02d}".format(loop.index) }}</div>
            <div class="name-col">
              <a href="/{{ database }}/{{ view.name }}" class="name">{{ view.name|replace('_', ' ')|title }}</a>
              {% if view.description %}<div class="desc">{{ view.description }}</div>{% endif %}
            </div>
            <div class="cols"></div>
            <div class="count-col"><span class="count">view</span><span class="label">&nbsp;</span></div>
            <div class="date-col"><a href="/{{ database }}/{{ view.name }}.json">JSON</a></div>
          </div>
          {% endfor %}
        </div>
      </div>
    </section>
    {% endif %}

    {# --- Canned queries (retained) ------------------------------ #}
    {% if canned_queries %}
    <section class="section">
      <div class="container">
        <div class="section-num">№ 03 · Saved queries</div>
        <div class="list">
          {% for query in canned_queries %}
          <div class="row">
            <div class="idx">{{ "{:02d}".format(loop.index) }}</div>
            <div class="name-col">
              <a href="/{{ database }}/{{ query.name }}" class="name">{{ query.title }}</a>
              {% if query.description %}<div class="desc">{{ query.description }}</div>{% endif %}
            </div>
            <div class="cols"></div>
            <div class="count-col"></div>
            <div class="date-col"><a href="/{{ database }}/{{ query.name }}.json">JSON</a></div>
          </div>
          {% endfor %}
        </div>
      </div>
    </section>
    {% endif %}
    {% endblock %}
    ```

    DO-NOT-REGRESS rules:
    - Keep `{% extends "default:database.html" %}` line 1.
    - Keep `{% block nav %}` set-breadcrumbs + include `_header.html` intact (Plan 02 Task 1.5 already updated the crumb format — DO NOT re-add Home entry).
    - Keep `{% block footer %}{% include "_footer.html" %}{% endblock %}` (note: base `database.html` already handles footer via its template; only override if the current file does — preserve current behavior).
    - The `metadata.get('tables', {}).get(table.name) or {}` safe-access pattern is MANDATORY on every table metadata lookup.
    - The `vt` filter uses `selectattr('hidden','ne',true)|rejectattr('name','match','^_zeeker.*')` (BLK-03) — NOT the old `vt = [] ; vt.append` mutation pattern.
    - Do NOT reference any `matching_zeeker` filter (BLK-02 — the filter does not exist).
    - Do NOT touch the top-of-file `{% block extra_head %}` beyond the existing meta-description block.

    **Explicit prohibitions (must NOT appear anywhere in the output file):**
    - The literal line `{% set visible_tables = tables|rejectattr('hidden')|reject('matching_zeeker')|list if tables else [] %}` or any `matching_zeeker` reference (BLK-02).
    - The `{% set vt = [] %}` / `{% set _ = vt.append(t) %}` mutation pattern (BLK-03).
    - The `{% set parts = db_title.split(' ', 1) %}` first-space split pattern (WARN-04 — use `rfind` on last space instead).
    - The `"%02d"|format(loop.index0 + 1) if loop is defined` expression — replace with literal `№ 01 · Database` (WARN-03). `loop` is not defined outside a `{% for %}` — the guard was a cosmetic bug.
  </action>
  <verify>
    <automated>grep -q 'class="db-header"' templates/database.html && grep -q 'class="db-statband"' templates/database.html && grep -q 'class="db-toolbar"' templates/database.html && grep -q 'class="list"' templates/database.html && grep -q 'class="row"' templates/database.html && grep -q "metadata.get('tables', {}).get" templates/database.html && grep -q "startswith('_zeeker')\|_zeeker" templates/database.html && grep -q 'class="fts-badge"' templates/database.html && grep -q 'class="kicker"' templates/database.html && grep -q '№ 01 · Tables' templates/database.html && ! grep -q 'tables-grid' templates/database.html && ! grep -q 'table-card' templates/database.html && [ "$(grep -c 'matching_zeeker' templates/database.html)" = "0" ] && [ "$(grep -c 'selectattr' templates/database.html)" -ge "1" ] && ! grep -q "vt.append" templates/database.html && ! grep -q "split(' ', 1)" templates/database.html && grep -q 'rfind' templates/database.html</automated>
  </verify>
  <acceptance_criteria>
    - `templates/database.html` contains literal `class="db-header"`
    - `templates/database.html` contains literal `class="db-statband"`
    - `templates/database.html` contains literal `class="db-toolbar"` (WARN-02 — consumer present)
    - `templates/database.html` contains literal `class="db-toolbar-search"` form posting to `/{{ database }}` with `name="_search"`
    - `templates/database.html` contains literal `class="list"` and `class="row"`
    - `templates/database.html` contains the `metadata.get('tables', {}).get(table.name)` safe-access pattern (today's fix preserved)
    - `grep -c 'matching_zeeker' templates/database.html` returns 0 (BLK-02)
    - `grep -c 'selectattr' templates/database.html` returns >= 1 (BLK-03 — canonical filter chain in use)
    - `grep -c 'vt.append' templates/database.html` returns 0 (BLK-03 — mutation pattern removed)
    - `grep -c "split(' ', 1)" templates/database.html` returns 0 (WARN-04 — first-space split removed)
    - `grep -c 'rfind' templates/database.html` returns >= 1 (WARN-04 — last-space split used)
    - `grep -c 'loop.index0 + 1' templates/database.html` returns 0 (WARN-03 — cosmetic `loop is defined` guard removed)
    - `templates/database.html` contains literal `№ 01 · Database` as a hardcoded kicker string (WARN-03)
    - `templates/database.html` contains `class="fts-badge"` on the FTS-enabled branch
    - `templates/database.html` contains literal `№ 01 · Tables`
    - `templates/database.html` does NOT contain `tables-grid` or `table-card` (old cards pattern removed — template only; dead CSS per WARN-09 is tolerated)
    - `{% extends "default:database.html" %}` retained at line 1
    - `{% block nav %}` with `_header.html` include retained (DO NOT re-add Home to breadcrumbs)
    - Views and canned_queries sections retained
  </acceptance_criteria>
  <done>Database page renders as editorial rows with sticky filter toolbar, uses canonical `selectattr` filter for zeeker-table hiding, uses `rfind` for last-space italic split, uses literal kicker string; FTS badge shows on searchable tables; `/fixtures` still returns 200.</done>
</task>

<task type="auto">
  <name>Task 2: Append DATABASE EDITORIAL ROWS CSS section to static/css/zeeker-base.css</name>
  <files>static/css/zeeker-base.css</files>
  <read_first>
    - static/css/zeeker-base.css — read the TAIL of the file to confirm the HOME section end and locate the `footer a:link` override block. Anchor by `grep 'footer a:link'`.
    - .claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md (CSS Patterns → "Editorial row (shared base)")
  </read_first>
  <action>
    Append this section AFTER the `/* =========== HOME — phase 01 ============ */` block from Plan 03 and BEFORE the existing `footer a:link` override. Exact selectors/properties mandatory:

    ```css
    /* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */

    .list {
      border-top: 2px solid var(--color-ink);
    }
    .row {
      display: grid;
      grid-template-columns: 60px 1fr 280px 130px 130px;
      gap: var(--space-6);
      align-items: baseline;
      padding: var(--space-6) 0;
      border-bottom: 1px solid var(--color-border);
      transition: background 0.2s ease, padding 0.2s ease, margin 0.2s ease;
      position: relative;
    }
    .row::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      width: 0;
      height: 0;
      background: var(--color-accent);
      transition: width 0.2s ease, height 0.2s ease, left 0.2s ease;
      transform: translateY(-50%);
    }
    .row:hover {
      background: var(--color-bg-alt);
      padding-left: var(--space-6);
      padding-right: var(--space-4);
      margin-left: calc(-1 * var(--space-6));
      margin-right: calc(-1 * var(--space-4));
    }
    .row:hover::before {
      width: 3px;
      height: 60%;
      left: -3px;
    }
    .row:hover .name { color: var(--color-accent); }

    .row .idx {
      font-family: var(--font-mono);
      color: var(--color-text-muted);
      font-size: var(--text-sm);
    }
    .row .name-col { min-width: 0; }
    .row .name,
    .row .name:link,
    .row .name:visited {
      font-family: var(--font-display);
      font-size: var(--text-3xl);
      font-weight: 500;
      color: var(--color-ink);
      letter-spacing: -0.01em;
      line-height: 1.1;
      display: block;
      margin-bottom: var(--space-2);
      text-decoration: none;
      transition: color 0.15s ease;
    }
    .row .name:hover { color: var(--color-accent); text-decoration: none; }
    .row .desc {
      color: var(--color-text-muted);
      font-size: var(--text-sm);
      line-height: 1.5;
      margin: 0;
    }
    .row .cols {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--color-text-secondary);
      line-height: 1.7;
      word-break: break-word;
    }
    .row .cols .pk {
      color: var(--color-accent);
      font-weight: 600;
    }
    .row .cols .more {
      color: var(--color-text-muted);
      font-style: italic;
    }
    .row .count-col { text-align: right; }
    .row .count {
      font-family: var(--font-display);
      font-size: var(--text-3xl);
      font-weight: 500;
      color: var(--color-ink);
      display: block;
      line-height: 1;
    }
    .row .label {
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--color-text-muted);
      text-transform: uppercase;
      letter-spacing: var(--tracking-wide);
      margin-top: 4px;
      display: block;
    }
    .row .date-col {
      text-align: right;
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--color-text-muted);
      line-height: 1.7;
    }
    .row .date-col a { color: var(--color-text-secondary); }
    .row .date-col a:hover { color: var(--color-accent); text-decoration: none; }

    /* Meta-col export-links variant on database hero */
    .db-header .meta-col dd.export-links {
      font-family: var(--font-mono);
      font-size: var(--text-sm);
      display: flex;
      gap: var(--space-3);
    }
    .db-header .meta-col dd.export-links a {
      color: var(--color-accent);
      text-decoration: none;
    }
    .db-header .meta-col dd.export-links a:hover { color: var(--color-accent-hover); text-decoration: underline; }

    @media (max-width: 960px) {
      .row {
        grid-template-columns: 40px 1fr 110px;
        gap: var(--space-3);
      }
      .row .cols,
      .row .date-col {
        display: none;
      }
      .row .name { font-size: var(--text-xl); }
      .row .count { font-size: var(--text-xl); }
    }
    ```

    Constraints:
    - Place AFTER the HOME block from Plan 03 and BEFORE the `footer a:link` override.
    - The `footer a:link` override MUST remain in the last 20 lines of the file after this edit (WARN-05).
    - Do not modify any rule in previous sections.
  </action>
  <verify>
    <automated>grep -q 'DATABASE EDITORIAL ROWS — phase 01' static/css/zeeker-base.css && grep -q '\.list {' static/css/zeeker-base.css && grep -q '\.row {' static/css/zeeker-base.css && grep -q '\.row::before' static/css/zeeker-base.css && grep -q '\.row:hover::before' static/css/zeeker-base.css && grep -q '\.row \.name' static/css/zeeker-base.css && grep -q '\.row \.cols \.pk' static/css/zeeker-base.css && grep -q '\.row \.count-col' static/css/zeeker-base.css && grep -q 'grid-template-columns: 60px 1fr 280px 130px 130px' static/css/zeeker-base.css && grep -q 'footer a:link' static/css/zeeker-base.css && tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'</automated>
  </verify>
  <acceptance_criteria>
    - Banner `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` present
    - `.list` selector has `border-top: 2px solid var(--color-ink)`
    - `.row` selector has `grid-template-columns: 60px 1fr 280px 130px 130px`
    - `.row::before` pseudo-element defined with `background: var(--color-accent)`
    - `.row:hover::before` has `width: 3px` (the slider)
    - `.row .name` set to `font-family: var(--font-display)`, `font-size: var(--text-3xl)`
    - `.row .cols .pk` set to `color: var(--color-accent)`, `font-weight: 600`
    - `.row .count` set to `font-family: var(--font-display)`, `font-size: var(--text-3xl)`
    - `@media (max-width: 960px)` rule collapses `.row .cols` and `.row .date-col` to `display: none`
    - `footer a:link` override block still present
    - `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` returns 0 (WARN-05)
  </acceptance_criteria>
  <done>Editorial-row CSS appended; database page renders rows with petrol slider on hover and PK highlight on columns; footer override still in last 20 lines.</done>
</task>

</tasks>

<verification>
1. `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/fixtures` returns `200` (today's bug fix preserved).
2. Load `http://127.0.0.1:8001/fixtures` — dark nav + `HOME › FIXTURES` crumb + warm hero with italic H1 (only the LAST word italicized) + petrol stat band + sticky `.db-toolbar` filter strip + editorial rows for each table with FTS badge where applicable.
3. Hover any row — background shifts to warm `--color-bg-alt`, a 3px petrol slider appears on the left edge, table name changes to petrol.
4. Load `http://127.0.0.1:8001/SG-Government-Newsrooms` (if available on dev server) — all 20+ `*_news` tables render as rows, scannable vertically. Hero H1 italicizes the LAST word (e.g. `SG Government` + italic `Newsrooms`).
5. Type `news` into the sticky toolbar filter and submit → URL becomes `/SG-Government-Newsrooms?_search=news`, table list filters to tables matching `news`.
6. Mobile viewport (390x844) — columns collapse to `idx | name+desc | count`, `.cols` and `.date-col` hidden.
7. `curl` the rendered database page and confirm `grep -c 'matching_zeeker'` on the HTML response body returns 0 (no stale filter reference leaked through).
</verification>

<success_criteria>
- Database page renders editorial rows for all real databases without 500 errors.
- `/fixtures` still returns 200 (today's bug fix preserved).
- FTS badge shows on FTS-enabled tables.
- Row hover produces petrol left-edge slider.
- PK columns highlighted in petrol in the column list.
- `.db-toolbar` filter form renders and submits to `/{database}?_search=...` (WARN-02).
- Zero `matching_zeeker` references remain (BLK-02).
- Canonical `selectattr`/`rejectattr` filter chain is used for the visible-tables list (BLK-03).
- Hero H1 italicizes the last word only (WARN-04).
- Kicker reads literal `№ 01 · Database` without any `loop.index0` expression (WARN-03).
- Footer override still in last 20 lines of the CSS (WARN-05).
</success_criteria>

<output>
Create `.planning/phases/01-editorial-shell-home-inventory/01-04-database-editorial-rows-SUMMARY.md` documenting:
- Which Datasette context variables were consumed.
- Confirmation that `metadata.get('tables', {}).get(name)` pattern was preserved.
- Confirmation that `_zeeker_*` table filter was preserved AND now uses the canonical `selectattr`/`rejectattr` chain (no `matching_zeeker`, no mutation).
- Any column-count truncation choice (currently 8 columns before "+N").
- New CSS classes shipped: `.list`, `.row`, `.row::before`, `.row .idx / .name-col / .name / .desc / .cols / .cols .pk / .cols .more / .count-col / .count / .label / .date-col`.
- Note that dead legacy CSS selectors (`.tables-grid`, `.table-card`, `.database-card`) remain in the CSS file — templates have been purged of these class references; CSS cleanup is a future polish pass (WARN-09).
</output>
</content>
