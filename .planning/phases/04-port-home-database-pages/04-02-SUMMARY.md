---
phase: 04-port-home-database-pages
plan: 02
subsystem: ui
tags: [css, fonts, static-assets, harvest, woff2, fastapi, jinja]

# Dependency graph
requires:
  - phase: 04-port-home-database-pages/04-01
    provides: frontend FastAPI scaffold with static file mount at /static

provides:
  - zeeker.css: 1102-line harvested stylesheet (theme + shell chrome + home + database editorial rows + tail footer override)
  - inter-latin.woff2: self-hosted Inter body font (byte-identical copy from M1)
  - jetbrains-mono-latin.woff2: self-hosted JetBrains Mono code font (byte-identical copy from M1)
  - fraunces-latin.woff2: self-hosted Fraunces display font (byte-identical copy from M1)

affects: [04-03-home-page, 04-04-database-page, 04-05-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS harvest: sed -n 'start,endp' slice from M1 zeeker-base.css — surgical, reviewable as diff"
    - "Balanced-brace verification via grep -c before commit"
    - "var() token resolution check via comm -23 on used vs declared sets"

key-files:
  created:
    - packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css
    - packages/zeeker-frontend/src/zeeker_frontend/static/fonts/inter-latin.woff2
    - packages/zeeker-frontend/src/zeeker_frontend/static/fonts/jetbrains-mono-latin.woff2
    - packages/zeeker-frontend/src/zeeker_frontend/static/fonts/fraunces-latin.woff2
  modified: []

key-decisions:
  - "Extend token harvest range to L352 (not L350) to close kbd{} block — plan specified L350 but kbd's closing brace lands at L352"
  - ".visually-hidden appended inline rather than harvested from L354-550 range — cleaner than widening legacy misc range that contains unrelated V1 selectors"
  - "uv.lock datasette version bump (0.65.1→0.65.2) left unstaged — out of scope for CSS harvest task"

patterns-established:
  - "CSS harvest via sed slices — reproducible, auditable via diff against M1 source"
  - "Post-harvest sanity script: brace balance + @font-face count + font URL presence + class presence + var() resolution + size bounds"

requirements-completed: [REQ-eliminate-template-drift]

# Metrics
duration: 15min
completed: 2026-04-22
---

# Phase 4 Plan 02: CSS Harvest + Self-hosted Fonts Summary

**Harvested zeeker.css (1102 lines, 6.6 KB gzipped) from M1's 4116-line zeeker-base.css — theme tokens + shell chrome + home + database editorial rows + tail footer override; three woff2 fonts copied byte-identical from M1 static/fonts/**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-22
- **Completed:** 2026-04-22
- **Tasks:** 1
- **Files modified:** 4 (all new)

## Accomplishments

- zeeker.css harvested as strict subset of M1: 1102 lines, balanced braces, 3 @font-face declarations, all var() tokens resolve, no Phase-5 va-feed leak
- All 3 woff2 font files copied byte-identical from M1 `static/fonts/`: inter-latin (73080B), jetbrains-mono-latin (21168B), fraunces-latin (108812B)
- .visually-hidden utility appended inline for 04-03/04-04 search label accessibility
- 30/30 frontend pytest tests still passing

## Task Commits

1. **Task 1: Copy 3 woff2 fonts + harvest CSS via sed slice** - `bc6bbfa` (feat)

**Plan metadata:** (to be added by orchestrator)

## Exact Line Ranges Harvested

| Range | Description | Lines extracted |
|-------|-------------|-----------------|
| 1–163 | Header comment + @font-face declarations + opening :root tokens | 163 |
| 164–352 | Remaining tokens + [data-theme="broadsheet"/"petrol-ink"] + base typography + italic-accent (h1 em, h1 .und) + global a/a:link/a:visited + code/pre/kbd | 189 (plan said 350 — extended to 352 to close kbd{}) |
| 3160–3862 | SHELL CHROME + HOME + DATABASE EDITORIAL ROWS phase-01 banner sections | 703 |
| 4097–4116 | Tail footer link override | 20 |
| appended | .visually-hidden utility (inline) | 1 |
| **Total** | | **1102** |

## Final Metrics

- **CSS line count:** 1102
- **CSS gzipped size:** ~6.6 KB
- **Brace balance:** 167 open / 167 close
- **@font-face declarations:** 3
- **var() undefined references:** 0
- **Phase-5 leak (va-feed):** absent

## Font File Sizes (byte-identical to M1 source)

| Font | Size |
|------|------|
| inter-latin.woff2 | 73,080 bytes |
| jetbrains-mono-latin.woff2 | 21,168 bytes |
| fraunces-latin.woff2 | 108,812 bytes |

## Decisions Made

- **Range extension to L352:** Plan specified `164,350` but line 350 is inside `kbd {}` (font-family property). The closing brace is at line 352. Extended to `164,352` to produce balanced output. This is a deviation from the plan's sed recipe, not a design change.
- **.visually-hidden inline:** RESEARCH §CSS Harvest Strategy notes line range 354–550 as "partial harvest — keep .visually-hidden, drop the rest". Rather than widening the harvest to include unrelated legacy selectors, the utility was appended inline as a single minified rule. Cleaner and matches the plan's own inline declaration in the action step.
- **uv.lock not staged:** Running `uv run pytest` regenerated the lock file with datasette 0.65.1→0.65.2. This is incidental and out of scope for this plan's CSS harvest.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extended CSS harvest range from L350 to L352 to close kbd{} block**
- **Found during:** Task 1 (post-harvest brace balance check)
- **Issue:** Plan's `sed -n '164,350p'` cuts mid-rule inside `kbd {}` — closing brace at line 352 was excluded, producing 167 open / 166 close
- **Fix:** Changed harvest range from `164,350` to `164,352` (adds font-size property + closing brace of kbd block)
- **Files modified:** packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css
- **Verification:** Brace balance check passes (167/167); all other sanity checks pass
- **Committed in:** bc6bbfa (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — unbalanced braces from off-by-2 line range)
**Impact on plan:** Minor correction to sed line range. No design changes. All must_haves satisfied.

## Issues Encountered

- M1-side tests (test_download_from_s3, test_manage, test_cache_headers) fail with ModuleNotFoundError — pre-existing, unrelated to this plan. Frontend tests 30/30 green.

## Known Stubs

None — this plan delivers static assets only. No template rendering or data wiring.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. Static asset delivery only (threat model in plan covers the supply-chain and routing surface).

## Next Phase Readiness

- 04-03 (home page `index.html`) and 04-04 (database page `database.html`) can reference `/static/css/zeeker.css` via base.html's existing `<link>` tag — no further CSS work needed in Phase 4
- Font loading will be verified at the 04-05 human-verify checkpoint (full visual render)
- Live-stack asset check (docker compose up + curl 200 assertions) deferred to 04-05 per plan's verification section

---
*Phase: 04-port-home-database-pages*
*Completed: 2026-04-22*

## Self-Check: PASSED

- `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` — FOUND
- `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/inter-latin.woff2` — FOUND
- `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/jetbrains-mono-latin.woff2` — FOUND
- `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/fraunces-latin.woff2` — FOUND
- Commit `bc6bbfa` — FOUND (feat(04-02): harvest M1 CSS subset + copy 3 woff2 fonts into frontend package)
