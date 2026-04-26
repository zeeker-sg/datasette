---
phase: 5
slug: port-table-browse-row-view
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-25
last_updated: 2026-04-25
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Detailed test pyramid lives in `05-RESEARCH.md` `## Validation Architecture` section.
> The Per-Task Verification Map below is filled in by the planner and consumed by `/gsd-execute-phase`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 + pytest-httpx 0.36.0 (carry-forward Phase 4) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` |
| **Quick run command** | `cd packages/zeeker-frontend && uv run pytest -x -q` |
| **Full suite command** | `cd packages/zeeker-frontend && uv run pytest -v` |
| **Verifier (E2E)** | `bash scripts/verify_phase_05.sh` (requires running stack — `docker compose up -d` first) |
| **Estimated runtime** | unit + integration ~6s; full suite + verifier ~25s |

---

## Sampling Rate

- **After every task commit:** Run `cd packages/zeeker-frontend && uv run pytest -x -q`
- **After every plan wave:** Run full suite `cd packages/zeeker-frontend && uv run pytest -v`
- **Before `/gsd-verify-work`:** Full suite green AND `verify_phase_05.sh` exits 0
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-T1 | 05-01 | 1 | REQ-frontend-data-via-http | T-05-01 | fixtures don't ship live PII; load via stdlib json | structural | `python -c "import json; ..."` (4 fixture validations + pytest --collect-only) | yes (after task) | ⬜ pending |
| 05-01-T2 | 05-01 | 1 | REQ-frontend-data-via-http | T-05-01, T-05-02 | tilde_encode prevents URL ambiguity (Pitfall 5); url helpers are pure | unit | `cd packages/zeeker-frontend && uv run pytest tests/test_urls.py -q -x` | yes | ⬜ pending |
| 05-01-T3 | 05-01 | 1 | REQ-frontend-data-via-http | T-05-02, T-05-01 | fetch_table allowlist drops unknown _-prefixed params (smuggling); _shape=objects forced; 404→None | unit | `cd packages/zeeker-frontend && uv run pytest tests/test_datasette_client_table_row.py -q -x` | yes | ⬜ pending |
| 05-01-T4 | 05-01 | 1 | REQ-frontend-route-set, REQ-frontend-data-via-http | T-05-03 | hidden-table prefix+suffix guard at route boundary; both routes 404 _zeeker_*/* _fts* | structural + ASGI smoke | `python -c "from zeeker_frontend.main import app; ..."` + ASGI smoke for hidden-table 404s | yes | ⬜ pending |
| 05-02-T1 | 05-02 | 2 | REQ-frontend-route-set, REQ-frontend-data-via-http | T-05-01, T-05-02, T-05-03, T-05-05 | route-boundary hidden guard; fetch_table allowlist consumed; next_url rewrite | structural | grep + `python -c "from zeeker_frontend.routes_table import router"` | yes | ⬜ pending |
| 05-02-T2 | 05-02 | 2 | REQ-eliminate-template-drift, REQ-frontend-route-set | T-05-04 | autoescape preserved; no `\|safe` on dataset content | structural | grep for class names + `! grep '\|safe'` | yes | ⬜ pending |
| 05-02-T3 | 05-02 | 2 | REQ-frontend-route-set, REQ-frontend-data-via-http, REQ-eliminate-template-drift, REQ-api-byte-parity | T-05-01..T-05-05 | full integration coverage of must_haves; export anchors direct (D-05); next_url relative (Pitfall 2); hidden 404 | integration | `cd packages/zeeker-frontend && uv run pytest tests/test_routes_table.py -q -x` | yes | ⬜ pending |
| 05-03-T1 | 05-03 | 2 | REQ-frontend-route-set, REQ-frontend-data-via-http | T-05-01, T-05-03 | route-boundary hidden guard; pk_label truncation | structural | grep + `python -c "from zeeker_frontend.routes_row import router"` | yes | ⬜ pending |
| 05-03-T2 | 05-03 | 2 | REQ-eliminate-template-drift, REQ-frontend-route-set | T-05-04, T-05-05 | autoescape preserved; long-text uses native <details>; rel='noopener noreferrer' on source links | structural | grep for class names + `! grep '\|safe'` | yes | ⬜ pending |
| 05-03-T3 | 05-03 | 2 | REQ-frontend-route-set, REQ-frontend-data-via-http, REQ-eliminate-template-drift | T-05-01..T-05-05 | 4-mode integration coverage; rowid-PK fallback; 3-segment breadcrumb truncated | integration | `cd packages/zeeker-frontend && uv run pytest tests/test_routes_row.py -q -x` | yes | ⬜ pending |
| 05-04-T1 | 05-04 | 2 | REQ-frontend-route-set, REQ-eliminate-template-drift | T-05-04, T-05-06 | no dataset-keyed url()/content(); no new tokens | structural | python brace+token validator + `tail -3 \| grep visually-hidden` | yes | ⬜ pending |
| 05-05-T1 | 05-05 | 3 | REQ-eliminate-template-drift, REQ-frontend-route-set | n/a | hidden-table wildcard preserved; no new top-level config | structural | python JSON validator (11 display blocks; wildcard intact) | yes | ⬜ pending |
| 05-05-T2 | 05-05 | 3 | REQ-api-byte-parity, REQ-frontend-route-set, REQ-frontend-data-via-http | T-05-01, T-05-03, T-05-05 | E2E coverage of all must_haves; Phase-6 boundary; API parity wrap | E2E (offline shape check) | `bash -n scripts/verify_phase_05.sh` + grep section presence | yes | ⬜ pending |
| 05-05-T3 | 05-05 | 3 | n/a | n/a | deploy decision rationale captured | structural | grep for required headings | yes | ⬜ pending |
| 05-05-T4 | 05-05 | 3 | REQ-api-byte-parity, REQ-frontend-route-set, REQ-frontend-data-via-http, REQ-eliminate-template-drift | T-05-01, T-05-03, T-05-05, T-05-06 | E2E verifier exits 0 against running stack; operator triage of any failures | E2E (live stack) | `bash scripts/verify_phase_05.sh` (requires `docker compose up -d`) | yes (after stack up) | ⬜ pending (human checkpoint) |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Coverage rule:** every REQ-ID claimed by any plan in this phase has at least
one row above with a non-empty `Automated Command`. Verified — all four:
- REQ-frontend-route-set: covered by 05-01-T4, 05-02-T1/T3, 05-03-T1/T3, 05-04-T1, 05-05-T2/T4
- REQ-frontend-data-via-http: covered by 05-01-T1/T2/T3/T4, 05-02-T1/T3, 05-03-T1/T3, 05-05-T2/T4
- REQ-api-byte-parity: covered by 05-02-T3 (export anchors), 05-05-T2/T4 (verifier section O)
- REQ-eliminate-template-drift: covered by 05-02-T2/T3, 05-03-T2/T3, 05-04-T1, 05-05-T1/T2

---

## Wave 0 Stubs (declared in Plan 05-01)

All Wave 0 stubs are tasks within Plan 05-01:

- [x] **05-01-T1** creates `tests/fixtures/headlines_table.json`, `about_singapore_law_table.json`, `headlines_row.json`, `judgments_row.json` + extends `tests/conftest.py` with 4 new fixture functions
- [x] **05-01-T2** creates `tests/test_urls.py` (>= 25 unit tests covering 9 helpers)
- [x] **05-01-T3** creates `tests/test_datasette_client_table_row.py` (>= 12 unit tests covering fetch_table + fetch_row)
- [x] **05-01-T4** creates `routes_table.py` + `routes_row.py` stubs with hidden-table guard active (replaced in 05-02 + 05-03 with full handlers)

Plans 05-02 + 05-03 each declare their own integration test file (`test_routes_table.py`, `test_routes_row.py`) — those run AFTER Wave 0 because they require the Wave 0 fixtures + stub routers.

Plan 05-05 Task 2 creates `scripts/verify_phase_05.sh` — Wave 3 (depends on the actual templates + handlers shipped by 05-02/05-03).

*pytest framework already installed in Phase 4 — no install task needed.*

---

## Test Pyramid (summary; see RESEARCH.md `## Validation Architecture` for full detail)

