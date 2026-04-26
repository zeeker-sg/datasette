---
phase: 07-prune-zeeker-datasette
plan: 02
subsystem: infra
tags: [metadata, datasette, baseline, verifier, caddy, s3-overlay]

# Dependency graph
requires:
  - phase: 07-prune-zeeker-datasette
    provides: phase-07-pre rollback tag (`pre-phase-7-prune`); ROADMAP scope rewritten to repo-root paths; verify_phase_03.sh fallthrough fingerprint rebased to Datasette-bundled string (07-01).
provides:
  - Cleaned `metadata.json` (11 top-level keys; `extra_css_urls` + `extra_js_urls` removed; `menu_links` + `plugins.datasette-search-all` + `databases.*` preserved verbatim)
  - `.planning/baselines/phase-07-pre/` directory (13 endpoints captured through Caddy; 28 git-tracked files: 13 .json + 13 .url + README.md + .gitkeep) — `/-/metadata.json` baseline reflects post-edit shape
  - Three verifier scripts (`verify_phase_03.sh`, `verify_phase_04.sh`, `verify_phase_06.sh`) with `phase-07-pre` prepended to the baseline-cascade arrays so subsequent runs prefer the new baseline; `verify_phase_05.sh` intentionally untouched
  - Documented sequencing constraint between Plan 07-02 and Plan 07-03 (the S3 three-pass overlay sync overwrites the baked-in metadata.json at startup; baseline capture requires a temporary no-S3 stack OR Plan 07-03 to land first)
