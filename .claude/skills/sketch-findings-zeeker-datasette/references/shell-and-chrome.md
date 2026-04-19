# Shell & Chrome

Cross-cutting page chrome shared by every template: dark editorial nav, breadcrumb strip, hero pattern, petrol stat band, sticky toolbar, footer. Establishes the civic-broadsheet identity before any page-specific content renders.

## Design Decisions

### Dark editorial nav — ink on ink, ochre logo
Full-width dark bar at the top of every page. `background: var(--color-ink)`, white text, ochre logo. Contrasts against the warm paper body to signal "you are on a platform," not a document.

- Logo uppercase, Fraunces 700, `var(--color-ochre)` — the only always-colored element in the nav.
- Menu links right-aligned, Inter 500, 80% opacity white, hover to 100%.
- Consistent 56–64px total height.

### Breadcrumb strip — separate row, mono typography
A second row below the nav, `var(--color-bg-alt)` background. JetBrains Mono, uppercase, muted colors, `›`/`·` separators. Always shows Home → database → table → (pk) per Datasette route pattern. Current page highlighted in `var(--color-accent)`.

### Hero pattern — asymmetric 7fr/5fr or 3fr/2fr
Every "top of page" follows the same pattern: main content left (kicker + italic-accent H1 + lede paragraph), metadata column right (definition list with petrol rule-top). Grid columns are typically `7fr 5fr` or `3fr 2fr` at desktop, collapsing to `1fr` under 960px.

### Petrol stat band — the signal moment
Full-bleed `background: var(--color-accent)` (petrol), `color: var(--color-text-inverse)` (paper), with big ochre numbers and small paper labels. 4-column grid of stats. This band appears on home, database, and table pages — it's the primary visual marker of "data density" and the clearest signal the design palette is being spent.

### Sticky toolbar — sits below nav
Sticky at `top: 52px` (nav height). Search input on left, view toggles (Cards / List / Schema) as segmented control, facet dropdowns, right-aligned export links. Separates content controls from navigation.

### Footer — 4-column link grid + copyright, light mode
Reuses the paper palette (`--color-surface-sunken`) — does **not** copy Datasette's default dark blue footer. 4 columns of category-grouped links (Product · Resources · Data · About) over a hairline-ruled copyright bar.

**Critical:** Datasette's `app.css` ships `footer a:link { color: rgba(255,255,244,0.8) }` which is invisible on this light footer. Always provide a matching-specificity override:

```css
footer a:link, footer a:visited, footer a:active {
  color: var(--color-text-secondary);
  text-decoration: none;
}
footer a:hover, footer a:focus {
  color: var(--color-accent);
  text-decoration: none;
}
```

## CSS Patterns

### Dark nav

```css
.db-nav { background: var(--color-ink); color: var(--color-bg); padding: var(--space-4) 0; }
.db-nav .container { display: flex; align-items: center; gap: var(--space-8); max-width: 1200px; margin: 0 auto; padding: 0 var(--space-8); }
.db-nav .logo { font-family: var(--font-display); font-weight: 700; font-size: var(--text-xl); color: var(--color-ochre); }
.db-nav .menu { margin-left: auto; display: flex; gap: var(--space-6); }
.db-nav .menu a { color: var(--color-bg); font-size: var(--text-sm); font-weight: 500; opacity: 0.8; }
.db-nav .menu a:hover { opacity: 1; text-decoration: none; }
```

### Breadcrumb strip

```css
.db-crumb { background: var(--color-bg-alt); border-bottom: 1px solid var(--color-border); padding: var(--space-3) 0; }
.db-crumb .container { display: flex; gap: var(--space-2); font-size: var(--text-xs); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: var(--tracking-wide); font-family: var(--font-mono); }
.db-crumb a { color: var(--color-text-secondary); }
.db-crumb .sep { color: var(--color-border); }
.db-crumb .current { color: var(--color-accent); font-weight: 600; }
```

### Hero grid + asymmetric meta column

