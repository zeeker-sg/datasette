---
phase: 07-prune-zeeker-datasette
verified: 2026-04-26T16:30:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
---

# Phase 7: Prune zeeker-datasette — Verification Report

**Phase Goal:** Delete UI-coupled plugins and the entire top-level `templates/` and `static/` directories from the Datasette image build context (repository root — the Datasette container is built from `docker-compose.yml` `context: .`). The image becomes data-only: `Dockerfile`, `metadata.json`, `scripts/`, `entrypoint.sh`, and `plugins/{__init__.py,cache_headers.py}` (the surviving non-UI ASGI cache wrapper).

**Verified:** 2026-04-26T16:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria + plan must-haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Repository root has 0 UI plugins under `plugins/` (only `__init__.py` + `cache_headers.py` remain) | VERIFIED | `ls plugins/` → `__init__.py`, `cache_headers.py`, `__pycache__` (cache); explicit checks confirm 6 deleted plugins absent |
| 2 | No top-level `templates/` directory | VERIFIED | `test ! -d templates` exits 0 |
| 3 | No top-level `static/` directory | VERIFIED | `test ! -d static` exits 0 |
| 4 | Frontend `packages/zeeker-frontend/.../{templates,static}/` intact (over-deletion guard) | VERIFIED | Both directories present on disk |
| 5 | Datasette image rebuilds clean (data-only): `Dockerfile`, `metadata.json`, `scripts/`, `entrypoint.sh`, surviving plugins | VERIFIED | Dockerfile narrowed (whitelisted COPY of 2 plugin files; no `COPY templates/`/`COPY static/`); production deploy `d2dfdee` confirms clean rebuild |
| 6 | All HTML routes still render correctly (frontend owns them now) | VERIFIED | Live smoke against `https://data.zeeker.sg`: `/`, `/developers`, `/sources`, `/status`, `/about`, `/how-to-use`, `/search`, `/sql` all 200 |
| 7 | All API routes return identical bytes (REQ-api-byte-parity) | VERIFIED | `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_07.sh` Section G: `verify_api_parity.sh exit 0 against phase-07-pre` |
| 8 | D-01 boundary preserved: `/-/search`, `/-/sql`, `/-/metadata.json`, `/-/plugins.json` reach datasette via Caddy | VERIFIED | Live: `/-/search` → 200, `/-/sql` → 404 (datasette), `/-/metadata.json` → 200, `/-/plugins.json` → 200, `/-/versions.json` → 200 |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `plugins/__init__.py` | Empty package marker | VERIFIED | Present, byte-identical to pre-phase-7-prune |
| `plugins/cache_headers.py` | 75-line ASGI cache wrapper | VERIFIED | Present (74 lines), preserved verbatim |
| `metadata.json` | 11 top-level keys; no `extra_*_urls`; menu_links length=5 | VERIFIED | `extra_css_urls=False`, `extra_js_urls=False`, `menu_links=5` (live + on-disk) |
| `scripts/verify_phase_07.sh` | Phase-7 verifier with 8 sections (A-H) | VERIFIED | Exists, executable, exits 0 against prod |
| `scripts/download_from_s3.py` | Data-only sync; no UI overlay download | VERIFIED | 8 occurrences of `Phase-7 prune` comment trail; `_download_base_assets` has 0 UI-overlay download calls |
| `.planning/phases/07-prune-zeeker-datasette/07-DEPLOY.md` | Production runbook with rollback chain | VERIFIED | Present, 15KB, references `pre-phase-7-prune` tag |
| `.planning/baselines/phase-07-pre/` | 13+ JSON baselines + sidecar URLs | VERIFIED | 13 `.json` + 13 `.url` files + README.md captured |
| `Dockerfile` | Whitelisted COPY of 2 plugin files; no templates/static COPY | VERIFIED | `COPY plugins/__init__.py`, `COPY plugins/cache_headers.py` only; no `COPY templates/` or `COPY static/` |
| `entrypoint.sh` | Boots clean against pruned image | VERIFIED | `--template-dir`/`--static` flags removed (Datasette 0.65.2 boot-tolerance correction documented in plan); production deploy boots `Up (healthy)` |
| `git tag pre-phase-7-prune` | Annotated rollback anchor at pre-deletion commit | VERIFIED | Resolves to commit `8ddaf95 docs(07-prune-zeeker-datasette): create phase plan` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| Frontend `base.html` | `metadata.menu_links` (5 items) | `fetch_site_metadata` + Jinja loop | WIRED | Live `/-/metadata.json` returns 5 menu_links; nav renders on prod |
| `entrypoint.sh` | `scripts/download_from_s3.py` | `uv run /app/scripts/download_from_s3.py` | WIRED | entrypoint.sh line 7 invokes script when `S3_BUCKET` set |
| `scripts/download_from_s3.py` `_download_database_files` | S3 `latest/*.db` | boto3 `download_file` | WIRED | Method body byte-identical to pre-edit per SUMMARY threat T-07-03-01 mitigation |
| Verifier cascade `phase-07-pre` | Baseline directory | shell `for cand in ...` loop | WIRED | All 3 verifier scripts (`verify_phase_03/04/06.sh`) prepend `phase-07-pre` |
| `verify_phase_07.sh` | `verify_phase_06.sh` (delegation) | bash invocation gated on `BASE_URL=http://localhost` | WIRED | Conditional delegation present at Section A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase-7 verifier passes against production | `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_07.sh` | `== Phase 7 verifier: PASS ==` | PASS |
| All HTML routes return 200 on prod | curl loop over 8 routes | All 200 | PASS |
| All D-01 datasette routes reachable on prod | curl loop over `/-/*` | 4 of 5 → 200, `/-/sql` → 404 (datasette HTML, expected) | PASS |
| API byte-parity preserved | verify_api_parity.sh against phase-07-pre | exit 0 | PASS |
| Frontend pytest suite | `uv run pytest -q` in packages/zeeker-frontend | 165 passed in 0.18s | PASS |
| metadata.json shape on disk | `python3 -c "import json; ..."` | 11 keys, no extra_*_urls, menu_links=5 | PASS |
| Production `/-/plugins.json` excludes UI plugins | `curl /-/plugins.json` | None of {developers_page, status_page, sources_page, string_manager, template_filters} present | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REQ-api-byte-parity | 07-01, 07-02, 07-03, 07-04, 07-05 | API byte-parity preserved across prune | SATISFIED | verify_api_parity.sh exits 0 against phase-07-pre on both local + prod (Section G) |
| REQ-eliminate-template-drift | 07-03, 07-04, 07-05 | Single HTML codebase; no template duplication between datasette image and frontend | SATISFIED | Top-level templates/ deleted; download_from_s3.py no longer redownloads templates |
| REQ-frontend-route-set | 07-02, 07-05 | Frontend covers all routes; menu_links present | SATISFIED | All 8 frontend HTML routes return 200; menu_links length=5 on prod |
| REQ-internal-only-datasette-exposure | 07-01, 07-05 | Network isolation; D-01 boundary intact | SATISFIED | `/-/search`, `/-/sql`, etc. reachable via Caddy only; D-01 routes return 200/404 from Datasette |
| REQ-escape-datasette-template-surface | 07-04, 07-05 | No more Datasette template overrides | SATISFIED | No `templates/`, no `static/` at repo root; matches REQ acceptance criteria |
| REQ-reduce-plugin-count | 07-04, 07-05 | Drop UI-coupled plugins | SATISFIED | 5 UI plugins deleted; `/-/plugins.json` confirms zero UI plugins (only `__init__.py`, `cache_headers.py`, `datasette-search-all`, `datasette-template-sql`, `datasette-matomo` artifacts) |

