---
phase: 01-editorial-shell-home-inventory
plan: 02
type: execute
wave: 2
depends_on: ["01"]
files_modified:
  - templates/_header.html
  - templates/_footer.html
  - static/css/zeeker-base.css
autonomous: true
requirements:
  - SC-01-dark-nav
  - SC-01-breadcrumb-mono
  - SC-01-hero-asymmetric
  - SC-01-petrol-statband
  - SC-01-sticky-toolbar
  - SC-01-footer-contrast
tags:
  - shell
  - chrome
  - header
  - footer
  - css
must_haves:
  truths:
    - "Every page has a dark-ink nav bar with ochre logo and 4 menu links"
    - "Every database/table page shows a breadcrumb strip below the nav (mono, uppercase, petrol current)"
    - "Hero, petrol stat band, and sticky toolbar CSS classes are available for use by any page"
    - "Footer renders at full text contrast (footer a:link override survives)"
  artifacts:
    - path: "templates/_header.html"
      provides: "Dark nav + breadcrumb markup using .db-nav / .db-crumb classes"
      contains: "db-nav"
    - path: "templates/_footer.html"
      provides: "4-column link grid using .site-footer / .footer-col classes"
      contains: "footer-grid"
    - path: "static/css/zeeker-base.css"
      provides: "Component classes .db-nav, .db-crumb, .db-header, .db-statband, .db-toolbar, .section, .kicker, .site-footer + category pill classes"
      contains: ".db-statband"
  key_links:
    - from: "_header.html"
      to: "static/css/zeeker-base.css .db-nav / .db-crumb rules"
      via: "class attribute"
      pattern: "class=\"db-nav\""
    - from: "_footer.html"
      to: "zeeker-base.css footer a:link override (retained from today's fix)"
      via: "specificity override"
      pattern: "footer a:link"
---

<objective>
Ship the cross-cutting page chrome — dark editorial nav, breadcrumb strip, hero/stat-band/toolbar component classes, and the 4-column light footer — that every page in this phase (home, database, table) will consume. All shell-level CSS component classes live here so later page plans (03/04/05) only touch their respective HTML templates in parallel without further CSS churn.

Purpose: The sketches converge on one shared shell — dark ink nav + warm hero + petrol stat band + paper footer — appearing on home / database / table identically. Centralizing the chrome means page plans only vary the main-content block.

Output: Rewritten `templates/_header.html` and `templates/_footer.html` using the sketch class vocabulary, plus a new "## COMPONENTS / SHELL CHROME" section appended to `static/css/zeeker-base.css` with all chrome classes + hero/statband/toolbar + section framing + category pills.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.claude/skills/sketch-findings-zeeker-datasette/references/shell-and-chrome.md
@.claude/skills/sketch-findings-zeeker-datasette/references/theme-system.md
@.claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md
@.planning/notes/datasette-styling-limits.md
@.planning/phases/01-editorial-shell-home-inventory/01-01-theme-and-tokens-SUMMARY.md
@templates/_header.html
@templates/_footer.html
@metadata.json

<interfaces>
Tokens from Plan 01 now available in `static/css/zeeker-base.css :root`:
- Colors: `--color-bg`, `--color-bg-alt`, `--color-surface`, `--color-ink`, `--color-accent`, `--color-ochre`, `--color-terracotta`, `--color-text`, `--color-text-secondary`, `--color-text-muted`, `--color-text-inverse`, `--color-border`, `--color-accent-soft`, `--color-surface-sunken`
- Fonts: `--font-display` (Fraunces), `--font-body` (Inter), `--font-mono` (JetBrains Mono)
- Spacing: `--space-1` through `--space-32` (4px scale)
- Type scale: `--text-2xs` through `--text-7xl`
- Tracking: `--tracking-caps: 0.14em`, `--tracking-wide: 0.08em`, `--tracking-tight: -0.02em`
- Radius: `--radius-sm`, `--radius-full`
- Shadow: `--shadow-sm`, `--shadow-md`

Datasette context variables available in every template:
- `metadata.title`, `metadata.menu_links` (list of `{href, label}` dicts)
- `request.path` (for active-nav highlighting if desired)
- `str_site_title` (injected by the `string_manager` plugin)
- `s('key', 'default')` / `plural(n, key_singular, key_plural)` helpers
- `breadcrumbs` (set by caller template blocks — list of `{href?, label}` dicts)

