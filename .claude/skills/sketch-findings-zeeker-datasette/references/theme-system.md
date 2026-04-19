# Theme System

The visual vocabulary for the zeeker-datasette V2 shell. All sketches link to one `themes/default.css` that defines CSS custom properties only — no component styles, no layout rules. Component styles live in per-component references.

## Design Decisions

### Palette — civic broadsheet, color-confident
The starting palette was already defined as deep petrol (`#0A4F55`) but was barely being spent. Winning direction uses it with confidence alongside warm paper and two editorial accent colors:

- **`--color-bg: #F5F2EA`** — warm off-white paper; the default surface. Never pure white.
- **`--color-bg-alt: #EEE9DC`** — darker paper band for alternating sections. Used inside alternating `.section.alt`.
- **`--color-surface: #FFFFFF`** — cards / panels only. Pure white reserved for elevation, not backgrounds.
- **`--color-ink: #14201F`** — near-black with a petrol hint. All display typography, dark chrome (nav, CTA).
- **`--color-accent: #0A4F55`** — deep petrol. Primary brand, links, primary buttons, stat band background.
- **`--color-ochre: #C08A2E`** — editorial highlight. Speech category, secondary accent rotation on cards.
- **`--color-terracotta: #B5552F`** — data callout. Announcement category, tertiary accent rotation, kicker color.
- **`--color-text-secondary: #3E4F4E`** — body text with a slight cool cast.
- **`--color-text-muted: #6E7A79`** — metadata, timestamps, eyebrow labels.

Two alternate themes documented for future exploration: `[data-theme="broadsheet"]` (cream + ink-red) and `[data-theme="petrol-ink"]` (dark mode, petrol surfaces + ochre accent).

### Typography — Fraunces for display, Inter for body, JetBrains Mono for data
Three families, each with a specific job. Fraunces is opsz-aware for body use (not just display).

- **`--font-display: 'Fraunces', 'Georgia', serif`** — all `h1`/`h2`/`h3`/`h4`, kickers, large display numbers. Use 400 or 500 weight. Italic 400 for emphasis (`em` inside headings is styled as a colored accent).
- **`--font-body: 'Inter', system-ui, sans-serif`** — body copy in lists/cards, buttons, form fields, menu links. 300-500 weights.
- **`--font-mono: 'JetBrains Mono', monospace`** — kickers, section numbers (№ 01), dates, SHA ids, column lists, record identifiers, facet labels. 400-500 weights.

Type scale runs from `--text-2xs: 0.6875rem` up to `--text-7xl: 7.5rem`. Display headlines lean into the upper end — 4–7rem is normal for hero H1s. Body fluid around 1rem / 1.125rem.

### Spacing — 4px-based, generous for editorial
Scale: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64 / 80 / 96 / 128. Use `--space-16` (64px) and above for section padding. Editorial layouts deliberately prefer more whitespace than a conventional dashboard.

### Shapes — restrained
- **`--radius-sm: 4px`** — buttons, chips, inputs.
- **`--radius-md: 6px`** — cards (sparingly — most cards use straight edges with top-border accent).
- **`--radius-full: 9999px`** — category pills only.

Shadows are subtle and paper-like, never glowy:
- `--shadow-sm: 0 1px 0 rgba(20,32,31,0.04), 0 1px 2px rgba(20,32,31,0.06)`
- `--shadow-md` / `--shadow-lg` for hover elevation only.

### Italic + colored accent on H1 — the signature move
Every major heading has an italicized word inside `<em>` tags styled in `--color-accent`. Example: `<h1>Public data, <em>rendered</em> legible.</h1>`. Pairs with an underlined span (`<span class="und">`) using ochre decoration color. This one typographic pattern carries most of the "editorial" signal.

## CSS Patterns

### Variable block (trimmed to essentials)

```css
:root {
  --color-bg: #F5F2EA;
  --color-bg-alt: #EEE9DC;
  --color-surface: #FFFFFF;
  --color-ink: #14201F;
  --color-accent: #0A4F55;
  --color-accent-hover: #063A3F;
  --color-accent-soft: #C4D8D9;
  --color-ochre: #C08A2E;
  --color-terracotta: #B5552F;
  --color-text: #14201F;
  --color-text-secondary: #3E4F4E;
  --color-text-muted: #6E7A79;
  --color-text-inverse: #F5F2EA;
  --color-border: #D9D3C4;

  --font-display: 'Fraunces', 'Georgia', serif;
  --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;

  --tracking-tight: -0.02em;
  --tracking-caps: 0.14em;

  --radius-sm: 4px;
  --radius-full: 9999px;
}
```

### Italic accent headline pattern

```html
<h1>Public data, <em>rendered</em> <span class="und">legible</span>.</h1>
```

```css
h1 em { font-style: italic; color: var(--color-accent); font-weight: 500; }
h1 .und { text-decoration: underline; text-decoration-color: var(--color-ochre); text-decoration-thickness: 4px; text-underline-offset: 6px; }
```

### Small-caps eyebrow label

```css
.kicker, .section-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--color-terracotta);
  font-weight: 600;
}
.kicker::before { content: '— '; }  /* or use '→ ' or '№ 01 · ' depending on context */
```

## HTML Structures

### Font loading (in-CSS import, for sketches)

```css
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700;9..144,900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```

For production, self-host the woff2 files in `static/fonts/` as the existing V2 base does. The Fraunces opsz axis must be preserved — body-sized Fraunces (`opsz` 11) reads very differently from display (`opsz` 100+).

## What to Avoid

- **Pure white page backgrounds.** `#FFF` is reserved for cards and inputs. Body is always `--color-bg` (warm paper).
- **Dark blue links.** Datasette's default `app.css` ships `a:link { color: #276890 }` — must be overridden with `--color-accent` (`#0A4F55`). Specificity wars documented in `datasette-styling-limits.md`.
- **Loud accents in large fills.** Petrol / ochre / terracotta are used as borders, small fills, text color — almost never as large background fills except the petrol stat band.
- **More than 3 accent colors on one page.** Petrol + ochre + terracotta rotating through the card grid is the ceiling. Adding a fourth breaks the broadsheet identity.
- **Sans-serif display type.** Display slots (h1/h2, large numbers) must use Fraunces. Inter is for body only.
- **Decorative shadows.** Shadows are for elevation on hover, never as ambient decoration.

## Origin
Synthesized from sketches: 001, 002, 003, 004
Theme file: `sources/themes/default.css`