Note: The project's REQUIREMENTS.md uses prose `### REQ-...` headings (not GSD-canonical checkbox tables). Completion is tracked via plan SUMMARY frontmatter `requirements-completed:` field and STATE.md narrative entries — confirmed in 07-05-SUMMARY.md frontmatter listing all 6 REQ IDs.

REQ-escape-datasette-template-surface acceptance criteria text references `packages/zeeker-datasette/` (the wrong path — Plan 07-01 fixed ROADMAP.md but did NOT amend REQUIREMENTS.md). The intent — "no `templates/` and no `static/` directory in Datasette image build context" — is satisfied by the actual repo-root deletion.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none — no anti-patterns detected in deletion-target files; all 6 files removed cleanly) | - | - | - | - |

Pre-existing issues (not regressions; logged in deferred-items.md):
- Root pytest collection failures (`ModuleNotFoundError: No module named 'scripts'`) in `tests/test_download_from_s3.py` + `tests/test_manage.py` — verified by the plan execution as pre-existing.
- `tests/test_cache_headers.py` async tests fail due to missing pytest-asyncio config — pre-existing.
- Production `/-/plugins.json` still surfaces `datasette-matomo` despite operator's pre-Phase-7 decom commit `d61a987` — Phase-8 scope per SUMMARY.

### Observed but not blocking

- The git tag `pre-phase-7-prune` resolves to commit `8ddaf95` (annotated tag SHA differs at `5444cb0d` — that is the tag object, not the commit). SUMMARY's "Self-Check" cites commit `8ddaf95` correctly. Rollback contract intact.
- Production smoke against `data.zeeker.sg` returned all expected status codes and the verifier output matches what 07-05-SUMMARY.md claims line-for-line.

### Human Verification Required

(none — all verification completed programmatically against live production)

### Gaps Summary

No gaps. Phase 7 goal achieved end-to-end:

1. **Image is data-only** — `plugins/` contains exactly `__init__.py` + `cache_headers.py`; top-level `templates/` and `static/` deleted; `Dockerfile` whitelisted to 2 plugin files; `metadata.json` 11 keys; `scripts/download_from_s3.py` reduced to data-only sync; `entrypoint.sh` boots clean (with the planned fallback edit dropping `--template-dir` / `--static` flags applied).
2. **HTML routes render correctly** — All 8 frontend HTML routes (home + 5 aux + /search + /sql) return 200 on `https://data.zeeker.sg`.
3. **API byte-parity holds** — `verify_api_parity.sh` exits 0 against `.planning/baselines/phase-07-pre/` on both local and production runs (Section G of `verify_phase_07.sh`).
4. **D-01 boundary intact** — `/-/search`, `/-/sql`, `/-/metadata.json`, `/-/plugins.json`, `/-/versions.json` all reach Datasette via Caddy.
5. **Frontend regression gate green** — `uv run pytest -q` returns `165 passed in 0.18s` (matches Phase-6 baseline).
6. **All 6 requirements satisfied** — REQ-api-byte-parity, REQ-eliminate-template-drift, REQ-frontend-route-set, REQ-internal-only-datasette-exposure, REQ-escape-datasette-template-surface, REQ-reduce-plugin-count.

PR #8 (`d2dfdee`) merged at 2026-04-26T15:09:30Z; production deploy executed; SHIPPED status correctly reflected in ROADMAP.md, STATE.md (frontmatter `completed_phases: 5`, `completed_plans: 30`, `percent: 97`), and the per-plan SUMMARY files.

---

*Verified: 2026-04-26T16:30:00Z*
*Verifier: Claude (gsd-verifier)*
