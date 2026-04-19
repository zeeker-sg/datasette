---
phase: 01-editorial-shell-home-inventory
plan: 03
type: execute
wave: 3
depends_on: ["01", "02"]
files_modified:
  - templates/index.html
  - static/css/zeeker-base.css
autonomous: true
requirements:
  - SC-01-home-hero-asymmetric
  - SC-01-home-statband
  - SC-01-home-card-grid-rotation
  - SC-01-home-cta-dark
tags:
  - home
  - editorial
  - card-grid
  - template-sql
must_haves:
  truths:
    - "Home `/` renders a warm hero with italic-accent H1 + meta-col sidebar + petrol stat band"
    - "`№ 01 · Databases` section shows one card per attached database, with rotating petrol/ochre/terracotta top-border accents"
    - "Each card shows title, row count (Fraunces big), mono index number, and metadata"
    - "A `№ 02 · How to use` three-column block + dark CTA block close the page"
  artifacts:
    - path: "templates/index.html"
      provides: "Sketch 001-D home page"
      contains: "№ 01 · Databases"
    - path: "static/css/zeeker-base.css"
      provides: ".cards / .card / .card .idx / .chip / .how-grid / .meta-col / .hero-lede-search CSS (home-specific, appended to SHELL CHROME section)"
      contains: ".card:nth-child(3n+2)"
  key_links:
    - from: "templates/index.html"
      to: "datasette-template-sql plugin for dynamic databases loop"
      via: "{% for database in databases %} (already-exposed Datasette context variable)"
      pattern: "for database in databases"
    - from: ".card:nth-child(3n+N)"
      to: "rotating accent colors (petrol/ochre/terracotta)"
      via: "CSS nth-child"
      pattern: "3n\\+2"
---

<objective>
Replace `templates/index.html` main content with the sketch 001-D editorial home: dark nav (inherited from `_header.html` Plan 02) + warm hero with italic-accent H1 + petrol stat band + numbered card grid of databases with rotating accent borders + "How to use" 3-column + dark CTA block. Populated with real databases via Datasette's built-in `databases` context variable (no custom SQL needed — Datasette's index view already passes `databases: list[{name, table_count, size, ...}]`).

Purpose: Home is the visitor's first impression and the place the civic-broadsheet identity must land hardest. The current `templates/index.html` is a blocky white hero + generic card grid; the sketch replaces it with the editorial front-page pattern.

Output: Rewritten `templates/index.html` using Plan 02's `.db-nav`, `.db-crumb` (omitted on home), `.db-header`, `.db-statband`, `.section`, `.cta`, `.btn-primary`, `.btn-ghost` classes plus new home-specific classes `.cards`, `.card`, `.how-grid`, `.chip`. New home-specific CSS appended to `static/css/zeeker-base.css` in a `/* =========== HOME — phase 01 ============ */` banner section.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.claude/skills/sketch-findings-zeeker-datasette/references/home-layout.md
@.claude/skills/sketch-findings-zeeker-datasette/references/theme-system.md
@.claude/skills/sketch-findings-zeeker-datasette/references/shell-and-chrome.md
@.claude/skills/sketch-findings-zeeker-datasette/sources/001-home-editorial-hero/index.html
@.planning/phases/01-editorial-shell-home-inventory/01-01-theme-and-tokens-SUMMARY.md
@.planning/phases/01-editorial-shell-home-inventory/01-02-shared-chrome-SUMMARY.md
@templates/index.html
@plugins/string_manager.py
@metadata.json

<interfaces>
Datasette's default `index.html` view passes this Jinja context (Datasette 0.65.1, `datasette/views/base.py`):

- `databases`: list of dicts, each with at least:
  - `name` (string, url-encoded form)
  - `path` (e.g. `/SG-Government-Newsrooms`)
  - `tables_and_views_truncated` or `table_count` (varies by version — current code checks `database.table_count is defined`)
  - `hidden` (bool)
  - `size` (int, bytes)
  - `color` (deprecated)
- `metadata`: dict with `title`, `description`, `databases` (per-database metadata dicts)
- `databases` items may also have `show_table_row_counts` data in recent versions

The current template already uses `databases|length`, `database.table_count`, `database.size|filesizeformat`, `metadata.databases[database.name].title` — these are all confirmed to work.

String manager helpers available: `s(key, default)`, `sf(key, default, **kwargs)`, `plural(n, singular_key, plural_key)`.

