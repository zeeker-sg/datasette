---
phase: 4
slug: port-home-database-pages
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for the first user-visible FastAPI/Jinja port. Combines pytest (Jinja render + route contract), bash + curl (live routing + CSS/font serving + HTML structural assertions), and a final production smoke that authors may re-run on `data.zeeker.sg` (manual gate).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (frontend handlers + Jinja + datasette-client mocks) + bash + curl (live routing + structural HTML) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` (existing; add pytest-httpx for datasette client tests) |
| **Quick run command** | `bash scripts/verify_phase_04.sh` |
| **Full suite command** | `bash scripts/verify_phase_04.sh && cd packages/zeeker-frontend && uv run pytest -q` |
| **Estimated runtime** | ~15 seconds (pytest ~3s, shell assertions ~10s) |

---

## Sampling Rate

- **After every task commit:** Run `bash scripts/verify_phase_04.sh`. For tasks inside plans 04-01/04-03/04-04, also run `cd packages/zeeker-frontend && uv run pytest -q`.
- **After every plan wave:** Full suite (verify_phase_04.sh + frontend pytest + Phase-3 parity wrap to confirm API unchanged).
- **Before `/gsd-verify-work`:** Full suite green + production smoke (Plan 04-05) + operator visual spot-check.
- **Max feedback latency:** 15 seconds (local); production smoke adds deploy roundtrip.

---

## Per-Task Verification Map

> Populated by gsd-planner against actual plan task IDs. The 3 phase REQ-* IDs (REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http) MUST each map to at least one row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-XX | 01 | 1 | REQ-frontend-data-via-http | — | httpx client built at app-lifespan scope; filters module has isolated `_zeeker_*`+hidden filter logic; Jinja2Templates instantiated with autoescape default | pytest | `cd packages/zeeker-frontend && uv run pytest tests/test_client.py tests/test_filters.py -q` | ❌ W0 | ⬜ pending |
| 04-02-XX | 02 | 2 | REQ-eliminate-template-drift | — | zeeker.css + fonts harvested into frontend/static/; CSS contains only theme+shell+home+db sections; no references to feed-card or row-reading sections | shell | `test -f packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css && test -d packages/zeeker-frontend/src/zeeker_frontend/static/fonts && [ $(wc -l < packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css) -ge 2000 ]` | ❌ W0 | ⬜ pending |
| 04-03-XX | 03 | 3 | REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http | — | GET / returns 200 HTML with db card grid, stat band, italic-accent H1, no zeeker-base.css reference; datasette count from live /.json | pytest + shell | `cd packages/zeeker-frontend && uv run pytest tests/test_home.py -q && curl -fsS http://localhost/ \| grep -q '<em' && curl -fsS http://localhost/ \| grep -qv 'zeeker-base.css'` | ❌ W0 | ⬜ pending |
| 04-04-XX | 04 | 3 | REQ-frontend-route-set, REQ-eliminate-template-drift | — | GET /sglawwatch returns 200 HTML with editorial-row table list, hidden tables filtered; GET /nonexistent-db returns 404 | pytest + shell | `cd packages/zeeker-frontend && uv run pytest tests/test_database.py -q && curl -fsS http://localhost/sglawwatch \| grep -q 'headlines' && curl -fsS http://localhost/sglawwatch \| grep -qv '_zeeker_' && curl -s -o /dev/null -w '%{http_code}' http://localhost/nonexistent-database-check \| grep -q '^404$'` | ❌ W0 | ⬜ pending |
| 04-05-XX | 05 | 4 | REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http | T-04-XX | docker-compose.prod.yml + Caddyfile.prod authored; verify_phase_04.sh passes; API parity still holds; post-deploy production smoke OK | shell + manual | `bash scripts/verify_phase_04.sh && ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

Artifacts MUST exist before downstream waves can claim "done":

- [ ] `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` — thin httpx wrapper (Plan 01)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/filters.py` — Jinja custom filters (`plural`, `filesizeformat`; optional `s()` stub) (Plan 01)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` — shell chrome (Plan 01)
- [ ] `packages/zeeker-frontend/pyproject.toml` — pytest-httpx declared (Plan 01)
- [ ] `packages/zeeker-frontend/tests/test_client.py` — datasette client unit tests (Plan 01)
- [ ] `packages/zeeker-frontend/tests/test_filters.py` — Jinja filter unit tests (Plan 01)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` — harvested CSS (~2300 lines) (Plan 02)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/` — Inter + JetBrains Mono + Fraunces .woff2 (Plan 02)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/templates/index.html` — home page (Plan 03)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` — database page (Plan 04)
- [ ] `scripts/verify_phase_04.sh` — structural HTML + live routing assertions (Plan 05)
- [ ] `docker-compose.prod.yml` — production overlay with TLS at `data.zeeker.sg` (Plan 05)
- [ ] `Caddyfile.prod` — production Caddyfile with domain + auto-HTTPS (Plan 05)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual parity with M1: homepage and database page look identical to the M1 versions (palette, typography, card accent rotation, stat band proportions) | REQ-eliminate-template-drift | Pixel-perfect parity can't be automated without visual regression tooling (scripts/visual_qa.py is against datasette templates, not frontend) | Open `http://localhost/` and `http://localhost/sglawwatch` in a browser hard-refreshed (Cmd-Shift-R). Compare against a pre-port screenshot from M1. Document outcome in `04-05-SUMMARY.md`. |
| Production smoke on `https://data.zeeker.sg` | All three | Production-only; TLS handshake + CDN caching + real user agents can surface issues that localhost doesn't | After Plan 04-05 deploy: `curl -fsSI https://data.zeeker.sg/` (expect 200 HTML), `curl -fsS https://data.zeeker.sg/sglawwatch.json \| jq .ok` (expect true; API still works). Document in SUMMARY. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (client/filters/tests/CSS harvest/templates/verifier/prod compose)
- [ ] No watch-mode flags (pytest runs single-pass)
- [ ] Feedback latency < 15s local; prod smoke separate
- [ ] `nyquist_compliant: true` set in frontmatter after planner populates the Per-Task Verification Map

**Approval:** pending
