# Directory & Feed Lists

The "editorial list" pattern applied to two surfaces:
- **Database page** (sketch 002 winner B) — listing tables inside a database
- **Table page** (sketch 004 winner A) — listing rows inside a table (news archive)

Both are full-width lists with display-serif titles and mono metadata. No taxonomy, no grouping, no content-type specialization — which is exactly why they scale.

## Design Decisions

### Why full-width editorial rows beat card grids for inventories
Card grids worked for 12 databases (home page) but the same pattern for 24+ tables or 300+ rows overwhelmed. Rows work because:

1. The eye scans vertically in a single column — uniform rows let the title do the work.
2. Row counts and dates align on a right edge, so the eye gets a second anchor.
3. There's no "which card did I just see" disorientation.
4. Adding 100 more rows costs one scroll, not a grid reflow.

### Why no grouping
Sketch 002 tried semantic groups (Core / Reference / Key Patterns / Edge Cases), and sketch 004 tried monthly groups. Both required either per-database metadata (sketch 002-C) or got visually unbalanced at scale (sketch 004-B: one month may have 1 entry, the next 40). The flat list ignores the grouping question — Datasette's built-in facets already handle slicing, so the template doesn't need to.

### Anatomy of a row — shared across 002 and 004

```
| index (mono)    | primary content          | secondary meta      | count/date (right) |
| 01              | Display-serif title      | mono column/tag     | 1,148,221 rows     |
|                 | muted description        | summary             | UPD. 2d ago        |
```

Key typography rules:
- **Title** in Fraunces 500 at `--text-3xl`, letter-spacing `-0.01em`, color `--color-ink`. Hover swaps to `--color-accent`.
- **Description** in Inter at `--text-sm`, color `--color-text-muted`, max 2 lines.
- **Metadata column** in JetBrains Mono at `--text-xs`, color `--color-text-secondary`. PK/important columns get `color: var(--color-accent)` `font-weight: 600`.
- **Right-aligned count** in Fraunces at `--text-3xl`, with `.label` (rows / entries / cases) in mono `--text-2xs` uppercase.

### Row hover — the left-edge slider
On hover, a petrol (or content-specific accent) bar slides in from the left edge with a width/height transition, while the body background shifts to `--color-bg-alt`. The hover feels like the row pulling toward you. No wholesale scale/shadow.

### Per-row identity via accent color (sketch 004 category pills)
When content does have a categorical axis (news category, court type), category pills color-code:
- `.cat-pill.press-release` → petrol soft bg, petrol text
- `.cat-pill.speech` → ochre-soft bg, ochre text
- `.cat-pill.announcement` → terracotta-soft bg, terracotta text
- `.cat-pill.newsletter` → muted surface-sunken bg, text-secondary

Pills use `border-radius: var(--radius-full)`, mono font, uppercase letter-spacing 0.1em.

## CSS Patterns

### Editorial row (shared base)

```css
.list { border-top: 2px solid var(--color-ink); }
.row {
  display: grid;
  grid-template-columns: 50px 1fr 280px 130px 130px;  /* idx | name+desc | cols | count | date */
  gap: var(--space-6);
  align-items: baseline;
  padding: var(--space-6) 0;
  border-bottom: 1px solid var(--color-border);
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
}
.row::before {
  content: ''; position: absolute; left: 0; top: 50%;
  width: 0; height: 0;
  background: var(--color-accent);
  transition: all 0.2s ease;
  transform: translateY(-50%);
}
.row:hover {
  background: var(--color-bg-alt);
  padding-left: var(--space-6); padding-right: var(--space-4);
  margin-left: calc(-1 * var(--space-6)); margin-right: calc(-1 * var(--space-4));
}
.row:hover::before { width: 3px; height: 60%; left: -3px; }
.row:hover .name { color: var(--color-accent); }

.row .idx { font-family: var(--font-mono); color: var(--color-text-muted); font-size: var(--text-sm); }
.row .name { font-family: var(--font-display); font-size: var(--text-3xl); font-weight: 500; color: var(--color-ink); letter-spacing: -0.01em; line-height: 1.1; display: block; margin-bottom: var(--space-2); transition: color 0.15s ease; }
.row .desc { color: var(--color-text-muted); font-size: var(--text-sm); line-height: 1.5; }
.row .cols { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-text-secondary); line-height: 1.7; }
.row .cols .pk { color: var(--color-accent); font-weight: 600; }
.row .count-col { text-align: right; }
.row .count { font-family: var(--font-display); font-size: var(--text-3xl); font-weight: 500; color: var(--color-ink); display: block; line-height: 1; }
.row .label { font-family: var(--font-mono); font-size: var(--text-2xs); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: var(--tracking-wide); margin-top: 4px; display: block; }
.row .date-col { text-align: right; font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-text-muted); }

@media (max-width: 960px) {
  .row { grid-template-columns: 40px 1fr; gap: var(--space-3); }
  .row > :nth-child(n+3) { display: none; }
}
```