Shell CSS classes from Plan 02 consumable without redefinition:
- `.db-nav`, `.db-crumb` (but home omits crumb)
- `.db-header`, `.db-header-grid`, `.db-header h1 em`, `.db-header .lede`, `.db-header .meta-col` / `dt` / `dd`
- `.db-statband`, `.db-statband .stat-num`, `.db-statband .stat-label`
- `.section`, `.section.alt`, `.section-num`, `.section-head`, `.section-head h2 em`, `.section-head .aside`
- `.cta`, `.cta h2 em`, `.cta-actions`, `.btn-primary`, `.btn-ghost`
- `.kicker` (`— ` prefix) and `.section-label`

Plan 02 already removed the old `.header-search` — the hero on home gets its own search form inline.

Total-rows calculation: current code uses a `namespace(total_tables=0)` pattern summing `database.table_count`. Datasette does NOT expose per-database row counts on the index page by default — `database.table_count` exists, `total_rows` does not. Keep stat band to: `{n_databases}`, `{total_tables}`, `{since_year (static "2022")}`, `export formats` — do not fabricate a row count.

The `hidden` flag on databases should skip hidden internal databases. Filter via `{% for database in databases if not database.hidden %}`.

**Canonical URL note (BLK-01):** Datasette does NOT expose a `request.url` variable to Jinja — referencing it raises under StrictUndefined. The home page is already at `/` and search engines do not need a custom canonical on the index view (Datasette emits standard `<link rel="canonical">` via its base template where needed). Do NOT add any `<link rel="canonical">` tag on the home template.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite templates/index.html as sketch 001-D (editorial hero + stat band + card grid + how-to + CTA)</name>
  <files>templates/index.html</files>
  <read_first>
    - templates/index.html (current — the blocky "Available Data" version)
    - .claude/skills/sketch-findings-zeeker-datasette/references/home-layout.md (full)
    - .claude/skills/sketch-findings-zeeker-datasette/sources/001-home-editorial-hero/index.html — search for "variant D" or the synthesis variant markup (`.vb-` or `.vd-` prefixed classes in the winner tab)
    - templates/_header.html (post-Plan-02 — confirms available blocks)
    - plugins/string_manager.py (if exists, to know which `s()` keys resolve)
  </read_first>
  <action>
    Replace the full contents of `templates/index.html` with the structure below. The template extends `default:index.html` to inherit `{% block nav %}` / `{% block footer %}` slots, then defines new main-content blocks. DO NOT include a breadcrumb in the home page (crumbs appear on database/table only; no crumbs is the home signal).

    ```jinja
    {% extends "default:index.html" %}

    {% block extra_head %}
    {{ super() }}
    {% if metadata and metadata.description %}
    <meta name="description" content="{{ metadata.description }}">
    {% endif %}
    {% endblock %}

    {% block nav %}
    {% include "_header.html" %}
    {% endblock %}

    {% block content %}
    {# --- Hero -------------------------------------------------------- #}
    <header class="db-header home-header">
      <div class="container">
        <div class="db-header-grid">
          <div>
            <div class="kicker">Civic data, open access</div>
            <h1>
              {{ s('home_hero_primary', 'Public data,')|safe }}
              <em>{{ s('home_hero_accent', 'rendered')|safe }}</em>
              <span class="und">{{ s('home_hero_underline', 'legible')|safe }}</span>.
            </h1>
            <p class="lede">
              {{ metadata.description if metadata and metadata.description
                 else s('site_tagline', 'A curated, queryable archive of Singapore government, judicial, and legal publications.') }}
            </p>
            <form class="hero-search" action="/-/search" method="get" role="search">
              <label for="home-search" class="visually-hidden">Search across all data</label>
              <input id="home-search" type="search" name="q"
                     placeholder="{{ s('search_placeholder', 'Search press releases, judgments, guides…') }}"
                     autocomplete="off">
              <button type="submit">Search</button>
            </form>
          </div>
          <dl class="meta-col">
            <dt>Licence</dt>
            <dd>{{ metadata.license if metadata and metadata.license else 'CC-BY-4.0' }}</dd>
            <dt>Source</dt>
            <dd>{{ metadata.source if metadata and metadata.source else 'Various curated sources' }}</dd>
            <dt>Last refreshed</dt>
            <dd>{{ current_year if current_year is defined else '' }}</dd>
          </dl>
        </div>
      </div>
    </header>

    {# --- Petrol stat band ------------------------------------------- #}
    {% set visible_dbs = databases|rejectattr('hidden')|list if databases else [] %}
    {% set ns = namespace(total_tables=0) %}
    {% for database in visible_dbs %}
      {% if database.table_count is defined and database.table_count %}
        {% set ns.total_tables = ns.total_tables + database.table_count %}
      {% endif %}
    {% endfor %}
    <div class="db-statband">
      <div class="container">
        <div>
          <div class="stat-num">{{ visible_dbs|length }}</div>
          <span class="stat-label">{{ plural(visible_dbs|length, 'plural_database', 'plural_databases') }}</span>
        </div>
        {% if ns.total_tables > 0 %}
        <div>
          <div class="stat-num">{{ "{:,}".format(ns.total_tables) }}</div>
          <span class="stat-label">{{ plural(ns.total_tables, 'plural_table', 'plural_tables') }}</span>
        </div>
        {% endif %}
        <div>
          <div class="stat-num">SQL</div>
          <span class="stat-label">full query access</span>
        </div>
        <div>
          <div class="stat-num">CSV · JSON</div>
          <span class="stat-label">{{ s('form_export', 'export formats') }}</span>
        </div>
      </div>
    </div>

    {# --- № 01 · Databases ------------------------------------------- #}
    <section class="section">
      <div class="container">
        <div class="section-num">№ 01 · {{ s('databases_heading', 'Databases') }}</div>
        <div class="section-head">
          <h2>
            {{ s('home_section1_line1', 'Curated public data,')|safe }}
            <em>{{ s('home_section1_line2', 'ready to query')|safe }}</em>.
          </h2>
          <div class="aside">
            {{ s('home_section1_aside', 'Every dataset ships with schema, source citation, and full SQL access.') }}
            <br>
            <a href="/-/search">Search across all data →</a>
          </div>
        </div>
        {% if visible_dbs %}
        <div class="cards">
          {% for database in visible_dbs %}
            {% set db_meta = metadata.databases[database.name] if metadata and metadata.databases and metadata.databases[database.name] else {} %}
            <article class="card">
              <span class="idx">{{ "{:02d}".format(loop.index) }}</span>
              <div class="card-meta">
                <span>{{ plural(database.table_count|default(0), 'plural_table', 'plural_tables') }}</span>
                {% if database.size is defined and database.size %}
                <span>· {{ database.size|filesizeformat }}</span>
                {% endif %}
              </div>
              <h3>
                <a href="/{{ database.name }}">
                  {% if db_meta.title %}{{ db_meta.title }}{% else %}{{ database.name|replace('-', ' ')|replace('_', ' ')|title }}{% endif %}
                </a>
              </h3>
              {% if db_meta.description %}
              <p class="card-desc">{{ db_meta.description }}</p>
              {% endif %}
              {% if database.table_count is defined and database.table_count %}
              <div class="card-count">
                {{ "{:,}".format(database.table_count) }}
                <small>{{ plural(database.table_count, 'plural_table', 'plural_tables') }}</small>
              </div>
              {% endif %}
              <div class="chips">
                <span class="chip">Browse</span>
                <a class="chip chip-link" href="/{{ database.name }}.csv">CSV</a>
                <a class="chip chip-link" href="/{{ database.name }}.json">JSON</a>
              </div>
            </article>
          {% endfor %}
        </div>
        {% endif %}
      </div>
    </section>

    {# --- № 02 · How to use ------------------------------------------ #}
    <section class="section alt">
      <div class="container">
        <div class="section-num">№ 02 · {{ s('howto_heading', 'How to use') }}</div>
        <div class="section-head">
          <h2>
            {{ s('home_section2_line1', 'Three ways to')|safe }}
            <em>{{ s('home_section2_line2', 'spend')|safe }}</em>
            {{ s('home_section2_line3', 'the data.')|safe }}
          </h2>
        </div>
        <div class="how-grid">
          <div class="how-item">
            <div class="kicker">Explore</div>
            <h3>Browse by database</h3>
            <p>Open any database above. Each page lists its tables with descriptions, schemas, and full-text search where available.</p>
          </div>
          <div class="how-item">
            <div class="kicker">Query</div>
            <h3>Write SQL</h3>
            <p>Every database accepts custom SQL via the query UI. Press <kbd>?sql=…</kbd> to pre-fill, or click <em>Schema</em> on a database page.</p>
          </div>
          <div class="how-item">
            <div class="kicker">Export</div>
            <h3>Pull the data</h3>
            <p>Append <code>.csv</code>, <code>.json</code>, or <code>.db</code> to any URL. Use the JSON API for programmatic access.</p>
          </div>
        </div>
      </div>
    </section>

    {# --- Dark CTA --------------------------------------------------- #}
    <section class="cta">
      <div class="container">
        <h2>
          {{ s('home_cta_line1', 'Bring your questions,')|safe }}
          <em>{{ s('home_cta_line2', 'leave with data')|safe }}</em>.
        </h2>
        <p>{{ s('home_cta_body', 'Open, citable, machine-readable. CC-BY-4.0 unless noted otherwise.') }}</p>
        <div class="cta-actions">
          <a href="/-/search" class="btn-primary">{{ s('home_cta_primary', 'Start searching') }}</a>
          <a href="/how-to-use" class="btn-ghost">{{ s('home_cta_ghost', 'Read the guide') }}</a>
        </div>
      </div>
    </section>
    {% endblock %}

    {% block footer %}
    {% include "_footer.html" %}
    {% endblock %}
    ```

    Notes:
    - No breadcrumb on home (deliberate — home is root).
    - **Do NOT include any `<link rel="canonical">` tag (BLK-01).** `request.url` is not a valid Jinja variable in Datasette, and the home page does not need a custom canonical tag — Datasette handles canonicalization on the index view.
    - `visible_dbs` filters `hidden: true` databases.
    - `loop.index` is used for the mono `01`, `02`, `03` corner numeral.
    - `database.name|replace('-',' ')|replace('_',' ')|title` gives a human-readable fallback when no `metadata.databases[name].title` exists (e.g. `SG-Government-Newsrooms` → `Sg Government Newsrooms`).
    - `current_year` is injected by the string_manager plugin.
    - Use `|safe` on s() calls that contain `<em>` markup (none here, but the pattern is forward-compatible).
    - Prefer `s()` keys with sensible defaults so the page renders even when `strings.yaml` has no translation.

    Do NOT invent fake total-rows numbers; the stat band uses `databases count + tables count + SQL marker + export formats` only.
  </action>
  <verify>
    <automated>grep -q '№ 01' templates/index.html && grep -q '№ 02' templates/index.html && grep -q 'class="db-header home-header"' templates/index.html && grep -q 'class="db-statband"' templates/index.html && grep -q 'class="cards"' templates/index.html && grep -q 'class="cta"' templates/index.html && grep -q 'for database in visible_dbs' templates/index.html && grep -q 'btn-primary' templates/index.html && grep -q 'btn-ghost' templates/index.html && ! grep -q 'hero-section' templates/index.html && ! grep -q 'stats-strip' templates/index.html && ! grep -q 'request.url' templates/index.html && ! grep -q 'rel="canonical"' templates/index.html</automated>
  </verify>
  <acceptance_criteria>
    - `templates/index.html` contains literal `№ 01` (numbered section label)
    - `templates/index.html` contains literal `№ 02`
    - `templates/index.html` contains literal `class="db-header home-header"` exactly (WARN-08 — the class attribute must be present as this literal string)
    - `templates/index.html` contains `class="db-statband"`
    - `templates/index.html` contains `class="cards"` (plural — the grid wrapper)
    - `templates/index.html` contains `<article class="card">`
    - `templates/index.html` contains `class="meta-col"`
    - `templates/index.html` contains `class="cta"`
    - `templates/index.html` contains `class="btn-primary"` and `class="btn-ghost"`
    - `templates/index.html` iterates `visible_dbs` (filtered for hidden)
    - `templates/index.html` uses `loop.index` for the mono corner number
    - `templates/index.html` does NOT contain `hero-section` or `stats-strip` (old classes removed)
    - `templates/index.html` does NOT invent row counts that Datasette doesn't expose
    - `templates/index.html` does NOT contain any reference to `request.url` (BLK-01)
    - `templates/index.html` does NOT contain `rel="canonical"` anywhere (BLK-01 — Datasette handles canonicalization)
    - `{% extends "default:index.html" %}` retained at top
    - `{% block nav %}{% include "_header.html" %}` retained
    - `{% block footer %}{% include "_footer.html" %}` retained
  </acceptance_criteria>
  <done>Home template uses the shell chrome classes from Plan 02, iterates real databases, and contains the numbered section + dark CTA pattern from sketch 001-D. No `request.url` reference, no canonical link.</done>
