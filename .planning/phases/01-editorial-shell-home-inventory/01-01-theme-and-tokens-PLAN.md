---
phase: 01-editorial-shell-home-inventory
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - static/css/zeeker-base.css
autonomous: true
requirements:
  - SC-01-palette-applied
  - SC-01-typography-applied
  - SC-01-spacing-scale
tags:
  - theme
  - css
  - design-tokens
must_haves:
  truths:
    - "Body background is warm paper #F5F2EA, never pure white"
    - "Body text uses Inter; all h1-h4 use Fraunces; code/mono uses JetBrains Mono"
    - "Deep petrol #0A4F55, ochre #C08A2E, terracotta #B5552F are exposed as CSS custom properties"
    - "Italic accent pattern (h1 em → petrol, h1 .und → ochre underline) is globally defined"
    - "Link color overrides Datasette's default #276890 with --color-accent petrol"
  artifacts:
    - path: "static/css/zeeker-base.css"
      provides: "Civic-broadsheet palette + Fraunces/Inter/Mono typography tokens + 4px spacing scale + italic-accent-on-h1 signature"
      contains: "--color-bg: #F5F2EA"
  key_links:
    - from: "static/css/zeeker-base.css :root"
      to: "zeeker-base.js (references --color-accent-primary alias)"
      via: "CSS custom property alias"
      pattern: "--color-accent-primary"
    - from: "h1 em selector"
      to: "var(--color-accent)"
      via: "italic signature"
      pattern: "h1 em.*color.*var\\(--color-accent\\)"
---

<objective>
Replace the current "white and plain" token layer in `static/css/zeeker-base.css` with the civic-broadsheet design system: warm paper + deep petrol + ochre + terracotta palette, Fraunces/Inter/JetBrains-Mono typography, 4px spacing scale, and the italic-accent-on-h1 signature move. All component CSS (chrome, cards, rows, feed cards) in later plans will consume these tokens; wrong tokens here cascade into every later plan, so this plan is the foundation.

Purpose: The first ui-polish attempt left placeholder petrol in `:root` but kept most component colors hardcoded and the palette un-spent. Sketch sessions validated the specific tokens and typography moves that make the UI feel editorial. This plan bakes those tokens into the production CSS so later plans can reference them without rework.

Output: Updated `:root` block, new `body` base styles (warm paper bg), new global `a:link` override to beat Datasette's `app.css`, new `h1 em` / `h1 .und` italic-accent CSS — all in `static/css/zeeker-base.css` without breaking the existing Prism SQL styling or the footer `a:link` override added today.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.claude/skills/sketch-findings-zeeker-datasette/SKILL.md
@.claude/skills/sketch-findings-zeeker-datasette/references/theme-system.md
@.claude/skills/sketch-findings-zeeker-datasette/sources/themes/default.css
@.planning/notes/datasette-styling-limits.md

<interfaces>
Datasette injects `/-/static/app.css` which ships `a:link { color: #276890 }` — must be beaten by matching selector specificity loaded later via `extra_css_urls` (already configured in `metadata.json`).

Existing `static/js/zeeker-base.js` references the alias `--color-accent-primary` — keep this alias pointing at `--color-accent` so the JS enhancer keeps working.

Existing fonts are already self-hosted at `static/fonts/{inter,jetbrains-mono,fraunces}-latin.woff2` via `@font-face` at the top of `zeeker-base.css`. Do NOT re-declare them; keep them as-is. (Anchor: the `@font-face` block immediately precedes the `:root { … }` declaration — line numbers may drift over edits; locate by the `@font-face` marker.)

The existing `footer a:link` specificity override block must remain intact. Anchor: it is the LAST rule block in the file (tail of the file, after all component sections). Locate by `tail` / `grep 'footer a:link' static/css/zeeker-base.css` — do not rely on absolute line numbers.

