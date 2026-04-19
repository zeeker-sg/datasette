# Home Layout

The `/` page — hero, stat band, "Available Data" card grid, "How to use" three-column, dark CTA. Pattern: editorial shell (from shell-and-chrome) wraps a card-grid data section that scales to 12+ databases.

## Design Decisions

Sketch 001 winner: **Variant D — Synthesis: editorial shell + card grid**. Combined B's chrome (dark nav, warm hero, petrol stat band, dark CTA, numbered section framing) with A's card-grid treatment for the "Available data" section. The synthesis won because:

- B's full-editorial-rows approach didn't scale visually for 12 databases — rows all look alike at that count, so the user can't locate a database by eye.
- A's cards alone felt "too light" (the whole user complaint). Pairing them with B's editorial chrome solved that.
- Cards scale linearly: 4 → 12 → 24 databases all work.

### Key home-specific moves

1. **Numbered section labels** (`№ 01 · Databases`, `№ 02 · How to use`) in mono terracotta between major sections. Gives the page the feel of an ordered broadsheet front page.
2. **Accent rotation on cards** — `border-top` rotates through petrol / ochre / terracotta via `:nth-child(3n+N)`. Matching chip backgrounds rotate per card. Visual rhythm without per-card semantic meaning.
3. **Mono index numbers** (`01`, `02`, …) in card top-right corner. Mono-scale row count (`1,148,221`) in display serif, with small mono unit (`rows`).
4. **Dark CTA block at page end** — inverse of nav. Large italic Fraunces H2 with ochre "em" accent, ghost + primary buttons (ochre primary against ink background).

## CSS Patterns

### Card grid with rotating accent

```css
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-4); }
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-top: 3px solid var(--color-accent);
  padding: var(--space-6);
  position: relative;
  transition: all 0.2s ease;
  cursor: pointer;
}
.card:nth-child(3n+2) { border-top-color: var(--color-ochre); }
.card:nth-child(3n+3) { border-top-color: var(--color-terracotta); }
.card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }

.card .idx { position: absolute; top: var(--space-3); right: var(--space-4); font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-text-muted); }
.card .meta { display: flex; gap: var(--space-3); color: var(--color-text-muted); font-size: var(--text-2xs); text-transform: uppercase; letter-spacing: var(--tracking-wide); margin-bottom: var(--space-3); font-family: var(--font-mono); }
.card h3 { font-family: var(--font-display); font-size: var(--text-2xl); font-weight: 500; margin-bottom: var(--space-2); letter-spacing: -0.01em; }
.card .count { font-family: var(--font-display); font-size: var(--text-xl); font-weight: 500; color: var(--color-ink); margin-bottom: var(--space-3); }
.card .count small { font-family: var(--font-body); font-size: var(--text-xs); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: var(--tracking-wide); margin-left: 4px; }

.chip { font-size: var(--text-2xs); background: var(--color-accent-soft); color: var(--color-accent); padding: 3px 8px; border-radius: var(--radius-full); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; font-family: var(--font-body); }
.card:nth-child(3n+2) .chip { background: rgba(192,138,46,0.15); color: var(--color-ochre); }
.card:nth-child(3n+3) .chip { background: rgba(181,85,47,0.15); color: var(--color-terracotta); }
```

### Dark CTA block

```css
.cta {
  background: var(--color-ink); color: var(--color-bg);
  padding: var(--space-20) 0; text-align: center;
}
.cta h2 { font-family: var(--font-display); font-size: var(--text-5xl); font-weight: 400; color: var(--color-bg); max-width: 700px; margin: 0 auto var(--space-6); line-height: 1.05; }
.cta h2 em { font-style: italic; color: var(--color-ochre); }
.cta p { color: var(--color-bg); opacity: 0.75; max-width: 520px; margin: 0 auto var(--space-8); font-size: var(--text-lg); font-weight: 300; }
.cta-actions { display: flex; gap: var(--space-4); justify-content: center; }
.btn-primary { background: var(--color-ochre); color: var(--color-ink); padding: var(--space-4) var(--space-8); font-weight: 600; border: 0; font-size: var(--text-base); }
.btn-primary:hover { background: var(--color-bg); transform: translateY(-1px); }
.btn-ghost { background: transparent; color: var(--color-bg); padding: var(--space-4) var(--space-8); border: 1px solid rgba(245,242,234,0.4); font-weight: 500; }
```

## HTML Structures

### Database card (one entry in the grid)

```html
<article class="card">
  <span class="idx">01</span>
  <div class="meta"><span>{tag}</span><span>· updated {date}</span></div>
  <h3>{title}</h3>
  <p>{description}</p>
  <div class="count">{row_count} <small>rows</small></div>
  <div class="chips"><span class="chip">{tag1}</span><span class="chip">{tag2}</span></div>
</article>
```

### Section with framing

```html
<section class="section">
  <div class="container">
    <div class="section-num">№ 01 · Databases</div>
    <div class="section-head">
      <h2>Four years of curated public data, <em>ready to query</em>.</h2>
      <div class="aside">
        Each dataset comes with schema, source citation, and full SQL access.
        <br><a href="#">View catalogue (12) →</a>
      </div>
    </div>
    <div class="cards">
      <!-- cards -->
    </div>
  </div>
</section>
```

## What to Avoid

- **Cards without the accent-rotation.** A monochrome card grid is exactly what the existing site has — the whole point of the sketch is the rotation.
- **More than 2 chips per card.** Card becomes busy; card width also becomes a constraint.
- **Hover shadow without the `translateY(-2px)`.** The lift is what makes it feel responsive. Shadow alone feels heavy.
- **Radial-gradient dots / patterns in hero.** Tried in variant B, muted in the final direction — the pattern pulls attention from the headline.
- **Centered hero.** Asymmetric `7fr 5fr` with metadata right is the winning layout. Centered felt generic in all tests.
- **Ochre as the CTA background color.** Ink on ochre reads as a warning. Ink background with ochre CTA button is the right polarity.

## Origin
Synthesized from sketch 001 (variant D winner).
Source file: `sources/001-home-editorial-hero/index.html` (variant D tab).
