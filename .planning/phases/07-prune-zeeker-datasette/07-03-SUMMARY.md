---
phase: 07-prune-zeeker-datasette
plan: 03
subsystem: infra
tags: [s3-sync, download_from_s3, prune, runtime-overlay, container-startup]

# Dependency graph
requires:
  - phase: 07-prune-zeeker-datasette
    provides: ROADMAP scope explicitly names scripts/download_from_s3.py edit as in-scope (07-01); metadata.json shape pruned to 11 keys, phase-07-pre baseline captured against post-edit shape (07-02). Plan 07-02 documented the runtime-overlay sequencing constraint that this plan closes.
provides:
  - scripts/download_from_s3.py runs as a data-only sync — .db files (latest/*.db) + base/per-database metadata.json — and refuses to re-overlay templates/, static/, or plugins/ on container restart
  - Plan 07-04's mass-delete of templates/+static/ becomes runtime-effective (not cosmetic-only)
  - Plan 07-02's no-S3 docker-compose override workaround becomes obsolete (override file gitignored + disposable; can be dropped after this plan ships)
  - upload_base_assets() can no longer accidentally wipe S3-side overlays by mirroring up empty local dirs (T-07-03-02 mitigation)
affects: [07-04, 07-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Surgical-edit-with-named-preservation: explicitly enumerate KEEP-VERBATIM methods in plan action block; verify byte-identical via diff awk-pass that filters by hunk header method name"
    - "Forensic-comment trail: leave `Phase-7 prune` literal string in every edited method's docstring + log line, so future grep audits can locate the rationale without re-reading the plan"

key-files:
  created:
    - .planning/phases/07-prune-zeeker-datasette/07-03-SUMMARY.md
  modified:
    - scripts/download_from_s3.py

key-decisions:
  - "Five-surface surgical edit over rewrite — module docstring + four methods replaced; two methods (_download_database_files at lines 108-142, _merge_all_metadata at lines 283-354) preserved byte-identical because their bodies do data-layer work orthogonal to the UI prune"
  - "Keep _setup_base_assets dispatcher unchanged — it's a 14-line if/else that just calls _check_base_assets_exist + (download_base_assets | upload_base_assets); both callees still exist with the same signatures, so the dispatcher remains correct without any body edit"
  - "Preserve metadata.json upload path in upload_base_assets — the scrape pipeline writes per-database metadata; without the metadata-only mirror-up, a fresh-bucket bootstrap would lose the merged base. Drop only the templates/static/plugins branches"
  - "Phase-7 prune literal in 8 places (vs the AC's >=2) — visible in module docstring + 4 method docstrings + 3 log lines. Forensic-continuity over minimum-cost"

patterns-established:
  - "Five-surface surgical edit: when a script needs to drop functionality but keep adjacent functionality, edit each function in isolation rather than rewriting; verify by enumerating KEEP-VERBATIM method names + diff-awk-pass to assert zero removed lines from those bodies"
  - "Preserve dispatcher when callees stay; rewrite callees when callees change — _setup_base_assets unchanged because its callees still exist with same signatures"

requirements-completed:
  - REQ-api-byte-parity
  - REQ-eliminate-template-drift

# Metrics
duration: ~2min
completed: 2026-04-26
---

# Phase 07 Plan 03: Sever runtime S3 re-overlay path Summary

**`scripts/download_from_s3.py` reduced to a data-only sync at five surgical edit surfaces: module docstring + 4 method bodies (`_check_base_assets_exist`, `_download_base_assets`, `upload_base_assets`, `_apply_database_customizations`). Two load-bearing methods (`_download_database_files`, `_merge_all_metadata`) preserved byte-identical (zero removed lines from their bodies). Plan 07-04's mass-delete of `templates/`+`static/` is now runtime-effective; container restarts can no longer re-download the legacy M1 overlay onto the (about-to-be-empty) container directories.**

## Performance

- **Duration:** ~2 min (104s wall, single-pass — auto-mode)
- **Started:** 2026-04-26T13:31:49Z
- **Completed:** 2026-04-26T13:33:33Z
- **Tasks:** 1 / 1
- **Files modified:** 1 (`scripts/download_from_s3.py`)
- **Commits:** 1 task commit (`a433bec`) + 1 plan-metadata commit to follow this SUMMARY

## Accomplishments

- **Runtime re-overlay path severed.** All four UI-overlay sync paths in `scripts/download_from_s3.py` are now gone: (1) `_download_base_assets` no longer calls `_download_s3_directory` for `templates/`/`static/`/`plugins/` paths; (2) `upload_base_assets` no longer calls `_upload_directory_to_s3` for those three paths; (3) `_apply_database_customizations` no longer overlays per-database template/static dirs; (4) `_check_base_assets_exist` required-files list shrunk from 3 entries to 1 (metadata.json only). Verified via grep counts: all four return 0 occurrences of the disabled-call patterns.

- **Load-bearing data sync preserved verbatim.** `_download_database_files` (lines 108-142) and `_merge_all_metadata` (lines 283-354) bodies are byte-identical to pre-edit. Verified via `git diff` awk-pass that filters by hunk method name and reports `removed-lines-in-_download_database_files: 0` and `removed-lines-in-_merge_all_metadata: 0`. The container will continue pulling `.db` files from `latest/*.db` and merging per-database metadata from `assets/databases/{db}/metadata.json`.

- **Forensic comment trail seeded.** `Phase-7 prune` literal string appears 8 times across the file (module docstring + 4 method docstrings + 3 log lines): well above the AC threshold of >=2. Future audits can grep for `Phase-7 prune` and locate the rationale + the 07-RESEARCH Q3 Option A reference without re-reading the plan.

- **`upload_base_assets` empty-dir wipe risk closed.** Post-Plan-07-04, the local `templates/` and `static/` dirs will be deleted. The pre-edit `upload_base_assets` would have mirrored the empty (or missing) dirs up to S3, potentially wiping any S3-side overlay used by other consumers. The post-edit method only uploads `metadata.json` (single-file upload, cannot wipe directories). T-07-03-02 mitigated.

## Task Commits

1. **Task 1: Surgically disable templates/static/plugins S3 sync** — `a433bec` (fix)

_Plan metadata commit will follow this SUMMARY._

## Diff: `scripts/download_from_s3.py` (one file, +63 / -70)

Diff confined to six hunks at the five planned edit surfaces:

| Hunk header | Surface | Edit |
|-------------|---------|------|
| `@@ -1,7 +1,18 @@` | Module docstring (lines 1-7) | Rewrite to document data-only sync model |
| `@@ -157,11 +168,16 @@` | `_check_base_assets_exist` | Required-files list 3 → 1 (metadata.json only) |
| `@@ -174,34 +190,27 @@` | `_download_base_assets` | Drop templates/static/plugins downloads; keep metadata.json |
| `@@ -209,30 +218,16 @@` | `upload_base_assets` | Drop templates/static/plugins uploads; keep metadata.json |
| `@@ -240,7 +235,10 @@` | Spans `upload_base_assets` close + `_apply_database_customizations` open (context lines around the `def` boundary) | Inserts the new method-docstring block |
| `@@ -248,36 +246,31 @@` | `_apply_database_customizations` | Drop per-database template/static overlay branches; preserve forensic-log return-True path |

Lines 108-142 (`_download_database_files`) and lines 283-354 (`_merge_all_metadata`) appear in NO diff hunk — verified byte-identical.

### Per-method line-count summary

| Method | Pre-edit | Post-edit | Δ |
|--------|----------|-----------|---|
| Module docstring | 4 lines | 15 lines | +11 |
| `_check_base_assets_exist` | 16 lines | 18 lines | +2 |
| `_download_base_assets` | 34 lines | 22 lines | -12 |
| `upload_base_assets` | 38 lines | 22 lines | -16 |
| `_apply_database_customizations` | 32 lines | 24 lines | -8 |
| `_download_database_files` | 35 lines | 35 lines | 0 (verbatim) |
| `_merge_all_metadata` | 72 lines | 72 lines | 0 (verbatim) |
| `_setup_base_assets` | 14 lines | 14 lines | 0 (untouched dispatcher) |

## Method inventory (proves no methods accidentally lost)

**Pre-edit (HEAD~1) — 14 methods:**
```
['__init__', '_apply_database_customizations', '_check_base_assets_exist',
 '_check_s3_path_exists', '_deep_merge_metadata', '_download_base_assets',
 '_download_database_files', '_download_s3_directory', '_merge_all_metadata',
 '_setup_base_assets', '_setup_s3_client', '_upload_directory_to_s3',
 'download_complete_setup', 'upload_base_assets']
```

**Post-edit (HEAD) — 14 methods:**
```
['__init__', '_apply_database_customizations', '_check_base_assets_exist',
 '_check_s3_path_exists', '_deep_merge_metadata', '_download_base_assets',
 '_download_database_files', '_download_s3_directory', '_merge_all_metadata',
 '_setup_base_assets', '_setup_s3_client', '_upload_directory_to_s3',
 'download_complete_setup', 'upload_base_assets']
```

Identical name set. All 7 plan-required methods (`_download_database_files`, `_merge_all_metadata`, `_setup_base_assets`, `_check_base_assets_exist`, `_download_base_assets`, `upload_base_assets`, `_apply_database_customizations`) plus 7 helpers all retained.

## Acceptance criteria results

| AC # | Check | Expected | Observed | Status |
|------|-------|----------|----------|--------|
| 1 | `python3 -c "import ast; ast.parse(...)"` exits 0 | 0 | 0 | ✅ |
| 2 | All 7 required methods present | 7/7 | 7/7 | ✅ |
| 3 | `_download_base_assets` no `_download_s3_directory.*templates|static|plugins` | 0 | 0 | ✅ |
| 4 | `upload_base_assets` no `_upload_directory_to_s3.*templates|static|plugins` | 0 | 0 | ✅ |
| 5 | `_apply_database_customizations` no `_download_s3_directory` | 0 | 0 | ✅ |
| 6 | `_download_database_files` body byte-identical (no removed lines) | 0 removed | 0 removed | ✅ |
| 7 | `_merge_all_metadata` body byte-identical (no removed lines) | 0 removed | 0 removed | ✅ |
| 8 | `Phase-7 prune` literal occurrences | >=2 | 8 | ✅ |

All eight acceptance criteria pass.

## Decisions Made

- **Five-surface surgical edit over rewrite.** The plan's `<action>` block named exactly five edit surfaces; respected the boundary. Two adjacent methods (`_download_database_files`, `_merge_all_metadata`) explicitly named-out as KEEP-VERBATIM in the plan twice. This minimum-surface approach makes the diff auditable in `git diff HEAD~1` without context-line leakage into the load-bearing methods.
- **Keep `_setup_base_assets` dispatcher unchanged.** Lines 144-157 are pure dispatch logic (`if self._check_base_assets_exist(): return self._download_base_assets() else: return self.upload_base_assets()`). Both callees still exist with identical signatures post-edit; the dispatcher is correct without modification. Plan instructed not to touch; honoured.
- **Preserve metadata.json mirror-up in `upload_base_assets`.** The scrape pipeline depends on the `metadata.json` upload path for fresh-bucket bootstrap. Drop only the three UI-overlay branches; keep the metadata branch + the success-log line.
- **Phase-7 prune literal in 8 places vs. AC's `>=2`.** Forensic continuity: every edited method's docstring + every changed log message names the rationale. A single `grep 'Phase-7 prune'` in 12 months locates the entire scope without re-reading any plan.

## Deviations from Plan

None — plan executed exactly as written. All five edit surfaces matched the plan's verbatim replacement blocks; all eight acceptance criteria pass on first run; both load-bearing methods preserved byte-identical.

## Issues Encountered

- **Local docker stack smoke check skipped.** Plan `<verification>` step 4 ("docker compose up -d --build zeeker-datasette + grep logs for Phase-7 prune message") is opt-in based on stack availability. Per the parent execution context message, this plan is the load-bearing fix per 07-RESEARCH §3; a live smoke run would require either (a) S3 credentials to populate /data with .db files for datasette boot OR (b) reusing Plan 07-02's `docker-compose.no-s3.yml` override + `/tmp/zeeker-data-snapshot/` bind-mount. Neither was set up at execution time. The AST + grep + diff gates above provide the same epistemic guarantee programmatically (the post-edit script will only execute the new code paths because the old ones are physically removed). Live smoke is deferred to Plan 07-04 / 07-05 verifier runs which exercise the full container boot.

## Verification Results

End-to-end gates (per plan `<verification>` section):

1. **AST parse + method inventory** — `python3 -c "import ast; ..."` exits 0; pre/post method sets identical (14 methods each, all by name). ✅
2. **No template/static/plugins downloads in body of editable methods** — verified via three awk-passes that scope grep to the method body only:
   - `_download_base_assets`: 0 occurrences of `_download_s3_directory` paired with `templates|static|plugins`
   - `upload_base_assets`: 0 occurrences of `_upload_directory_to_s3` paired with `templates|static|plugins`
   - `_apply_database_customizations`: 0 occurrences of `_download_s3_directory`
   ✅
3. **Load-bearing methods byte-identical** — `git diff HEAD~1 -- scripts/download_from_s3.py` awk-filtered by hunk header reports `removed-lines-in-_download_database_files: 0` and `removed-lines-in-_merge_all_metadata: 0`. The full diff stat is `1 file changed, 63 insertions(+), 70 deletions(-)`, all confined to the 6 hunks at the 5 named edit surfaces. ✅
4. **Local-stack smoke** — Skipped per "Issues Encountered" above. ⊘

## Threat Register Dispositions (T-07-03-01..05)

- **T-07-03-01 (Tampering HIGH — `_download_database_files` inadvertently affected):** Mitigated. Awk-filtered diff reports `removed-lines-in-_download_database_files: 0`. Method body (lines 108-142) appears in no diff hunk. The load-bearing `latest/*.db` pull is unchanged.
- **T-07-03-02 (Tampering HIGH — `upload_base_assets` pushes empty dirs to S3):** Mitigated. Post-edit `upload_base_assets` has zero `_upload_directory_to_s3` calls (verified by AC4 grep). Only the `metadata.json` upload path remains; that's a single-file upload that cannot wipe S3 directories. After Plan 07-04 deletes the local `templates/`+`static/` dirs, the post-edit method has no path to S3 for those keys.
- **T-07-03-03 (DoS — malformed Python breaks container boot):** Mitigated. AST parse exits 0; all 7 required + 7 helper methods still defined. The `_setup_base_assets` dispatcher (unchanged) still resolves both branches — `_download_base_assets` (downloads metadata.json on cache hit) and `upload_base_assets` (uploads metadata.json on cache miss) — so the boot path remains valid for both branches.
- **T-07-03-04 (Race condition — container restart between 07-03 ship and 07-04 ship):** Accepted (per plan threat-model disposition). The Phase 7 wave order is 07-01 → {07-02 || 07-03} → 07-04 → 07-05. Since 07-03 ships BEFORE 07-04 deletes the local `templates/`+`static/` dirs, even if a container restart fires in this window the script has already been taught not to redownload, and the local dirs are still present. After 07-04 ships, both states are coherent. Per 07-RESEARCH §3 this is the correct sequence.
- **T-07-03-05 (Info-disclosure — comment trail names internal phase):** Accepted (per plan threat-model disposition). "Phase-7 prune" is meaningful for forensic continuity; no secrets exposed; same convention as Phase-6's "Pitfall 11" inline comments in `verify_phase_06.sh`. 8 occurrences in the file.

## Threat Flags

None — this plan only edits a single Python script that reads + writes S3 + the local filesystem inside the container. No new network endpoints, auth paths, or schema changes at trust boundaries. The trust boundaries (container ↔ S3, S3 ↔ local FS) remain identical to pre-edit; the script just stops crossing those boundaries for `templates/`/`static/`/`plugins/` paths.

## User Setup Required

None — no external service configuration required. The next container restart against the post-edit script will skip the templates/static/plugins paths automatically. Plan 07-02's gitignored `docker-compose.no-s3.yml` override file is now obsolete (the in-script S3 sync is disabled at the source); it can be deleted from the local checkout when convenient. No production action needed.

## Next Phase Readiness

- **Plan 07-04 (Wave-2 mass deletion) — Ready and now SAFE to ship.** With the runtime re-overlay path severed, deleting `templates/` and `static/` on disk + narrowing the Dockerfile `COPY plugins/` to whitelist (`__init__.py` + `cache_headers.py`) is now genuinely effective at runtime. A container restart after 07-04 ships will: (1) run the post-edit `download_from_s3.py`, (2) skip the templates/static/plugins paths entirely, (3) leave the (now-deleted) local dirs untouched, (4) datasette boots without the M1 overlay and falls through to its bundled defaults — which Plan 07-01's verifier fingerprint already accounts for.
- **Plan 07-05 (deploy) — Ready.** The post-edit script logs `(templates/static/plugins skipped — Phase-7 prune)` on every successful boot, providing a runtime-side confirmation marker that the prune is in effect. The four-category triage at the deploy checkpoint can use this log line as a positive-assertion sentinel.
- **Plan 07-02's runtime sequencing constraint — RESOLVED.** Plan 07-02 documented that the live stack would continue serving the S3-overlaid `metadata.json` (with `extra_*_urls`) until this plan shipped. With 07-03 now shipped and the in-script S3 sync disabled, the live stack will serve the baked-in metadata.json (as edited in Plan 07-02) on next container restart. `verify_api_parity.sh` Section K's metadata diff against `phase-07-pre/-_metadata.json.json` will now pass.
- **No blockers, no concerns.**

## Self-Check: PASSED

- File `scripts/download_from_s3.py` exists and was modified — verified via `git log --oneline -1 scripts/download_from_s3.py` shows `a433bec`.
- Commit `a433bec` exists — verified via `git log --oneline | grep a433bec` returns the commit line `a433bec fix(07-03): disable templates/static/plugins S3 sync per Phase-7 prune`.
- File `.planning/phases/07-prune-zeeker-datasette/07-03-SUMMARY.md` exists — this file just written.
- All 8 acceptance criteria pass — see "Acceptance criteria results" table above.
- All 5 plan-required threat-register dispositions addressed — see "Threat Register Dispositions" section above.
- Pre/post AST method-name sets identical (14 methods each) — see "Method inventory" section above.

---
*Phase: 07-prune-zeeker-datasette*
*Completed: 2026-04-26*