The existing Prism SQL styles (in a dedicated section later in the file) must remain intact. Locate by the Prism banner comment or `.token.keyword` selector.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace :root token block with civic-broadsheet palette + type scale + spacing scale</name>
  <files>static/css/zeeker-base.css</files>
  <read_first>
    - static/css/zeeker-base.css — read the header region (lines 1-~160). Locate the `@font-face` block and the immediately-following `:root { … }` declaration by pattern, not by absolute line number.
    - .claude/skills/sketch-findings-zeeker-datasette/references/theme-system.md — palette rationale + italic-accent pattern
    - .claude/skills/sketch-findings-zeeker-datasette/sources/themes/default.css — canonical :root definition
  </read_first>
  <action>
    Replace the existing `:root { … }` block in `static/css/zeeker-base.css` with the civic-broadsheet tokens below. (Anchor the replacement by the `:root {` opening brace that follows the `@font-face` block — not by line number.) Keep all `@font-face` declarations above the `:root` block intact. Keep `--color-accent-primary` as an alias so `zeeker-base.js` keeps working.

    Exact tokens to write into :root (all of these must be present literally):

    ```css
    :root {
      /* Surfaces — warm paper, never pure white */
      --color-bg: #F5F2EA;
      --color-bg-alt: #EEE9DC;
      --color-surface: #FFFFFF;
      --color-surface-sunken: #F0ECE0;

      /* Back-compat aliases (retain so existing components don't 500) */
      --color-bg-primary: #F5F2EA;
      --color-bg-secondary: #FFFFFF;
      --color-bg-tertiary: #EEE9DC;
      --color-bg-elevated: #F0ECE0;
      --color-surface-raised: #FFFFFF;

      /* Borders */
      --color-border: #D9D3C4;
      --color-border-hover: #B5AD99;
      --color-border-strong: #0A4F55;

      /* Text */
      --color-text: #14201F;
      --color-text-primary: #14201F;
      --color-text-secondary: #3E4F4E;
      --color-text-muted: #6E7A79;
      --color-text-inverse: #F5F2EA;

      /* Brand / editorial accents */
      --color-accent: #0A4F55;
      --color-accent-hover: #063A3F;
      --color-accent-soft: #C4D8D9;
      --color-accent-primary: #0A4F55; /* alias — do not remove; JS references */
      --color-ochre: #C08A2E;
      --color-terracotta: #B5552F;
      --color-ink: #14201F;

      /* Status (retain) */
      --color-success: #10B981;
      --color-warning: #F59E0B;
      --color-info: #3B82F6;

      /* Code */
      --color-code-bg: var(--color-surface-sunken);
      --color-code-text: var(--color-text);

      /* Typography */
      --font-display: 'Fraunces', 'Georgia', serif;
      --font-headline: 'Fraunces', 'Georgia', serif;
      --font-body: 'Inter', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;

      /* Type scale */
      --text-2xs: 0.6875rem;
      --text-xs: 0.75rem;
      --text-sm: 0.875rem;
      --text-base: 1rem;
      --text-lg: 1.125rem;
      --text-xl: 1.375rem;
      --text-2xl: 1.75rem;
      --text-3xl: 2.25rem;
      --text-4xl: 3rem;
      --text-5xl: 4rem;
      --text-6xl: 5.5rem;
      --text-7xl: 7.5rem;
      --text-display: clamp(3rem, 6vw, 5.5rem);

      /* Leading / tracking */
      --leading-tight: 1.05;
      --leading-snug: 1.25;
      --leading-normal: 1.55;
      --tracking-tight: -0.02em;
      --tracking-normal: 0;
      --tracking-wide: 0.08em;
      --tracking-caps: 0.14em;

      /* Spacing — 4px scale */
      --space-1: 4px;
      --space-2: 8px;
      --space-3: 12px;
      --space-4: 16px;
      --space-5: 20px;
      --space-6: 24px;
      --space-8: 32px;
      --space-10: 40px;
      --space-12: 48px;
      --space-16: 64px;
      --space-20: 80px;
      --space-24: 96px;
      --space-32: 128px;

      /* Back-compat named spacing (existing CSS still uses these) */
      --space-xs: 8px;
      --space-sm: 12px;
      --space-md: 16px;
      --space-lg: 24px;
      --space-xl: 32px;
      --space-2xl: 48px;
      --space-3xl: 64px;

      /* Shape */
      --radius-xs: 2px;
      --radius-sm: 4px;
      --radius-md: 6px;
      --radius-lg: 10px;
      --radius-xl: 16px;
      --radius-2xl: 16px;
      --radius-full: 9999px;

      /* Elevation — paper-like, never glowy */
      --shadow-sm: 0 1px 0 rgba(20,32,31,0.04), 0 1px 2px rgba(20,32,31,0.06);
      --shadow-md: 0 2px 4px rgba(20,32,31,0.06), 0 4px 12px rgba(20,32,31,0.06);
      --shadow-lg: 0 8px 24px rgba(20,32,31,0.08);

      /* Decorative rules */
      --rule-hair: 1px solid var(--color-border);
      --rule-accent: 2px solid var(--color-accent);

      /* Transitions */
      --transition-fast: 150ms ease;
      --transition-base: 200ms ease;
      --transition-slow: 400ms ease;

      /* Z-layers (retain) */
      --z-dropdown: 1000;
      --z-sticky: 1020;
      --z-modal: 1040;
    }
    ```

    Additionally append two alternate-theme stubs immediately after :root (copy verbatim from `.claude/skills/sketch-findings-zeeker-datasette/sources/themes/default.css` — the `[data-theme="broadsheet"]` and `[data-theme="petrol-ink"]` blocks in that source file):
    - `[data-theme="broadsheet"] { … }`
    - `[data-theme="petrol-ink"] { … }`

    These are inert until `<html data-theme="...">` is set at runtime — defined-but-not-wired is the desired state per scope-out.
  </action>
  <verify>
    <automated>grep -c -- '--color-bg: #F5F2EA' static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -c -- '--color-accent: #0A4F55' static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -c -- '--color-ochre: #C08A2E' static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -c -- '--color-terracotta: #B5552F' static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -c -- '--color-ink: #14201F' static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -c -- "--font-display: 'Fraunces'" static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -c -- '--text-7xl: 7.5rem' static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -c -- '--space-16: 64px' static/css/zeeker-base.css | awk '{exit ($1>=1)?0:1}' && grep -q 'data-theme="petrol-ink"' static/css/zeeker-base.css && grep -q '\\-\\-color-accent-primary' static/css/zeeker-base.css && tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'</automated>
  </verify>
  <acceptance_criteria>
    - static/css/zeeker-base.css contains literal string `--color-bg: #F5F2EA`
    - static/css/zeeker-base.css contains literal string `--color-accent: #0A4F55`
    - static/css/zeeker-base.css contains literal string `--color-ochre: #C08A2E`
    - static/css/zeeker-base.css contains literal string `--color-terracotta: #B5552F`
    - static/css/zeeker-base.css contains literal string `--color-ink: #14201F`
    - static/css/zeeker-base.css contains literal string `--font-display: 'Fraunces'`
    - static/css/zeeker-base.css contains literal string `--text-7xl: 7.5rem`
    - static/css/zeeker-base.css contains literal string `--space-16: 64px`
    - static/css/zeeker-base.css contains literal string `--color-accent-primary:` (alias retained for JS)
    - static/css/zeeker-base.css contains `[data-theme="petrol-ink"]` block
    - `@font-face` declarations for Inter / JetBrains Mono / Fraunces still present near top of file (immediately above the `:root` block)
    - `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` returns 0 (footer override still in last 20 lines of file — WARN-05)
  </acceptance_criteria>
  <done>The :root block is replaced; all font-face declarations and alternate-theme stubs exist; no other sections of the file have been deleted.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite body/headings/links base styles to spend the palette + add italic-accent-on-h1 signature</name>
  <files>static/css/zeeker-base.css</files>
  <read_first>
    - static/css/zeeker-base.css — read the base-styles region (roughly after `:root` + alternate-theme stubs, before the first component section). Locate by selector patterns (`html {`, `body {`, `h1, h2`), not by absolute line number.
    - .claude/skills/sketch-findings-zeeker-datasette/references/theme-system.md — italic-accent pattern (section "Italic + colored accent on H1")
    - .planning/notes/datasette-styling-limits.md — section 2, why `a:link` beats `.footer-col a` specificity
  </read_first>
  <action>
    Update the BASE STYLES section of `static/css/zeeker-base.css` (immediately after the `:root` close and after the alternate-theme stubs). Replace (do not append) the existing `html`, `body`, `h1-h6`, `a`, `code`, `pre`, `kbd` rules with the civic-broadsheet base. Every rule below must be present verbatim (whitespace flexible):

    ```css
    html {
      font-family: var(--font-body);
      line-height: var(--leading-normal);
      -webkit-text-size-adjust: 100%;
      -webkit-font-smoothing: antialiased;
    }

    body {
      margin: 0;
      padding: 0;
      background: var(--color-bg);   /* warm paper, never pure white */
      color: var(--color-text);
      font-size: var(--text-base);
      line-height: var(--leading-normal);
      min-height: 100vh;
      overflow-x: hidden;
    }

    h1, h2, h3, h4, h5, h6 {
      font-family: var(--font-display);
      font-weight: 500;
      line-height: var(--leading-tight);
      letter-spacing: var(--tracking-tight);
      margin: 0 0 var(--space-4) 0;
      color: var(--color-ink);
    }

    h1 { font-size: var(--text-5xl); font-weight: 400; }
    h2 { font-size: var(--text-4xl); font-weight: 400; }
    h3 { font-size: var(--text-2xl); }
    h4 { font-size: var(--text-xl); }
    h5 { font-size: var(--text-lg); }
    h6 { font-size: var(--text-base); }

    /* Italic-accent-on-h1 signature — the move that carries the editorial feel */
    h1 em, h2 em, h3 em {
      font-style: italic;
      color: var(--color-accent);
      font-weight: 500;
    }
    h1 .und, h2 .und {
      text-decoration: underline;
      text-decoration-color: var(--color-ochre);
      text-decoration-thickness: 4px;
      text-underline-offset: 6px;
      text-decoration-skip-ink: none;
    }

    p { margin: 0 0 var(--space-4) 0; color: var(--color-text-secondary); }

    /* Beat Datasette app.css a:link #276890 with matching-specificity petrol */
    a, a:link, a:visited {
      color: var(--color-accent);
      text-decoration: none;
      transition: color var(--transition-fast);
    }
    a:hover, a:focus {
      color: var(--color-accent-hover);
      text-decoration: underline;
      text-underline-offset: 3px;
    }

    code {
      background: var(--color-code-bg);
      color: var(--color-code-text);
      padding: 2px 6px;
      border-radius: var(--radius-sm);
      font-family: var(--font-mono);
      font-size: 0.9em;
    }

    pre {
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: var(--space-4);
      overflow-x: auto;
      margin: var(--space-4) 0;
    }

    pre code {
      background: transparent;
      color: var(--color-code-text);
      padding: 0;
      font-size: var(--text-sm);
      line-height: 1.55;
    }

    kbd {
      background: var(--color-bg-alt);
      color: var(--color-text);
      padding: 2px 6px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--color-border);
      font-family: var(--font-mono);
      font-size: var(--text-xs);
    }
    ```

    CRITICAL DO-NOT-REGRESS rules:
    - The existing `footer a:link, footer a:visited, footer a:active { … }` override at the TAIL of the file MUST remain exactly as-is, and MUST stay within the last 20 lines of the file. The generic `a, a:link, a:visited` rule above sits earlier in the cascade and must not include anything that trumps the footer block (no `!important`).
    - The existing button-styled-anchor no-underline rules (`a.btn`, `a.cta-primary`, `.header-left`) must be retained or moved intact below the new `a:hover` rule so `.btn` hover does not underline. (Locate by `a.btn` grep.)
    - The existing Prism SQL styles elsewhere in the file must not be touched.
    - Retain the focus-visible rules unchanged (locate by `:focus-visible` selector).
    - Retain the prefers-reduced-motion block unchanged (locate by `@media (prefers-reduced-motion`).
  </action>
  <verify>
    <automated>grep -q 'background: var(--color-bg)' static/css/zeeker-base.css && grep -q 'h1 em' static/css/zeeker-base.css && grep -q 'color: var(--color-accent)' static/css/zeeker-base.css && grep -q 'text-decoration-color: var(--color-ochre)' static/css/zeeker-base.css && grep -q 'a, a:link, a:visited' static/css/zeeker-base.css && grep -q 'footer a:link' static/css/zeeker-base.css && grep -q 'a.btn' static/css/zeeker-base.css && tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'</automated>
  </verify>
  <acceptance_criteria>
    - static/css/zeeker-base.css contains `body { … background: var(--color-bg)` rule
    - static/css/zeeker-base.css contains `h1 em` selector with `color: var(--color-accent)`
    - static/css/zeeker-base.css contains `h1 .und` or `.und` selector with `text-decoration-color: var(--color-ochre)`
    - static/css/zeeker-base.css contains `a, a:link, a:visited` selector OR a bare `a:link` rule at root scope that sets color to `var(--color-accent)` (beats app.css #276890)
    - static/css/zeeker-base.css retains `footer a:link, footer a:visited, footer a:active` override (today's footer fix must still be present)
    - `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` returns 0 (footer override still in last 20 lines — WARN-05)
    - static/css/zeeker-base.css retains button no-underline rules (`a.btn` text-decoration: none)
    - `grep -c 'font-family: var(--font-display)' static/css/zeeker-base.css` returns >= 1 (h1-h6 rule present)
    - No `!important` added to `a:link` or body rules
    - File line count stays within ±500 of pre-edit count (no wholesale deletion)
  </acceptance_criteria>
  <done>Body uses warm paper background, H1-H6 use Fraunces with italic-accent `em` styling, links render petrol, footer fix + button overrides are intact, Prism SQL styling is intact.</done>
</task>

</tasks>

<verification>
After both tasks:

1. `grep -c -- '--color-' static/css/zeeker-base.css` returns at least 30 (full token block present).
2. `grep -c 'Fraunces' static/css/zeeker-base.css` returns >= 2 (font-face + --font-display).
3. Load `http://127.0.0.1:8001/` in a browser — body background is warm paper (#F5F2EA, not pure white), h1 renders Fraunces, `em` inside h1 is petrol.
4. Open DevTools → Elements → `<a>` in content area — computed color is `rgb(10, 79, 85)` (petrol), not Datasette's `rgb(39, 104, 144)`.
5. Footer links on `/` still visible at full contrast (no regression from today's fix).
6. `/fixtures` page still returns 200 (no regression from today's `database.html` bug fix).
</verification>

<success_criteria>
- All :root tokens present with exact hex codes listed in Task 1.
- Body / h1-h6 / a / code / pre / kbd base styles rewritten per Task 2.
- Footer `a:link` override still present AND still in the last 20 lines of the file.
- `/fixtures` returns 200.
- Link color in body computed as `rgb(10, 79, 85)`.
</success_criteria>

<output>
After completion, create `.planning/phases/01-editorial-shell-home-inventory/01-01-theme-and-tokens-SUMMARY.md` describing:
- What tokens shipped (palette hex codes, typography families, spacing scale).
- Any back-compat aliases retained and why.
- Any existing CSS rules preserved verbatim (footer fix, Prism SQL, focus-visible).
- Any follow-up cleanup the executor noticed but did not do (e.g. old `--color-*` variable references elsewhere in the file that should migrate in a later polish pass).
</output>
</content>
