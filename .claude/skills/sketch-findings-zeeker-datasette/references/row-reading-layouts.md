# Row Reading Layouts

The `/{database}/{table}/{pk}` page — a single record viewed as a readable article. Three variants sketched (magazine / broadsheet / structured hybrid), all generic enough to apply across news, judgments, and legal guides. No winner picked yet — this reference captures the design vocabulary and the content-type field mapping.

## Design Decisions

### The single biggest move: display serif + comfortable measure
Datasette's default row page is a `<dl>` of `field: value`. That treats a 400-word news article body identically to a SHA-256 id. For long-text content the body must be promoted to hero and the other fields demoted to chrome.

All three sketched variants (A magazine / B broadsheet / C structured hybrid) share:
- **Body in Fraunces opsz-tuned** at 1.125rem – 1.1875rem, line-height 1.65–1.7 (variant C uses Inter body for closer-to-app feel — tradeoff).
- **Max-width 60–68ch** on the reading column. Never full width.
- **Display-serif title** at `--text-5xl` (5rem) or larger for broadsheet-style (B uses `clamp(2.5rem, 6vw, 5rem)`).
- **Kicker eyebrow** — mono terracotta, short prefix (agency / court / section).

### Three layouts, three uses
- **A · Magazine feature** — reading column left + sticky metadata sidebar right, drop-cap on first paragraph, "More from {agency}" strip at the bottom. Best when related items matter. Layout grid `minmax(0,1fr) 280px`.
- **B · Editorial broadsheet** — dark dateline strip, full-width centered column, italic-accent headline, 4-column meta strip below title, double-ruled source coda at bottom. Most "designed"; fewest chrome distractions. Best when the content IS the whole experience (a single judgment).
- **C · Structured hybrid** — reading content left + full `<dl>` of raw record fields right. Keeps developer/debugger utility while promoting content. Best for tables where the record identity (SHA, fetched_at, word_count, language) is genuinely useful to casual readers.

### Generic row anatomy — one layout, field binding per table

| Slot | News / speech | Judgment | Guide |
|------|---------------|----------|-------|
| Kicker | `category` pill | `court` + `citation` | `section` |
| Title | `title` | `case_name` | `title` |
| Byline / dateline | date · agency · source | `decision_date` · judges · LawWatch | `last_scraped` · LawWatch |
| Body | `content` | judgment text | `content` (often empty → source link-out only) |
| Secondary tags | — | `subject_tags[]` as chip row | — |
| Source | `source_url` | `source_url` | `item_url` |
| Sidebar meta | `id`, `published_date`, `fetched_at` | `id`, `citation`, `case_numbers`, `court` | `id`, `home_page`, `content_length` |

**Do not build three separate templates.** Implementation is likely one `row.html` that branches on which columns are present, OR one per-table `row-{db}-{table}.html` that imports a shared `_partials/article.html` with field bindings passed in.

### Drop cap as the signature move (variant A)
One small styling detail that moves the page from "article" to "magazine":

```css
.article-body p:first-of-type::first-letter {
  font-family: var(--font-display);
  float: left;
  font-size: 4.5em;
  line-height: 0.85;
  font-weight: 500;
  color: var(--color-accent);
  margin: 2px var(--space-3) 0 -2px;
}
```

## CSS Patterns

### Article body with serif (variants A and B)

```css
.article-body {
  font-family: 'Fraunces', serif;
  font-optical-sizing: auto;
  font-variation-settings: 'opsz' 11, 'SOFT' 50;
  font-size: 1.125rem;
  line-height: 1.65;
  color: var(--color-text);
  max-width: 62ch;
}
.article-body p { margin: 0 0 var(--space-5); }
.article-body p:first-of-type { font-size: 1.25rem; line-height: 1.55; }
.article-body h2 { font-family: var(--font-display); font-size: var(--text-2xl); font-weight: 500; margin: var(--space-10) 0 var(--space-4); }
.article-body ul { padding-left: var(--space-6); }
.article-body li { margin-bottom: var(--space-2); }
```

### Pull quote (variant A side, B centred)

```css
/* A — left border */
.pullquote {
  font-family: var(--font-display);
  font-style: italic;
  font-size: var(--text-3xl);
  font-weight: 400;
  color: var(--color-ink);
  line-height: 1.25;
  margin: var(--space-8) 0;
  padding: var(--space-6) 0 var(--space-6) var(--space-8);
  border-left: 3px solid var(--color-ochre);
  max-width: 22ch;
}

/* B — top-bottom rules, centered */
.pullquote-center {
  font-family: var(--font-display); font-style: italic;
  font-size: var(--text-3xl); line-height: 1.25;
  margin: var(--space-10) auto;
  padding: var(--space-6) var(--space-8);
  border-top: 3px solid var(--color-ochre);
  border-bottom: 1px solid var(--color-border);
  text-align: center;
  max-width: 50ch;
}
```