### Category pills (sketch 004)

```css
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
```

### Faceted sidebar (sketch 004)

```css
.feed-layout { display: grid; grid-template-columns: minmax(0,1fr) 240px; gap: var(--space-12); padding-top: var(--space-8); }
.facets { position: sticky; top: 120px; align-self: start; }
.facet-block { padding: var(--space-5) 0; border-top: 2px solid var(--color-accent); }
.facet-block + .facet-block { border-top-color: var(--color-border); }
.facet-block h4 { font-family: var(--font-mono); font-size: var(--text-xs); text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--color-text-muted); margin-bottom: var(--space-3); }
.facet-item { display: flex; justify-content: space-between; padding: var(--space-2) var(--space-3); font-size: var(--text-sm); border-radius: var(--radius-sm); cursor: pointer; }
.facet-item:hover { background: var(--color-surface-sunken); }
.facet-item.active { background: var(--color-accent); color: var(--color-text-inverse); }
.facet-item .count { font-family: var(--font-mono); font-size: var(--text-2xs); opacity: 0.7; }
```

## HTML Structures

### Database row (sketch 002)

```html
<div class="row">
  <div class="idx">01</div>
  <div class="name-col">
    <a href="/{db}/{table}" class="name">{Table name}</a>
    <div class="desc">{Full-text searchable. Primary key on <code>id</code>.}</div>
  </div>
  <div class="cols">
    <span class="pk">id</span> · created · state · tags · ...
  </div>
  <div class="count-col">
    <span class="count">1,148,221</span>
    <span class="label">rows</span>
  </div>
  <div class="date-col">
    <span class="fts">FTS</span><br>
    UPD. 2d ago
  </div>
</div>
```

### News-feed item (sketch 004)

```html
<article class="va-item">
  <div class="va-item-head">
    <span class="date">2026-04-17</span>
    <span class="cat-pill press-release">Press release</span>
  </div>
  <h3 class="va-item-title">{Title}</h3>
  <p class="va-item-excerpt">{First 200 chars of body — optional if content empty.}</p>
  <div class="va-item-foot">
    <span>Record <code>{sha_short}</code></span>
    <a href="{source_url}" class="source-host">Source: {host} ↗</a>
  </div>
</article>
```

## Implementation — Datasette-specific

**Do not replace `table.html`.** Use the `_table-{database}-{table}.html` seam:

- Lookup order: `_table-{db}-{table}.html` → `_table-table-{db}-{table}.html` → `_table.html`
- Replaces only the `<table class="rows-and-columns">` block
- Keeps filter form, FTS search, facets sidebar, sort links, pagination, CSV/JSON export, and the advanced-export pane
- Full `table.html` Jinja context available inside: `display_rows`, `facet_results`, `next_url`, `filters`, `sortable_columns`, `url_csv`, `metadata`, and helpers `urls.row(db, table, pk)` + `path_with_replaced_args(request, {...})`
- Use `row.display("col")` not `row["col"]` so foreign-key labels and `datasette-render-markdown` continue to work
- See `.planning/notes/datasette-styling-limits.md` for the full context

For each news/speech/press-release/judgment/guide table, drop a partial like `templates/_table-{db}-{table}.html` that `{% include %}`s a shared `_partials/feed_card.html`.

## Content-agnostic mapping (sketch 004)

| Table shape | Title | Primary pill | Date | Excerpt | Source |
|-------------|-------|--------------|------|---------|--------|
| `*_news` | `title` | `category` | `published_date` | first N chars of `content` | `source_url` |
| `judgments` | `case_name` | `court` + `citation` | `decision_date` | first tag of `subject_tags[]` | `source_url` |
| `about_singapore_law` | `title` | `section` | `last_scraped` | (omit — `content_length` often 0) | `item_url` |

Cards where body is absent collapse gracefully — the excerpt block disappears, leaving title + meta + source. No new template needed.

## What to Avoid

- **Wide HTML `<table>` rendering for long-text rows.** This is exactly what the current Datasette default does and what the sketches reject. The table view must render as feed cards, not as HTML table cells, for any table with body text.
- **Grouping rows (monthly or by category).** Tested in sketch 004-B — visually heavy, uneven group sizes, Datasette facets already solve slicing.
- **Hero cards at the top of subsequent pages.** Sketch 004-C used "featured + list"; page 2+ has no meaningful "featured" so the pattern breaks. Uniform rows only.
- **Excerpt longer than 2 lines.** Three lines start competing with the title for weight.
- **Dynamic category colors beyond the four defined.** Introducing a 5th color breaks the category semantic at a glance.
- **Making `.row` clickable as a whole vs. the title anchor only.** Screen readers / keyboard users need the `<a>` to be the target. Use CSS to style the anchor but keep the semantic.

## Origin
Synthesized from sketches: 002 (variant B winner), 004 (variant A winner).
Source files: `sources/002-database-table-grid/index.html` (variant B tab), `sources/004-table-as-news-archive/index.html` (variant A tab).