affects: [07-03, 07-04, 07-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Baseline-after-edit-before-prune: capture the post-edit /-/metadata.json shape into a fresh baseline directory BEFORE the bigger mass-deletion plan ships, so the post-deletion byte-parity diff is clean (no false-positive Category-D drift to triage)"
    - "Cascade-prepend over cascade-replace: prepend the new baseline name to existing for-cand arrays so older checkouts that lack the new directory fall through to the older baselines automatically"
    - "Local-only baseline-capture override: docker-compose override file (gitignored) bypassing the S3 sync at container startup so the baked-in metadata can be served + baselined WITHOUT modifying the shared S3 bucket"

key-files:
  created:
    - .planning/baselines/phase-07-pre/ (28 files — 13 .json baselines + 13 .url sidecars + README.md + .gitkeep)
    - .planning/phases/07-prune-zeeker-datasette/deferred-items.md
  modified:
    - metadata.json
    - scripts/verify_phase_03.sh
    - scripts/verify_phase_04.sh
    - scripts/verify_phase_06.sh
    - .gitignore

key-decisions:
  - "Auto-mode auto-approval of the human-verify checkpoint at Task 2(a) — verified jq triple-check (false/false/5) + 11-key total against the local stack programmatically; no human pause needed"
  - "Local-only no-S3 override (docker-compose.no-s3.yml + /tmp/zeeker-data-snapshot bind-mount) over pushing the new metadata.json to shared S3 — auto-mode rule #5 forbids modifying shared/production systems without explicit user confirmation; the local override achieves the same goal (baseline against post-edit shape) without touching prod"
  - "Cascade prepend (`phase-07-pre phase-06-pre ...`) over replace — preserves backward-compat for older checkouts that haven't pulled the new baseline directory yet; matches the pattern documented in the plan's <verifier_baseline_cascade> block"
  - "Defer pre-existing verify_phase_03.sh §F.1 uppercase-.JSON failure to phase HUMAN-UAT — out of Plan 07-02 scope (frontmatter `files_modified` does not list verify_phase_03.sh §F); logged in deferred-items.md with triage path"

patterns-established:
  - "S3-overlay-bypass compose override: when a plan needs to validate against the baked-in image-content (not the runtime-overlaid content), write a docker-compose.<purpose>.yml that sets `S3_BUCKET=\"\"` + bind-mounts a /data snapshot. Gitignore the file. Drop after the in-script S3 sync is disabled."
  - "Two-step baseline cascade evolution: (a) capture new baseline against post-edit stack; (b) prepend the new directory name to every verifier's `for cand in ...` array. The break-on-first-match-found semantics mean the prepend takes effect automatically once the baseline directory is on disk, with zero impact on older checkouts."

requirements-completed:
  - REQ-api-byte-parity
  - REQ-frontend-route-set

# Metrics
duration: ~10min
completed: 2026-04-26
---

# Phase 07 Plan 02: Wave-1 metadata clean + re-baseline Summary

**`metadata.json` pruned to 11 keys (dropped `extra_css_urls` + `extra_js_urls`; preserved `menu_links` + `plugins.datasette-search-all` + `databases.*` verbatim); fresh `phase-07-pre/` baseline captured through Caddy against the post-edit stack (13 endpoints, 28 tracked files); three verifier scripts (`verify_phase_03/04/06.sh`) prepend `phase-07-pre` to their baseline-cascade arrays so subsequent runs prefer it over `phase-06-pre`.**

## Performance

- **Duration:** ~10 min (619s wall, single-pass — auto-mode)
- **Started:** 2026-04-26T13:15:29Z
- **Completed:** 2026-04-26T13:25:48Z
- **Tasks:** 4 / 4 (Task 1, Task 2(a) auto-approved checkpoint, Task 2(b), Task 3) + 1 housekeeping commit
- **Files modified:** 4 source files + 28 baseline files created + 1 deferred-items log + .gitignore

## Accomplishments

- **`metadata.json` shape pruned.** Top-level keys: 13 → 11. The two array-typed UI-overlay reference keys (`extra_css_urls`, `extra_js_urls` — together holding 5 `/static/...` paths that Plan 07-04 will delete) removed. Every other key preserved verbatim: scalars (title/description/license/license_url/source/source_url/about/about_url), `databases` (named DBs + `*` wildcard with `allow_sql/allow_facet/allow_download` + `_zeeker_*` hidden tables), `plugins.datasette-search-all`, `menu_links` (5-entry array consumed by frontend `base.html` line 18-25). JSON validates clean: `python3 -c "import json; json.load(open('metadata.json'))"` exits 0.

- **`phase-07-pre/` baseline captured against the post-edit stack.** 13 endpoints probed via Caddy on `:80` — `/-/versions.json`, `/-/metadata.json`, `/-/plugins.json`, `/.json`, then per-database `/{db}.json?_size=10` for all 3 DBs (sg-gov-newsrooms, sglawwatch, zeeker-judgements) plus the first 2 tables of each (`_zeeker_schemas`, `_zeeker_updates`). 28 files committed (13 .json baselines + 13 .url sidecars + README.md + .gitkeep). The captured `/-/metadata.json` baseline reflects the post-Task-1 shape: 11 keys, no `extra_*_urls`, `menu_links` length=5.

- **Verifier baseline-cascade prepended in 3 scripts.** Single one-line edit per file:
  - `scripts/verify_phase_03.sh:260` — `for cand in phase-07-pre phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do`
  - `scripts/verify_phase_04.sh:174` — same.
  - `scripts/verify_phase_06.sh:244` — same.
  - `scripts/verify_phase_05.sh` intentionally untouched (verified: `grep "for cand in phase-" scripts/verify_phase_05.sh` returns nothing — that script has no parity wrap).
  All three pass `bash -n`. Smoke run reports `OK verify_api_parity.sh exit 0 against phase-07-pre` in Section K.

## Task Commits

1. **Task 1: Edit `metadata.json` — drop `extra_css_urls` + `extra_js_urls`** — `4c5d41c` (chore)
2. **Task 2(a): Bring local stack up against post-edit metadata.json (checkpoint:human-verify, AUTO-APPROVED)** — no commit; verified via 3-line jq check against `http://localhost/-/metadata.json` → `false / false / 5` after rebuilding container with `docker compose up -d --build` and applying the local-only no-S3 override
3. **Task 2(b): Capture phase-07-pre baseline through Caddy** — `99267d5` (chore)
4. **Task 3: Prepend phase-07-pre to baseline cascade in 3 verifier scripts** — `0ddcaaa` (chore)
5. **Housekeeping (gitignore override + log deferred items)** — `4c5b5c3` (chore)

_Plan metadata commit will follow this SUMMARY._

## Diff: `metadata.json`

```diff
@@ -239,15 +239,6 @@
       "template": "Search across all available data"
     }
   },
-  "extra_css_urls": [
-    "/static/css/vendor/prism.css",
-    "/static/css/zeeker-base.css"
-  ],
-  "extra_js_urls": [
-    "/static/js/vendor/prism-core.min.js",
-    "/static/js/vendor/prism-sql.min.js",
-    "/static/js/zeeker-base.js"
-  ],
   "menu_links": [
```

Result: 9 lines deleted; everything else byte-identical.

## Listing: `.planning/baselines/phase-07-pre/`

```
-_metadata.json.json   -_metadata.json.url
-_plugins.json.json    -_plugins.json.url
-_versions.json.json   -_versions.json.url
.gitkeep
.json.json             .json.url                              # ← /.json (db list)
README.md
sg-gov-newsrooms.json__size_10.json                          + .url
sg-gov-newsrooms__zeeker_schemas.json__size_10.json          + .url
sg-gov-newsrooms__zeeker_updates.json__size_10.json          + .url
sglawwatch.json__size_10.json                                + .url
sglawwatch__zeeker_schemas.json__size_10.json                + .url
sglawwatch__zeeker_updates.json__size_10.json                + .url
zeeker-judgements.json__size_10.json                         + .url
zeeker-judgements__zeeker_schemas.json__size_10.json         + .url
zeeker-judgements__zeeker_updates.json__size_10.json         + .url
```

`-_metadata.json.json` (post-edit baseline) shape:
```
$ jq 'keys' .planning/baselines/phase-07-pre/-_metadata.json.json
[
  "about", "about_url", "databases", "description",
  "license", "license_url", "menu_links", "plugins",
  "source", "source_url", "title"
]
```

11 keys; `has("extra_css_urls")` = `false`; `has("extra_js_urls")` = `false`; `.menu_links | length` = `5`. All Task 2(b) acceptance criteria met.

## Diff: 3 verifier scripts (one-line cascade prepend per file)

```diff
diff --git a/scripts/verify_phase_03.sh b/scripts/verify_phase_03.sh
@@ -257,7 +257,7 @@ fi
 PARITY_DIR=""
-for cand in phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do
+for cand in phase-07-pre phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do

diff --git a/scripts/verify_phase_04.sh b/scripts/verify_phase_04.sh
@@ -171,7 +171,7 @@ fi
   PARITY_DIR=""
-  for cand in phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do
+  for cand in phase-07-pre phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do

diff --git a/scripts/verify_phase_06.sh b/scripts/verify_phase_06.sh
@@ -241,7 +241,7 @@ fi
 BASELINE_DIR=""
-for cand in phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do
+for cand in phase-07-pre phase-06-pre phase-05-pre phase-04-pre phase-03-pre; do
```

3 files changed, 3 insertions, 3 deletions. `bash -n` validates all three.

## Decisions Made

- **Auto-approval of Task 2(a) checkpoint:human-verify** — auto-mode active; the gate's intent is "operator confirms the post-edit metadata is being served". Programmatic verification (3 jq assertions: `has("extra_css_urls")=false`, `has("extra_js_urls")=false`, `menu_links | length == 5`) achieves the same epistemic guarantee without operator presence. Logged: `⚡ Auto-approved Task 2(a)`.
- **Local-only no-S3 override over S3 push** — Plan 07-02 vs 07-03 sequencing: the S3 three-pass overlay sync (`scripts/download_from_s3.py` lines 197-202) overwrites the baked-in metadata.json at container startup, so a plain `docker compose up --build` does NOT serve the post-edit shape. Two routes: (a) push the new metadata.json to shared S3 — affects production, requires explicit user confirmation per auto-mode rule #5; (b) bypass S3 sync locally via a docker-compose override + /data snapshot bind-mount. Chose (b). The override file is gitignored and disposable.
- **Cascade prepend, not replace** — older checkouts that lack `phase-07-pre/` fall through automatically to `phase-06-pre/05-pre/04-pre/03-pre`. Pattern matches Plan 06-06 baseline-cascade work (per Phase-6 SUMMARY).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] S3 three-pass overlay sync overwrites the baked-in metadata.json at container startup; the plan's Task 2(a) "rebuild and verify" loop fails as written**
- **Found during:** Task 2(a) verification. After `docker compose up -d --build zeeker-datasette` (per the plan's `<how-to-verify>` block), `curl http://localhost/-/metadata.json | jq has("extra_css_urls")` returned `true` — i.e., the container was still serving the OLD shape despite the rebuild succeeding and the `/app/metadata.json` file inside the container being the post-edit version BEFORE the entrypoint ran. Diagnosis: `scripts/download_from_s3.py` line 197-202 calls `s3_client.download_file(..., self.metadata_file)` which OVERWRITES `/app/metadata.json` with the S3 copy at every container startup. This is a known concern documented in `07-RESEARCH §third hazard` ("Plan 07-03 will edit `download_from_s3.py` to disable this") but Plan 07-02 ships BEFORE 07-03.
- **Fix:** Created a local-only `docker-compose.no-s3.yml` override that sets `S3_BUCKET=""` (entrypoint.sh skips S3 download when this is empty) AND bind-mounts a `/tmp/zeeker-data-snapshot/` host directory containing the previously-S3-downloaded `.db` files (snapshotted via `docker cp zeeker-datasette:/data/.`) so datasette has data to serve. Recreated container with `docker compose -f docker-compose.yml -f docker-compose.no-s3.yml up -d --force-recreate zeeker-datasette`. Verified post-edit shape served. Captured baseline. Tore down the override and restored normal compose with `docker compose up -d --force-recreate zeeker-datasette` so the local stack is back to its pre-plan state.
- **Files modified:** `docker-compose.no-s3.yml` (new, gitignored, disposable); `.gitignore` (+ entry for the override).
- **Verification:** Post-override `/-/metadata.json` reported `false / false / 5` (Task 2(a) acceptance). Captured baseline `-_metadata.json.json` reports same. Post-restore stack is healthy on standard compose.
- **Committed in:** `4c5b5c3` (.gitignore + deferred-items.md housekeeping commit). The override file itself is intentionally NOT committed.

**2. [Rule 2 — Out-of-scope finding logged for future] verify_phase_03.sh §F.1 uppercase-.JSON case-insensitivity test fails on the live stack**
- **Found during:** Task 3 smoke run (`bash scripts/verify_phase_06.sh`).
- **Issue:** Section F.1 of verify_phase_03.sh asserts that `curl http://localhost/SGLAWWATCH.JSON?_size=1` returns a body matching `datasette-manager\.js|Powered by Datasette|"error"|"ok"|"tables"` — i.e., that Caddy's `path *.json` matcher is case-insensitive. This is incorrect: Caddy path matchers are case-sensitive by default; uppercase `.JSON` falls through to the frontend's HTML 404 page. Pre-existing issue, NOT caused by this plan (Plan 07-01's smoke pass was opt-skipped because the local stack wasn't running).
- **Fix:** Logged to `.planning/phases/07-prune-zeeker-datasette/deferred-items.md` with triage path: either fix Caddy matcher (architectural) or update the verifier assertion to accept a 404 from frontend (minimum-surface). Not fixed in this plan because Plan 07-02's frontmatter `files_modified` does not include verify_phase_03.sh §F.
- **Files modified:** `.planning/phases/07-prune-zeeker-datasette/deferred-items.md` (new file, +28 lines).
- **Verification:** Logged finding for HUMAN-UAT triage.
- **Committed in:** `4c5b5c3` (housekeeping commit).

---

**Total deviations:** 2 auto-fixed (1 blocking workaround, 1 out-of-scope deferred finding)
**Impact on plan:** Deviation #1 is a Plan 07-02 vs 07-03 sequencing concern that was anticipated in 07-RESEARCH §3 but not surfaced in Plan 07-02's `<context>` or `<action>` blocks. The local-only override workaround sidesteps the issue without modifying shared S3. The override is disposable and self-cleaning (drop the file once 07-03 ships). Deviation #2 is pre-existing and out-of-scope; logged for future triage.

## Issues Encountered

- **Caddy live-stack parity verifier fails post-restore** — After tearing down the no-S3 override and restoring the standard stack, `bash scripts/verify_phase_06.sh` Section K still uses the new `phase-07-pre` baseline (Task 3 cascade prepend works correctly), but `verify_api_parity.sh` reports a metadata diff because the live stack is now serving the S3-sourced `metadata.json` (with `extra_css_urls` etc.) while the baseline reflects the post-edit shape. This is the **expected sequencing constraint** documented in 07-RESEARCH §third hazard: until Plan 07-03 disables the S3 sync in `download_from_s3.py`, the live stack will keep serving the S3 copy. Resolution: Plan 07-03 ships, S3 sync disabled, live stack serves the baked-in post-edit metadata.json, parity check passes against `phase-07-pre/-_metadata.json.json`. Until then, the parity verifier is expected to FAIL on the metadata file specifically; this is Category-D-but-known and documented.

## Threat Register Dispositions (T-07-02-01..05)

- **T-07-02-01 (Tampering — `menu_links` accidentally dropped):** Mitigated. Acceptance criterion explicitly asserts `len(data['menu_links']) == 5`; Task 2(a) jq triple-check (`menu_links | length == 5`) verified against running stack BEFORE baseline capture; baseline file `-_metadata.json.json` itself jq-checks `menu_links | length == 5`. Frontend `base.html` will render the 5-entry nav once Plan 07-03 ships and the overlaid metadata stops overriding.
- **T-07-02-02 (Repudiation — baseline captured against stale image):** Mitigated. Task 2(a) checkpoint (auto-approved with programmatic verification: `has("extra_css_urls")=false` against `http://localhost/-/metadata.json`) confirmed the post-edit shape was being served BEFORE Task 2(b) ran the capture. The baseline file itself has `has("extra_css_urls") | not` jq-asserted. The no-S3 override forced the baked-in (post-edit) metadata to be served instead of the S3 copy.
- **T-07-02-03 (Tampering HIGH — `extra_*_urls` removal accidentally drops a non-UI plugin's stylesheet):** Mitigated. Both arrays exclusively contain `/static/...` paths (verified line-by-line); no plugin-injected URLs present.
- **T-07-02-04 (DoS — malformed JSON breaks Datasette boot):** Mitigated. `python3 -c "import json; json.load(open('metadata.json'))"` exits 0; rebuild + restart succeeded; container reports `healthy`.
- **T-07-02-05 (Info-disclosure — baseline directory commits sensitive data):** Accepted. Captured JSON contains only public API responses already served by `data.zeeker.sg`; same content category as `phase-06-pre/` baselines already committed; no secrets exposed.

## Threat Flags

None — this plan only edits `metadata.json` (UI-overlay reference cleanup), captures public-API JSON baselines, and updates verifier-script cascade arrays. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## User Setup Required

None — no external service configuration required. The temporary `docker-compose.no-s3.yml` override used for baseline capture is local-only, gitignored, and self-cleaning (drop the file once Plan 07-03 ships).

## Next Phase Readiness

- **Plan 07-03 (Wave-1 `download_from_s3.py` edit) — Ready and now MORE CRITICAL than research originally framed.** Until 07-03 disables the in-script S3 sync, the live stack will continue to serve the S3-overlaid `metadata.json` (with `extra_css_urls` etc.), and `verify_api_parity.sh` Section K will report a metadata diff against the new `phase-07-pre/-_metadata.json.json` baseline. Plan 07-03 is the gate that makes Plan 07-02's baseline meaningful at runtime.
- **Plan 07-04 (Wave-2 mass deletion) — Still ready.** The deletion targets (`/static/css/vendor/prism.css`, `/static/css/zeeker-base.css`, three `/static/js/...` paths) are no longer referenced from `metadata.json`, so deleting them no longer creates dangling references in `/-/metadata.json` body.
- **Plan 07-05 (deploy) — Ready.** The four-category triage at the deploy checkpoint (Categories A/B/C/D) will distinguish the expected metadata diff (Category-D-but-known until 07-03 ships) from genuine regressions.
- **Deferred for HUMAN-UAT:** verify_phase_03.sh §F.1 uppercase-.JSON case-insensitivity assertion (see `deferred-items.md`).

## Self-Check: PASSED

- File `metadata.json` exists and was modified — `git log --oneline -1 metadata.json` shows `4c5d41c`.
- File `.planning/baselines/phase-07-pre/-_metadata.json.json` exists — verified via `test -f` + jq parse.
- Files `scripts/verify_phase_03.sh`, `verify_phase_04.sh`, `verify_phase_06.sh` exist and were modified — `git log --oneline -1` shows `0ddcaaa`.
- File `.planning/phases/07-prune-zeeker-datasette/deferred-items.md` exists.
- Commit `4c5d41c` exists — verified via `git log --oneline | grep 4c5d41c`.
- Commit `99267d5` exists — `git ls-files .planning/baselines/phase-07-pre/ | wc -l` returns 28.
- Commit `0ddcaaa` exists — `grep -c 'phase-07-pre phase-06-pre phase-05-pre phase-04-pre phase-03-pre' scripts/verify_phase_*.sh` returns 3 matched files.
- Commit `4c5b5c3` exists — verified.
- `verify_phase_05.sh` UNTOUCHED — `git status scripts/verify_phase_05.sh` returns no modification (verified before any commits).

---
*Phase: 07-prune-zeeker-datasette*
*Completed: 2026-04-26*