### Sticky metadata sidebar (variant A)

```css
.aside { position: sticky; top: calc(52px + var(--space-8)); }
.aside-block { border-top: 2px solid var(--color-accent); padding: var(--space-4) 0 var(--space-6); margin-bottom: var(--space-6); }
.aside-block + .aside-block { border-top-color: var(--color-border); }
.aside h4 { font-family: var(--font-mono); font-size: var(--text-xs); text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--color-text-muted); margin-bottom: var(--space-3); font-weight: 600; }
.aside dt { font-family: var(--font-mono); font-size: var(--text-2xs); text-transform: uppercase; letter-spacing: var(--tracking-wide); color: var(--color-text-muted); margin-top: var(--space-3); }
.aside dd { font-family: var(--font-display); font-size: var(--text-base); color: var(--color-ink); margin: 2px 0 0; }
.aside dd.hash { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-text-secondary); word-break: break-all; }
```

### Dark dateline strip (variant B)

```css
.dateline {
  background: var(--color-ink); color: var(--color-bg);
  padding: var(--space-3) 0;
  font-family: var(--font-mono); font-size: var(--text-xs);
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
}
.dateline .container { display: flex; gap: var(--space-6); align-items: center; flex-wrap: wrap; }
.dateline .agency { color: var(--color-ochre); font-weight: 700; }
.dateline .record { color: rgba(245,242,234,0.6); margin-left: auto; }
```

### Source coda with double-rule divider (variant B)

```css
.coda {
  max-width: 62ch; margin: var(--space-16) auto 0;
  padding: var(--space-8) 0 0;
  border-top: 4px double var(--color-ink);
  text-align: center;
}
.coda-label { font-family: var(--font-mono); font-size: var(--text-xs); text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--color-text-muted); margin-bottom: var(--space-3); }
.coda a { font-family: var(--font-display); font-size: var(--text-base); color: var(--color-accent); word-break: break-all; }
.coda .fingerprint { font-family: var(--font-mono); font-size: var(--text-2xs); color: var(--color-text-muted); margin-top: var(--space-4); }
```

## HTML Structures

### Magazine-style article (variant A skeleton)

```html
<article class="article">
  <div class="read">
    <div class="kicker"><span class="agency">ACRA</span><span>Press release</span></div>
    <h1 class="title">{Title with <em>italic accent</em>}</h1>
    <p class="lede">{First paragraph as italic lede.}</p>
    <div class="byline">
      <span class="dateline">{Date}</span>
      <span class="dot">·</span>
      <span>{Agency}</span>
      <span class="dot">·</span>
      <a href="{source_url}">Source ↗</a>
    </div>
    <div class="article-body">
      <p>{Body paragraphs with drop cap on first...}</p>
      <blockquote class="pullquote">{Key line}</blockquote>
      <p>{More body...}</p>
    </div>
    <div class="source-citation">
      <strong>Source</strong>
      <a href="{source_url}">{source_url}</a><br>
      Fetched {date} · SHA-256: <code>{sha_short}</code>
    </div>
  </div>
  <aside class="aside">
    <div class="aside-block">
      <h4>Record</h4>
      <dl>{generic field mapping}</dl>
    </div>
    <div class="aside-block">
      <h4>Export this record</h4>
      <div class="actions">
        <a class="primary" href="?_format=json">View as JSON</a>
        <a class="ghost" href="?_format=csv">Download CSV</a>
      </div>
    </div>
  </aside>
</article>
```

## What to Avoid

- **Body column wider than 68ch.** Reading comfort breaks immediately above 72ch. Cap the max-width on the text, not the layout.
- **Drop cap on body text shorter than 3 paragraphs.** Looks decorative and empty.
- **SHA id in the hero area.** It belongs in the sidebar or coda. The user doesn't read for the SHA.
- **Big "Related from this agency" strip when there are 2 related items.** Only render when there are 3+ with enough metadata to make the strip useful.
- **Three variants as three templates.** The sketches were exploratory; production is one layout with conditional slots.
- **Using Inter body for long-form legal/policy text.** Serif reads better for anything past 500 words. Variant C's sans-serif body was ranked lower precisely for this reason.

## Origin
Synthesized from sketch 003 (three variants; generic layout, no single winner yet).
Source file: `sources/003-row-as-article/index.html`.
Field-mapping captured during post-design review when schemas for `judgments` and `about_singapore_law` revealed the content-type breadth.