</task>

<task type="auto">
  <name>Task 2: Append HOME CSS section (.cards, .card with nth-child accent rotation, .chip, .how-grid, .hero-search) to static/css/zeeker-base.css</name>
  <files>static/css/zeeker-base.css</files>
  <read_first>
    - static/css/zeeker-base.css — read the TAIL of the file to confirm the SHELL CHROME section ends cleanly and the `footer a:link` override is still the last block. Anchor by `grep 'footer a:link'` — do not rely on absolute line numbers.
    - .claude/skills/sketch-findings-zeeker-datasette/references/home-layout.md (all CSS Patterns — especially "Card grid with rotating accent")
  </read_first>
  <action>
    Append a new section banner `/* =========== HOME — phase 01 ============ */` and the CSS below to `static/css/zeeker-base.css`, placed AFTER the SHELL CHROME section but BEFORE the existing `footer a:link` override block. All selectors/properties must appear literally:

    ```css
    /* =========== HOME — phase 01 ============ */

    /* Hero inline search (home only) */
    .home-header .hero-search {
      margin-top: var(--space-8);
      display: flex;
      align-items: center;
      gap: var(--space-3);
      background: var(--color-surface);
      border: 2px solid var(--color-accent);
      padding: var(--space-3) var(--space-4);
      border-radius: var(--radius-sm);
      max-width: 640px;
    }
    .home-header .hero-search input {
      flex: 1;
      border: 0;
      outline: 0;
      background: transparent;
      font-family: var(--font-body);
      font-size: var(--text-lg);
      color: var(--color-text);
    }
    .home-header .hero-search button {
      background: var(--color-accent);
      color: var(--color-text-inverse);
      border: 0;
      padding: var(--space-3) var(--space-6);
      border-radius: var(--radius-sm);
      font-weight: 600;
      font-family: var(--font-body);
      font-size: var(--text-base);
      transition: background 0.15s ease;
    }
    .home-header .hero-search button:hover { background: var(--color-accent-hover); }

    /* Card grid with rotating accent borders */
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: var(--space-4);
    }
    .card {
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-top: 3px solid var(--color-accent);
      padding: var(--space-6);
      position: relative;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .card:nth-child(3n+2) { border-top-color: var(--color-ochre); }
    .card:nth-child(3n+3) { border-top-color: var(--color-terracotta); }
    .card:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }
    .card .idx {
      position: absolute;
      top: var(--space-3);
      right: var(--space-4);
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--color-text-muted);
    }
    .card .card-meta {
      display: flex;
      gap: var(--space-3);
      color: var(--color-text-muted);
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      text-transform: uppercase;
      letter-spacing: var(--tracking-wide);
      margin-bottom: var(--space-3);
    }
    .card h3 {
      font-family: var(--font-display);
      font-size: var(--text-2xl);
      font-weight: 500;
      letter-spacing: -0.01em;
      margin: 0 0 var(--space-2);
      line-height: 1.15;
    }
    .card h3 a,
    .card h3 a:link,
    .card h3 a:visited {
      color: var(--color-ink);
      text-decoration: none;
    }
    .card h3 a:hover { color: var(--color-accent); text-decoration: none; }
    .card .card-desc {
      color: var(--color-text-secondary);
      font-size: var(--text-sm);
      line-height: 1.5;
      margin: 0 0 var(--space-4);
    }
    .card .card-count {
      font-family: var(--font-display);
      font-size: var(--text-xl);
      font-weight: 500;
      color: var(--color-ink);
      margin-bottom: var(--space-4);
      line-height: 1;
    }
    .card .card-count small {
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--color-text-muted);
      text-transform: uppercase;
      letter-spacing: var(--tracking-wide);
      margin-left: 6px;
      font-weight: 400;
    }
    .card .chips {
      display: flex;
      gap: var(--space-2);
      flex-wrap: wrap;
      margin-top: auto;
    }
    .chip {
      font-family: var(--font-body);
      font-size: var(--text-2xs);
      background: var(--color-accent-soft);
      color: var(--color-accent);
      padding: 3px 8px;
      border-radius: var(--radius-full);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      text-decoration: none;
    }
    .chip.chip-link:hover { background: var(--color-accent); color: var(--color-text-inverse); text-decoration: none; }
    .card:nth-child(3n+2) .chip:not(.chip-link) { background: rgba(192,138,46,0.15); color: var(--color-ochre); }
    .card:nth-child(3n+3) .chip:not(.chip-link) { background: rgba(181,85,47,0.15); color: var(--color-terracotta); }

    /* How-to 3-column */
    .how-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--space-8);
    }
    .how-item .kicker { margin-bottom: var(--space-2); }
    .how-item h3 {
      font-family: var(--font-display);
      font-size: var(--text-2xl);
      font-weight: 500;
      color: var(--color-ink);
      margin: 0 0 var(--space-3);
      letter-spacing: -0.01em;
    }
    .how-item h3 em { font-style: italic; color: var(--color-accent); }
    .how-item p {
      color: var(--color-text-secondary);
      font-size: var(--text-base);
      line-height: 1.55;
      margin: 0;
    }
    @media (max-width: 960px) {
      .how-grid { grid-template-columns: 1fr; gap: var(--space-6); }
    }
    ```

    Insertion constraint: place this section AFTER the `/* =========== SHELL CHROME — phase 01 ============ */` block from Plan 02 and BEFORE the existing `footer a:link, footer a:visited, footer a:active { … }` override block. The override must remain the last rule in the file (within the last 20 lines) so it wins the cascade.
  </action>
  <verify>
    <automated>grep -q 'HOME — phase 01' static/css/zeeker-base.css && grep -q '\.cards {' static/css/zeeker-base.css && grep -q '\.card {' static/css/zeeker-base.css && grep -q '\.card:nth-child(3n+2)' static/css/zeeker-base.css && grep -q '\.card:nth-child(3n+3)' static/css/zeeker-base.css && grep -q 'border-top-color: var(--color-ochre)' static/css/zeeker-base.css && grep -q 'border-top-color: var(--color-terracotta)' static/css/zeeker-base.css && grep -q '\.how-grid' static/css/zeeker-base.css && grep -q '\.chip {' static/css/zeeker-base.css && grep -q 'hero-search' static/css/zeeker-base.css && grep -q 'footer a:link' static/css/zeeker-base.css && tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'</automated>
  </verify>
  <acceptance_criteria>
    - Section banner `/* =========== HOME — phase 01 ============ */` present
    - `.cards` selector present with `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`
    - `.card:nth-child(3n+2)` sets `border-top-color: var(--color-ochre)`
    - `.card:nth-child(3n+3)` sets `border-top-color: var(--color-terracotta)`
    - `.card:hover` includes `transform: translateY(-2px)`
    - `.chip` selector present with `border-radius: var(--radius-full)`
    - `.how-grid` has `grid-template-columns: repeat(3, 1fr)` and a `@media (max-width: 960px)` collapse rule
    - `.home-header .hero-search` present with `border: 2px solid var(--color-accent)`
    - Existing `footer a:link, footer a:visited, footer a:active` block remains last
    - `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` returns 0 (WARN-05)
    - Shell-chrome section from Plan 02 still intact
  </acceptance_criteria>
  <done>Home-specific CSS appended; page renders with rotating accent borders, hover lift, and mono corner numerals; footer override still within final 20 lines.</done>