DO NOT touch the existing `footer a:link, footer a:visited, footer a:active` override at the TAIL of zeeker-base.css (must remain in the last 20 lines). The new footer CSS must use non-`a:link` selectors (e.g. `.site-footer .footer-col a`) so the existing override keeps owning the link-color cascade.

The existing `metadata.json` `menu_links` array defines the 4 visible menu items: Home, How to Use, Developers, About, Status. Note: `Home` has `href: /` and `_header.html` already filters it out with `{% if link.href != '/' %}`. Keep that filter — the dark-ink logo already serves as the home link.

Datasette's built-in `<header>` default (from `base.html`) is replaced by `{% block nav %}` in every page template; our `_header.html` renders into that block. Similarly `{% block footer %}` renders `_footer.html`. This means: `_header.html` and `_footer.html` are themselves what renders, not snippets inside an outer shell.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite templates/_header.html as the sketch 001-D dark nav + breadcrumb strip</name>
  <files>templates/_header.html</files>
  <read_first>
    - templates/_header.html — current header (sticky blurred white bar with search input)
    - .claude/skills/sketch-findings-zeeker-datasette/references/shell-and-chrome.md — full skeleton example
    - .claude/skills/sketch-findings-zeeker-datasette/sources/001-home-editorial-hero/index.html (the `.vb-nav` variant)
    - metadata.json — menu_links array
  </read_first>
  <action>
    Replace the full contents of `templates/_header.html` with the following structure (Jinja preserved for `metadata.menu_links`, `breadcrumbs`, `database`, `table` variables). The rendered output must contain literally `<nav class="db-nav">` and (when breadcrumbs are set) `<div class="db-crumb">`.

    ```html
    <nav class="db-nav">
      <div class="container">
        <a class="logo" href="/">{{ str_site_title|default('data.zeeker.sg', true) }}</a>
        <div class="menu">
          {% if metadata and metadata.menu_links %}
            {% for link in metadata.menu_links %}
              {% if link.href != '/' %}
                <a href="{{ link.href }}">{{ link.label }}</a>
              {% endif %}
            {% endfor %}
          {% endif %}
        </div>
      </div>
    </nav>

    {% if breadcrumbs %}
    <div class="db-crumb">
      <div class="container">
        <a href="/">Home</a>
        {% for crumb in breadcrumbs %}
          <span class="sep">&rsaquo;</span>
          {% if crumb.href and not loop.last %}
            <a href="{{ crumb.href }}">{{ crumb.label }}</a>
          {% else %}
            <span class="current">{{ crumb.label }}</span>
          {% endif %}
        {% endfor %}
      </div>
    </div>
    {% endif %}
    ```

    Notes:
    - The existing page-level search input (`.header-search` form) that was embedded in the old header is REMOVED from the shell — hero pages provide their own `.hero-search` and the sticky toolbar (later) holds the per-page search. This is deliberate per sketch 001-D — the dark nav stays focused on logo + 4 menu links.
    - The first breadcrumb must always be `Home` linking to `/`. Callers (database.html, table.html) previously passed `{'href': '/', 'label': 'Home'}` as the first crumb — the new `_header.html` hardcodes Home itself and iterates the remaining crumbs, so callers must pass crumbs STARTING from the database level (not including Home). Update the two call sites in Task 1.5 below.
    - The logo text falls back to `data.zeeker.sg` when `str_site_title` is missing. **Uppercase is applied via CSS `text-transform: uppercase` on `.db-nav .logo`, NOT via Jinja `|upper`** (per WARN-07 — keep the raw string lowercase so the CSS controls presentation).
    - Do NOT add a backdrop-filter blur or any "sticky white" styling — the nav is a solid dark bar.
  </action>
  <verify>
    <automated>grep -q '<nav class="db-nav">' templates/_header.html && grep -q '<div class="db-crumb">' templates/_header.html && grep -q 'metadata.menu_links' templates/_header.html && grep -q 'class="logo"' templates/_header.html && grep -q 'class="current"' templates/_header.html && ! grep -q 'header-search' templates/_header.html && ! grep -q '|upper' templates/_header.html</automated>
  </verify>
  <acceptance_criteria>
    - `templates/_header.html` contains literal `<nav class="db-nav">`
    - `templates/_header.html` contains literal `<div class="db-crumb">`
    - `templates/_header.html` contains literal `class="logo"`
    - `templates/_header.html` contains literal `class="current"` inside the crumb loop
    - `templates/_header.html` references `metadata.menu_links`
    - `templates/_header.html` filters out `link.href == '/'` (Home already provided by logo)
    - `templates/_header.html` does NOT contain `header-search` (old search form removed)
    - `templates/_header.html` does NOT contain `backdrop-filter` or `sticky`-related inline styles
    - `templates/_header.html` does NOT contain `|upper` filter on the logo — uppercase is pure CSS via `.db-nav .logo` (WARN-07)
    - `templates/_header.html` logo fallback is the lowercase literal `'data.zeeker.sg'` (CSS uppercases it)
    - No `<header>` wrapper tag (template renders directly into `{% block nav %}`)
  </acceptance_criteria>
  <done>New header template matches the shell-and-chrome skeleton; old blurred-white header with embedded search is gone; uppercase styling is CSS-driven, not Jinja-driven.</done>