**Layer 1 — Unit (fastest, deterministic, no IO):**
- `urls.py` querystring helpers — 25+ tests (Plan 05-01-T2)
- `datasette_client.fetch_table` and `fetch_row` — 12+ tests (Plan 05-01-T3)
- Total: ~37+ unit tests

**Layer 2 — Integration (ASGI-level, real router, mocked datasette):**
- `tests/test_routes_table.py` — 18+ tests covering feed mode, tabular fallback, facet sidebar, applied chip, search chip, pagination relative href, export anchors direct, Cache-Control, italic H1, 3 hidden-table 404s, unknown table 404, FTS no-results, rowid PK fallback, 503 on httpx error, breadcrumb (Plan 05-02-T3)
- `tests/test_routes_row.py` — 15+ tests covering article/judgment/longform/tabular row modes, long-text <details>, Cache-Control, italic H1, 3-segment breadcrumb, hidden 404s, unknown row 404, 503 on httpx error, export JSON anchor, rowid-only fallback (Plan 05-03-T3)
- Total: ~33+ integration tests

**Layer 3 — E2E verifier (`scripts/verify_phase_05.sh`):**
- 14 sections (A-O) covering Phase-4 invariants, feed mode, tabular fallback, facet sidebar, applied chip, pagination, FTS, sort, export-direct, row article + tabular, hidden 404, Phase-6 boundary (8 routes), empty/error paths, API parity (Plan 05-05-T2/T4)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual fidelity to sketch 003-A / 003-B / 004-A | UI-SPEC | Pixel/typography parity needs human eye | After running stack: visit `sglawwatch/headlines`, `Zeeker-Judgements/judgments`, `sglawwatch/about_singapore_law` and corresponding `<pk>` pages; compare against `.claude/skills/sketch-findings-zeeker-datasette/references/*.md` |
| FTS `<mark>` policy | UI-SPEC § FTS search | Datasette 0.65.x doesn't expose `_search_highlight` (RESEARCH pitfall #3); v1 policy is "skip highlight, document as gap" | Plan 05-02 implements with no `<mark>` rendering; reviewer confirms in 05-DEPLOY-NOTES outcome |
| Drop cap suppression on short bodies | UI-SPEC § row_mode: article | Heuristic-based; visual check | Open an article-mode row with a short body; confirm drop cap renders only when first paragraph is long enough |
| Production deploy ship/no-ship | n/a | operator's call per 05-DEPLOY-NOTES | Plan 05-05 Task 4 — human checkpoint |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or a Wave 0 dependency that creates one
- [x] Sampling continuity: no 3 consecutive tasks in any plan without an automated verify
- [x] Wave 0 covers all MISSING references in the verification map
- [x] No watch-mode flags in any test command
- [x] Feedback latency < 30s on the quick-run command
- [x] `verify_phase_05.sh` is added to `scripts/` and runs in the verifier-script section
- [x] `nyquist_compliant: true` set in frontmatter once map is fully populated

**Approval:** planner sign-off 2026-04-25; executor consumes per-task map.