</task>

</tasks>

<verification>
1. `curl -s http://127.0.0.1:8001/ -o /dev/null -w '%{http_code}'` returns `200`.
2. Open `http://127.0.0.1:8001/` — H1 reads "Public data, *rendered* legible." with petrol italic and ochre underline.
3. Petrol stat band visible below hero with 3-4 cells, ochre numerals.
4. `№ 01 · Databases` label visible before card grid; cards show rotating top-border colors (petrol, ochre, terracotta) in sequence.
5. `№ 02 · How to use` label visible before three-column block.
6. Dark CTA block at page end — ink background, ochre italic in H2, ochre primary button + ghost button.
7. Footer visible with 4 columns and links at full contrast.
8. View-source on `/` contains NO `<link rel="canonical">` and NO reference to `request.url`.
</verification>

<success_criteria>
- Home page renders without 500 errors.
- Three accent colors (petrol, ochre, terracotta) visibly rotate across the database card grid.
- Italic-accent H1 with ochre underline visible in hero.
- `curl http://127.0.0.1:8001/` returns 200 on all viewports.
- Template contains `class="db-header home-header"` verbatim and contains no `request.url` / `rel="canonical"` references.
- Footer override still within the last 20 lines of `static/css/zeeker-base.css`.
</success_criteria>

<output>
Create `.planning/phases/01-editorial-shell-home-inventory/01-03-home-editorial-SUMMARY.md` documenting:
- Which Datasette context variables the template consumes.
- Which `s()` keys the template references (so strings.yaml can be updated later).
- Any fallback text hardcoded (for translation later).
- New CSS classes shipped: `.cards`, `.card`, `.card .idx`, `.chip`, `.how-grid`, `.home-header .hero-search`.
- Confirmation that no `<link rel="canonical">` is emitted (Datasette owns canonicalization on `/`).
</output>
</content>