```css
.db-header { padding: var(--space-16) 0 var(--space-12); background: var(--color-bg); }
.db-header-grid { display: grid; grid-template-columns: 1fr 320px; gap: var(--space-16); align-items: end; }
.db-header .kicker { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-terracotta); text-transform: uppercase; letter-spacing: var(--tracking-caps); margin-bottom: var(--space-4); }
.db-header h1 { font-family: var(--font-display); font-size: var(--text-6xl); font-weight: 400; line-height: 0.95; letter-spacing: -0.03em; }
.db-header h1 em { font-style: italic; color: var(--color-accent); }
.db-header .meta-col { border-top: 2px solid var(--color-accent); padding-top: var(--space-4); }
.db-header .meta-col dt { font-family: var(--font-mono); font-size: var(--text-xs); text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--color-text-muted); margin-top: var(--space-3); }
.db-header .meta-col dd { font-family: var(--font-display); font-size: var(--text-xl); font-weight: 500; color: var(--color-ink); margin: 0; }

@media (max-width: 960px) {
  .db-header-grid { grid-template-columns: 1fr; }
  .db-header h1 { font-size: var(--text-4xl); }
}
```

### Petrol stat band

```css
.db-statband { background: var(--color-accent); color: var(--color-text-inverse); padding: var(--space-5) 0; }
.db-statband .container { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-8); align-items: baseline; }
.db-statband .stat-num { font-family: var(--font-display); font-size: var(--text-3xl); font-weight: 500; line-height: 1; color: var(--color-ochre); }
.db-statband .stat-label { display: block; font-size: var(--text-xs); text-transform: uppercase; letter-spacing: var(--tracking-caps); margin-top: 4px; opacity: 0.75; }

@media (max-width: 960px) {
  .db-statband .container { grid-template-columns: repeat(2, 1fr); }
}
```

### Sticky toolbar

```css
.db-toolbar {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: var(--space-4) 0;
  position: sticky; top: 52px; z-index: 50;
}
.db-toolbar .container { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.db-toolbar-search {
  flex: 1; min-width: 240px; max-width: 360px;
  display: flex; align-items: center; gap: var(--space-2);
  background: var(--color-surface-sunken); border: 1px solid var(--color-border);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm);
}
.view-toggle { display: flex; border: 1px solid var(--color-border); border-radius: var(--radius-sm); overflow: hidden; }
.view-toggle button { background: transparent; border: 0; padding: 6px 12px; font-size: var(--text-xs); color: var(--color-text-muted); }
.view-toggle button.active { background: var(--color-accent); color: var(--color-text-inverse); }
```

## HTML Structures

### Full shell skeleton (for any page)

```html
<nav class="db-nav">
  <div class="container">
    <span class="logo">DATA.ZEEKER.SG</span>
    <div class="menu">
      <a href="/">Browse</a>
      <a href="/how-to-use">How to use</a>
      <a href="/developers">Developers</a>
      <a href="/about">About</a>
    </div>
  </div>
</nav>

<div class="db-crumb">
  <div class="container">
    <a href="/">Home</a><span class="sep">›</span>
    <a href="/{db}">{db}</a><span class="sep">›</span>
    <span class="current">{current}</span>
  </div>
</div>

<header class="db-header">
  <div class="container">
    <div class="db-header-grid">
      <div>
        <div class="kicker">№ 01 · {type}</div>
        <h1><em>{primary}</em> {secondary}</h1>
        <p class="lede">{description}</p>
      </div>
      <dl class="meta-col">
        <dt>Licence</dt><dd>{licence}</dd>
        <dt>Source</dt><dd>{source}</dd>
        <dt>Updated</dt><dd>{updated}</dd>
      </dl>
    </div>
  </div>
</header>

<div class="db-statband">
  <div class="container">
    <div><div class="stat-num">{n}</div><span class="stat-label">{label}</span></div>
    <!-- ... 4 cells ... -->
  </div>
</div>

<!-- page-specific toolbar + content -->
```

## What to Avoid

- **Copying Datasette's default dark-blue footer.** Our light footer needs the specificity override above or links will be near-invisible (the actual bug fixed during sketch work).
- **Nav menu with 6+ links.** Current pattern: 4 menu items max. More belongs in a drawer/disclosure.
- **Breadcrumb as one row with the nav.** Separate row keeps the nav clean and gives the crumb space to show deep paths.
- **Stat band on every type of page.** Reserve for home / database / table. A single row page should not have one — it would compete with the article.
- **Adding another full-bleed colored band below the stat band.** One full-bleed color change per scroll maximum; more reads as theme-y.
- **Meta-column without the petrol rule-top.** `border-top: 2px solid var(--color-accent)` is what makes the `dl` read as editorial metadata rather than random list.

## Origin
Synthesized from sketches: 001 (home variants), 002 (database variants), 004 (table variants — all three share this chrome).
Source files: `sources/001-home-editorial-hero/`, `sources/002-database-table-grid/`, `sources/004-table-as-news-archive/`.