</task>

<task type="auto">
  <name>Task 1.5: Update callers (database.html, table.html) to pass crumbs starting from the database level</name>
  <files>templates/database.html, templates/table.html</files>
  <read_first>
    - templates/database.html (current `{% set breadcrumbs = [ {'href': '/', 'label': 'Home'}, ... ] %}`)
    - templates/table.html (same pattern)
  </read_first>
  <action>
    The new `_header.html` hardcodes the `Home` crumb. Callers must pass crumbs starting from the database level.

    In `templates/database.html` block `nav`, change:
    ```
    {% set breadcrumbs = [
        {'href': '/', 'label': 'Home'},
        {'label': metadata.title if metadata and metadata.title else database|title}
    ] %}
    ```
    to:
    ```
    {% set breadcrumbs = [
        {'label': metadata.title if metadata and metadata.title else database|title}
    ] %}
    ```

    In `templates/table.html` block `nav`, change:
    ```
    {% set breadcrumbs = [
        {'href': '/', 'label': 'Home'},
        {'href': '/' ~ database, 'label': database|title},
        {'label': metadata.title if metadata and metadata.title else table|title}
    ] %}
    ```
    to:
    ```
    {% set breadcrumbs = [
        {'href': '/' ~ database, 'label': database|title},
        {'label': metadata.title if metadata and metadata.title else table|title}
    ] %}
    ```

    Do NOT touch any other block in `database.html` or `table.html` — Plan 04 owns `database.html` main-content rewrite and `table.html` is explicitly out of scope (Datasette's built-in row rendering is preserved).
  </action>
  <verify>
    <automated>grep -A2 'set breadcrumbs' templates/database.html | grep -v "'href': '/'," && grep -A3 'set breadcrumbs' templates/table.html | grep -v "'href': '/',"</automated>
  </verify>
  <acceptance_criteria>
    - `grep "'label': 'Home'" templates/database.html` returns no match
    - `grep "'label': 'Home'" templates/table.html` returns no match
    - `grep "set breadcrumbs" templates/database.html` still returns 1 match (block is still there, just without Home)
    - `grep "set breadcrumbs" templates/table.html` still returns 1 match
    - Rest of database.html and table.html bodies unchanged
  </acceptance_criteria>
  <done>Both callers pass crumbs without the Home prefix; `_header.html` provides Home itself.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite templates/_footer.html as the 4-column paper footer with site-footer class</name>
  <files>templates/_footer.html</files>
  <read_first>
    - templates/_footer.html — current 4-column footer
    - .claude/skills/sketch-findings-zeeker-datasette/references/shell-and-chrome.md — "Footer" section
    - .planning/notes/datasette-styling-limits.md — section 2 (footer specificity war)
  </read_first>
  <action>
    Replace the full contents of `templates/_footer.html` with the following. Key goals: wrap in `<footer class="site-footer">` (adds class for CSS targeting without breaking the existing bare `footer a:link` override), use `.footer-grid` / `.footer-col` / `.footer-bottom` class names the new CSS (Task 3) will style.

    ```html
    <footer class="site-footer">
      <div class="container">
        {% block footer_links %}
        <div class="footer-grid">
          <div class="footer-col">
            <h4>Product</h4>
            <ul>
              <li><a href="/">Databases</a></li>
              <li><a href="/-/search">Search</a></li>
            </ul>
          </div>
          <div class="footer-col">
            <h4>Resources</h4>
            <ul>
              <li><a href="/how-to-use">How to use</a></li>
              <li><a href="/developers">Developers</a></li>
              <li><a href="/llms.txt">llms.txt</a></li>
            </ul>
          </div>
          <div class="footer-col">
            <h4>Data</h4>
            <ul>
              <li><a href="/sources">Sources</a></li>
              <li><a href="/status">Status</a></li>
            </ul>
          </div>
          <div class="footer-col">
            <h4>About</h4>
            <ul>
              <li><a href="/about">About</a></li>
            </ul>
          </div>
        </div>
        {% endblock %}

        {% block footer_text %}
        <div class="footer-bottom">
          <p>&copy; {{ current_year }} {% if s is defined %}{{ s('site_title', 'data.zeeker.sg') }}{% else %}{{ (metadata.title if metadata and metadata.title else 'data.zeeker.sg') }}{% endif %}</p>
        </div>
        {% endblock %}
      </div>
    </footer>
    ```

    Retained behaviors:
    - Block names `footer_links` and `footer_text` preserved so per-database overlays can override.
    - Uses `s()` helper with fallback.
    - `current_year` variable is injected by the string_manager plugin.
  </action>
  <verify>
    <automated>grep -q '<footer class="site-footer">' templates/_footer.html && grep -q 'class="footer-grid"' templates/_footer.html && grep -q 'footer_links' templates/_footer.html && grep -q 'footer_bottom\|footer-bottom' templates/_footer.html</automated>
  </verify>
  <acceptance_criteria>
    - `templates/_footer.html` contains literal `<footer class="site-footer">`
    - `templates/_footer.html` contains literal `class="footer-grid"`
    - `templates/_footer.html` contains literal `class="footer-col"` (at least 4 times)
    - `templates/_footer.html` contains literal `class="footer-bottom"`
    - `templates/_footer.html` still defines `{% block footer_links %}` and `{% block footer_text %}`
  </acceptance_criteria>
  <done>Footer uses new class names and is ready for the CSS in Task 3.</done>
</task>

<task type="auto">
  <name>Task 3: Append "SHELL CHROME" CSS section to static/css/zeeker-base.css with nav + crumb + hero + statband + toolbar + section framing + pills + footer + container</name>
  <files>static/css/zeeker-base.css</files>
  <read_first>
    - static/css/zeeker-base.css — read the TAIL of the file (last 100 lines) to confirm the `footer a:link` override block is still present and to locate the correct insertion point. Anchor: `footer a:link` selector. Do not rely on absolute line numbers.
    - .claude/skills/sketch-findings-zeeker-datasette/references/shell-and-chrome.md (all CSS Patterns)
    - .claude/skills/sketch-findings-zeeker-datasette/references/directory-and-feed-lists.md (category pills + sticky toolbar)
    - .claude/skills/sketch-findings-zeeker-datasette/sources/001-home-editorial-hero/index.html (.vb-nav, .vb-hero, .vb-stat-band, .vb-cta reference blocks)
  </read_first>
  <action>
    Append a single new section (delimited by a `/* =========== SHELL CHROME — phase 01 ============ */` banner comment) to the END of `static/css/zeeker-base.css`, but BEFORE the existing `footer a:link` override (so the override's specificity still wins for link color). Locate the override by `grep 'footer a:link' static/css/zeeker-base.css` — insert the new chrome CSS immediately before that block so the override remains in the last 20 lines of the file.

    The section must include every class block below (values are non-negotiable — hex codes, spacing, fonts all come from Plan 01 tokens):

    ```css
    /* =========== SHELL CHROME — phase 01 ============ */

    /* .container — shared layout wrapper (if not already covered) */
    .db-nav > .container,
    .db-crumb > .container,
    .db-header > .container,
    .db-statband > .container,
    .db-toolbar > .container,
    .site-footer > .container,
    .section > .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 var(--space-8);
    }

    /* Dark editorial nav — ink on ink, ochre logo */
    .db-nav {
      background: var(--color-ink);
      color: var(--color-bg);
      padding: var(--space-4) 0;
    }
    .db-nav > .container {
      display: flex;
      align-items: center;
      gap: var(--space-8);
    }
    .db-nav .logo {
      font-family: var(--font-display);
      font-weight: 700;
      font-size: var(--text-xl);
      color: var(--color-ochre);
      letter-spacing: var(--tracking-caps);
      text-transform: uppercase;
      text-decoration: none;
    }
    .db-nav .logo:hover { color: var(--color-ochre); text-decoration: none; }
    .db-nav .menu {
      margin-left: auto;
      display: flex;
      gap: var(--space-6);
      flex-wrap: wrap;
    }
    .db-nav .menu a,
    .db-nav .menu a:link,
    .db-nav .menu a:visited {
      color: var(--color-bg);
      font-size: var(--text-sm);
      font-weight: 500;
      opacity: 0.8;
      text-decoration: none;
    }
    .db-nav .menu a:hover {
      opacity: 1;
      color: var(--color-ochre);
      text-decoration: none;
    }

    /* Breadcrumb strip — mono, uppercase */
    .db-crumb {
      background: var(--color-bg-alt);
      border-bottom: 1px solid var(--color-border);
      padding: var(--space-3) 0;
    }
    .db-crumb > .container {
      display: flex;
      gap: var(--space-2);
      align-items: center;
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      text-transform: uppercase;
      letter-spacing: var(--tracking-wide);
      color: var(--color-text-muted);
      flex-wrap: wrap;
    }
    .db-crumb a,
    .db-crumb a:link,
    .db-crumb a:visited {
      color: var(--color-text-secondary);
      text-decoration: none;
    }
    .db-crumb a:hover { color: var(--color-accent); text-decoration: none; }
    .db-crumb .sep { color: var(--color-border); }
    .db-crumb .current { color: var(--color-accent); font-weight: 600; }

    /* Kicker / section label */
    .kicker, .section-label {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      text-transform: uppercase;
      letter-spacing: var(--tracking-caps);
      color: var(--color-terracotta);
      font-weight: 600;
    }
    .kicker::before { content: '— '; }

    /* Numbered section framing (№ 01 · Databases) */
    .section { padding: var(--space-20) 0; }
    .section.alt { background: var(--color-bg-alt); }
    .section-num {
      font-family: var(--font-mono);
      font-size: var(--text-sm);
      color: var(--color-terracotta);
      font-weight: 500;
      margin-bottom: var(--space-2);
    }
    .section-head {
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: var(--space-16);
      align-items: end;
      margin-bottom: var(--space-12);
    }
    .section-head h2 {
      font-family: var(--font-display);
      font-size: var(--text-5xl);
      font-weight: 400;
      letter-spacing: -0.03em;
      line-height: 1;
      max-width: 800px;
      margin: 0;
    }
    .section-head h2 em { font-style: italic; color: var(--color-accent); }
    .section-head .aside {
      font-size: var(--text-sm);
      color: var(--color-text-muted);
      line-height: 1.5;
    }
    @media (max-width: 960px) {
      .section-head { grid-template-columns: 1fr; gap: var(--space-4); }
      .section-head h2 { font-size: var(--text-3xl); }
    }

    /* Asymmetric hero (7fr/5fr or 3fr/2fr) — reusable on home / database / table */
    .db-header {
      padding: var(--space-20) 0 var(--space-16);
      background: var(--color-bg);
    }
    .db-header-grid {
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: var(--space-16);
      align-items: end;
    }
    .db-header h1 {
      font-family: var(--font-display);
      font-size: var(--text-6xl);
      font-weight: 400;
      line-height: 0.95;
      letter-spacing: -0.035em;
      margin: 0 0 var(--space-6);
    }
    .db-header h1 em { font-style: italic; color: var(--color-accent); font-weight: 500; }
    .db-header .lede {
      font-size: var(--text-xl);
      line-height: 1.45;
      color: var(--color-text-secondary);
      max-width: 540px;
      font-weight: 300;
    }
    .db-header .meta-col {
      padding-top: var(--space-4);
      border-top: 2px solid var(--color-accent);
    }
    .db-header .meta-col dt {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      text-transform: uppercase;
      letter-spacing: var(--tracking-caps);
      color: var(--color-text-muted);
      margin-top: var(--space-4);
    }
    .db-header .meta-col dd {
      font-family: var(--font-display);
      font-size: var(--text-2xl);
      font-weight: 500;
      color: var(--color-ink);
      margin: 0;
    }
    @media (max-width: 960px) {
      .db-header-grid { grid-template-columns: 1fr; gap: var(--space-8); }
      .db-header h1 { font-size: var(--text-4xl); }
    }

    /* Petrol stat band — the signal moment */
    .db-statband {
      background: var(--color-accent);
      color: var(--color-text-inverse);
      padding: var(--space-8) 0;
    }
    .db-statband > .container {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--space-8);
      align-items: baseline;
    }
    .db-statband .stat-num {
      font-family: var(--font-display);
      font-size: var(--text-5xl);
      font-weight: 500;
      line-height: 1;
      color: var(--color-ochre);
    }
    .db-statband .stat-label {
      display: block;
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      text-transform: uppercase;
      letter-spacing: var(--tracking-caps);
      margin-top: var(--space-2);
      opacity: 0.8;
      color: var(--color-text-inverse);
    }
    @media (max-width: 960px) {
      .db-statband > .container { grid-template-columns: repeat(2, 1fr); gap: var(--space-6); }
      .db-statband .stat-num { font-size: var(--text-3xl); }
    }

    /* Sticky sub-toolbar — below nav */
    .db-toolbar {
      background: var(--color-surface);
      border-bottom: 1px solid var(--color-border);
      padding: var(--space-4) 0;
      position: sticky;
      top: 0;
      z-index: var(--z-sticky);
    }
    .db-toolbar > .container {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      flex-wrap: wrap;
    }
    .db-toolbar-search {
      flex: 1;
      min-width: 240px;
      max-width: 360px;
      display: flex;
      align-items: center;
      gap: var(--space-2);
      background: var(--color-surface-sunken);
      border: 1px solid var(--color-border);
      padding: var(--space-2) var(--space-3);
      border-radius: var(--radius-sm);
    }
    .db-toolbar-search input {
      flex: 1;
      border: 0;
      background: transparent;
      outline: 0;
      font-family: var(--font-body);
      font-size: var(--text-sm);
      color: var(--color-text);
    }
    .view-toggle {
      display: flex;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      overflow: hidden;
    }
    .view-toggle button {
      background: transparent;
      border: 0;
      padding: 6px 12px;
      font-size: var(--text-xs);
      color: var(--color-text-muted);
      font-family: var(--font-mono);
    }
    .view-toggle button.active {
      background: var(--color-accent);
      color: var(--color-text-inverse);
    }

    /* Dark CTA block — used on home (and elsewhere) */
    .cta {
      background: var(--color-ink);
      color: var(--color-bg);
      padding: var(--space-20) 0;
      text-align: center;
    }
    .cta h2 {
      font-family: var(--font-display);
      font-size: var(--text-5xl);
      font-weight: 400;
      color: var(--color-bg);
      max-width: 700px;
      margin: 0 auto var(--space-6);
      line-height: 1.05;
    }
    .cta h2 em { font-style: italic; color: var(--color-ochre); }
    .cta p {
      color: var(--color-bg);
      opacity: 0.75;
      max-width: 520px;
      margin: 0 auto var(--space-8);
      font-size: var(--text-lg);
      font-weight: 300;
    }
    .cta-actions { display: flex; gap: var(--space-4); justify-content: center; flex-wrap: wrap; }
    .btn-primary {
      background: var(--color-ochre);
      color: var(--color-ink);
      padding: var(--space-4) var(--space-8);
      font-weight: 600;
      border: 0;
      font-size: var(--text-base);
      font-family: var(--font-body);
      text-decoration: none;
      display: inline-block;
      transition: all 0.15s ease;
    }
    .btn-primary:hover { background: var(--color-bg); color: var(--color-ink); transform: translateY(-1px); text-decoration: none; }
    .btn-ghost {
      background: transparent;
      color: var(--color-bg);
      padding: var(--space-4) var(--space-8);
      border: 1px solid rgba(245,242,234,0.4);
      font-weight: 500;
      font-size: var(--text-base);
      font-family: var(--font-body);
      text-decoration: none;
      display: inline-block;
      transition: all 0.15s ease;
    }
    .btn-ghost:hover { border-color: var(--color-bg); background: rgba(245,242,234,0.05); color: var(--color-bg); text-decoration: none; }

    /* Category pills (consumed by feed cards in Plan 05) */
    .cat-pill {
      display: inline-block;
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: var(--radius-full);
    }
    .cat-pill.press-release { background: var(--color-accent-soft); color: var(--color-accent); }
    .cat-pill.speech        { background: rgba(192,138,46,0.18); color: var(--color-ochre); }
    .cat-pill.announcement  { background: rgba(181,85,47,0.15); color: var(--color-terracotta); }
    .cat-pill.newsletter    { background: var(--color-surface-sunken); color: var(--color-text-secondary); border: 1px solid var(--color-border); }

    /* FTS badge (consumed by database row in Plan 04) */
    .fts-badge {
      display: inline-block;
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 600;
      padding: 2px 6px;
      color: var(--color-accent);
      border: 1px solid var(--color-accent);
      border-radius: var(--radius-sm);
    }

    /* Paper footer — 4-column grid */
    .site-footer {
      background: var(--color-surface-sunken);
      border-top: 1px solid var(--color-border);
      padding: var(--space-16) 0 var(--space-8);
      margin-top: var(--space-20);
      color: var(--color-text-secondary);
    }
    .site-footer .footer-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--space-8);
      margin-bottom: var(--space-10);
    }
    .site-footer .footer-col h4 {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      text-transform: uppercase;
      letter-spacing: var(--tracking-caps);
      color: var(--color-text-muted);
      font-weight: 600;
      margin: 0 0 var(--space-4);
    }
    .site-footer .footer-col ul {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: var(--space-2);
    }
    .site-footer .footer-col a {
      font-size: var(--text-sm);
      font-family: var(--font-body);
    }
    .site-footer .footer-bottom {
      border-top: 1px solid var(--color-border);
      padding-top: var(--space-6);
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--color-text-muted);
      text-transform: uppercase;
      letter-spacing: var(--tracking-wide);
    }
    .site-footer .footer-bottom p { margin: 0; color: var(--color-text-muted); }
    @media (max-width: 960px) {
      .site-footer .footer-grid { grid-template-columns: repeat(2, 1fr); gap: var(--space-6); }
    }
    ```

    **Note on `.db-nav .logo` uppercase (WARN-07):** The `.db-nav .logo` selector above includes `text-transform: uppercase;` and `letter-spacing: var(--tracking-caps);`. This is what uppercases the logo text — the Jinja template MUST provide the lowercase literal (`data.zeeker.sg`), not `|upper`.

    **Note on `.db-toolbar` consumption (WARN-02):** This CSS defines `.db-toolbar` and `.db-toolbar-search`. Plan 04 renders a `<div class="db-toolbar">` (with a table-filter search input) on `templates/database.html` so the selector is actually used; do not remove it here.

    CRITICAL preservation:
    - Insert the banner section BEFORE the existing `footer a:link, footer a:visited, footer a:active { … }` block that already lives at the END of the file. Do NOT delete or relocate that block — its position at the bottom is what wins the cascade against Datasette's `app.css`. The override MUST remain within the last 20 lines of the file after this edit.
    - Do NOT remove any existing `.header-search`, `.hero-section`, `.database-card`, `.tables-grid`, or Prism SQL CSS — those selectors may no longer be rendered by the new templates, but other pages (developers, status, sources, about, how-to-use) still depend on some of them. Leaving dead CSS is acceptable this phase; removal is a later polish.
  </action>
  <verify>
    <automated>grep -q 'SHELL CHROME' static/css/zeeker-base.css && grep -q '\.db-nav {' static/css/zeeker-base.css && grep -q '\.db-crumb {' static/css/zeeker-base.css && grep -q '\.db-header {' static/css/zeeker-base.css && grep -q '\.db-statband {' static/css/zeeker-base.css && grep -q '\.db-toolbar {' static/css/zeeker-base.css && grep -q '\.cta {' static/css/zeeker-base.css && grep -q '\.cat-pill\.press-release' static/css/zeeker-base.css && grep -q '\.cat-pill\.speech' static/css/zeeker-base.css && grep -q '\.cat-pill\.announcement' static/css/zeeker-base.css && grep -q '\.site-footer' static/css/zeeker-base.css && grep -q 'footer a:link' static/css/zeeker-base.css && tail -20 static/css/zeeker-base.css | grep -q 'footer a:link' && grep -q 'text-transform: uppercase' static/css/zeeker-base.css</automated>
  </verify>
  <acceptance_criteria>
    - `static/css/zeeker-base.css` contains banner `/* =========== SHELL CHROME — phase 01 ============ */`
    - All of these selectors present (literally): `.db-nav`, `.db-crumb`, `.db-header`, `.db-header h1 em`, `.db-statband`, `.db-toolbar`, `.kicker`, `.section-num`, `.cta`, `.cta h2 em`, `.btn-primary`, `.btn-ghost`, `.cat-pill`, `.cat-pill.press-release`, `.cat-pill.speech`, `.cat-pill.announcement`, `.cat-pill.newsletter`, `.fts-badge`, `.site-footer`, `.site-footer .footer-grid`, `.site-footer .footer-col`, `.site-footer .footer-bottom`
    - `.db-nav .logo` selector contains BOTH `text-transform: uppercase` AND `letter-spacing: var(--tracking-caps)` (WARN-07 — CSS, not Jinja, does the uppercasing)
    - `grep -c -- '--color-ochre' static/css/zeeker-base.css` returns >= 5
    - `grep -c -- '--color-terracotta' static/css/zeeker-base.css` returns >= 4
    - `grep -c -- 'var(--color-accent)' static/css/zeeker-base.css` returns >= 10
    - Existing `footer a:link, footer a:visited, footer a:active` block remains present
    - `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` returns 0 (override still in last 20 lines — WARN-05)
    - File line count now approximately pre-edit + 350-450 lines
  </acceptance_criteria>
  <done>All shell-chrome component classes are defined; home/database/table/feed-card plans in Wave 3 can consume them without further CSS changes; uppercase-logo styling is CSS-driven.</done>
</task>

</tasks>

<verification>
After all tasks:

1. Run `datasette serve . --port 8001` (or ensure it's running). Load `http://127.0.0.1:8001/` — dark nav bar at top, ochre logo rendered UPPERCASE (via CSS) with caps tracking, 4 menu links right-aligned.
2. Load `http://127.0.0.1:8001/fixtures` — dark nav + breadcrumb strip (`HOME › FIXTURES`) rendered below nav.
3. Load `http://127.0.0.1:8001/fixtures/facetable` — crumbs read `HOME › FIXTURES › FACETABLE`.
4. Footer on every page is warm paper (`#F0ECE0`), 4 columns, links visible at `--color-text-secondary` contrast.
5. `curl -s http://127.0.0.1:8001/fixtures -o /dev/null -w '%{http_code}'` returns `200` (no regression of today's `metadata.get('tables', {}).get(name)` bug fix).
6. Inspect any link in the footer — computed color is `#3E4F4E` or similar (NOT `rgba(255,255,244,0.8)`).
7. View-source on `/` shows the logo anchor's text is lowercase `data.zeeker.sg`; DevTools shows it rendered uppercase via CSS `text-transform`.
</verification>

<success_criteria>
- `_header.html` renders `<nav class="db-nav">` + optional `<div class="db-crumb">`.
- `_footer.html` renders `<footer class="site-footer">` with 4 columns.
- All SHELL CHROME CSS classes exist in `zeeker-base.css` including `.db-toolbar`.
- Pages `/`, `/fixtures`, `/fixtures/facetable` all return 200.
- Footer links still visible (today's fix retained) AND still in the last 20 lines of the CSS file.
- Logo uppercasing is CSS-driven, not Jinja-driven.
</success_criteria>

<output>
After completion, create `.planning/phases/01-editorial-shell-home-inventory/01-02-shared-chrome-SUMMARY.md` documenting:
- New classes shipped (table: class → purpose).
- Caller updates made (database.html / table.html breadcrumb changes).
- Dead/legacy selectors retained (list of old `.header-*`, `.hero-*`, `.database-card`, etc. still present in CSS).
- Any `s()` string keys referenced (so the string_manager plugin can be audited).
</output>
</content>
