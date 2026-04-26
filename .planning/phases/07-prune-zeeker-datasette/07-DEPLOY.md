# Phase 7 — Production deploy runbook

**Status:** authored by Plan 07-05 before the deploy runs.
**Phase scope:** prune zeeker-datasette image — drop UI plugins, top-level
`templates/`+`static/`, narrow Dockerfile, sever runtime S3 re-overlay.
**Rollback anchor:** `pre-phase-7-prune` annotated tag at commit `8ddaf95`
(set by Plan 07-01).
**Production smoke target:** `data.zeeker.sg`.
**Closes-on-ship:** Phase-6 `data.zeeker.sg` production-smoke UAT item
(transitively, since Phase 7 deploy lands the new pruned image alongside
Phase-6 frontend code on production for the first time).

---

## Section 1 — Pre-flight checks (operator runs locally before deploy)

All four checks must exit 0 before proceeding to Section 2. If any fails,
STOP — do NOT deploy.

```bash
# 1.1 — Phase 7 verifier exits 0 against localhost
docker compose up -d --build zeeker-datasette
bash scripts/verify_phase_07.sh
# Expected final line: == Phase 7 verifier: PASS ==
# (Sections A-H all OK; A delegates to verify_phase_06.sh which delegates
# to verify_phase_04.sh which delegates to verify_phase_03.sh — full chain.)

# 1.2 — Frontend pytest suite exits 0
cd packages/zeeker-frontend && uv run pytest -q
# Expected tail line: 165 passed in <time>s
cd ../..

# 1.3 — Phase-7 commits in expected order vs rollback tag
git log --oneline pre-phase-7-prune..HEAD
# Expected: ~10-15 commits covering Plans 07-01..07-05 (verify scope below).

# 1.4 — Production compose file resolves cleanly (no merge errors)
docker compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null
echo "exit=$?"
# Expected: exit=0
```

If 1.3 surfaces unexpected commits outside the planned surface (see the
diff inventory in Section 2 below), investigate before deploying.

---

## Section 2 — Deploy invocation (the actual ship)

Run on the production host:

```bash
# 2.1 — Sync the deploy commit to the prod host
ssh <prod-host>
cd /path/to/zeeker-datasette
git fetch origin
git checkout master
git pull

# 2.2 — Snapshot the current image tag for rapid rollback (Layer-1 below)
docker image tag zeeker-datasette-zeeker-datasette:latest \
                 zeeker-datasette-zeeker-datasette:pre-phase-7-prune || true

# 2.3 — Rebuild + redeploy (this is the load-bearing line)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 2.4 — Wait for healthchecks
sleep 30
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Expected: zeeker-datasette + frontend + caddy all "Up (healthy)".
# zeeker-datasette healthcheck has start_period: 60s (S3 download phase).

# 2.5 — Initial smoke against production
curl -fsS https://data.zeeker.sg/-/versions.json | jq '.datasette.version'
# Expected: "0.65.2"
```

If 2.4 reports any service `Restarting` or `Unhealthy`, STOP and consult
Section 5 (Rollback). Do NOT proceed to Section 3 until all three services
are healthy.

---

## Section 3 — Production smoke against `data.zeeker.sg`

Run from the dev machine (operator). Each subsection MUST pass before
declaring the deploy successful.

### 3.1 — Verifier pass against production URL

```bash
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_07.sh 2>&1 | tee /tmp/p07-prod-smoke.log
# Expected final line: == Phase 7 verifier: PASS ==
```

When `BASE_URL=https://data.zeeker.sg`, Section A of `verify_phase_07.sh`
skips the `verify_phase_06.sh` delegation (the "skipping ... for non-local
BASE_URL" branch — the delegation chain inspects `docker compose ps` which
doesn't apply remotely). Section G (byte-parity vs `phase-07-pre/` baseline)
is the binding contract for production parity.

### 3.2 — Frontend HTML routes (manual or scripted)

Each must return `HTTP 200` with `<link rel="stylesheet"` pointing at the
frontend CSS bundle (NOT a datasette template fallthrough):

```bash
for path in / \
            /sglawwatch \
            /sglawwatch/headlines \
            /Zeeker-Judgements \
            /Zeeker-Judgements/judgments \
            /sg-gov-newsrooms ; do
  CODE=$(curl -s -o /tmp/p07-html-body -w '%{http_code}' "https://data.zeeker.sg${path}")
  if [ "$CODE" = "200" ] && grep -q '<link rel="stylesheet"' /tmp/p07-html-body; then
    echo "OK    $path"
  else
    echo "FAIL  $path  (code=$CODE, has-stylesheet=$(grep -c '<link rel=\"stylesheet\"' /tmp/p07-html-body))"
  fi
done
```

### 3.3 — Aux routes (Phase-6 ports — also closes Phase-6 UAT)

Each must return `HTTP 200` with the italic-accent H1 fingerprint
(`<h1>...<em>...</em>...</h1>`) — proves the FastAPI/Jinja frontend is
serving aux pages, not a datasette HTML fallthrough:

```bash
for path in /developers /sources /status /about /how-to-use /search /sql ; do
  CODE=$(curl -s -o /tmp/p07-aux-body -w '%{http_code}' "https://data.zeeker.sg${path}")
  echo "$path → $CODE"
done
# Expected: 200 for all 7 routes.
```

### 3.4 — D-01 datasette routes (boundary intact)

Each must return `HTTP 200` AND show the Datasette-bundled fingerprint
(`Powered by Datasette` in body) — proves the D-01 boundary is preserved:

```bash
for path in /-/search?q=test \
            /-/sql \
            /-/versions.json \
            /-/metadata.json \
            /-/plugins.json ; do
  CODE=$(curl -s -o /tmp/p07-ds-body -w '%{http_code}' "https://data.zeeker.sg${path}")
  echo "$path → $CODE"
done
# Expected: 200 (or 404 for /-/sql with no query) — all reach datasette via Caddy.
```

### 3.5 — API parity sentinel

The verifier's Section G (run in 3.1) covers this transitively. Optional
manual spot-check:

```bash
curl -fsS 'https://data.zeeker.sg/sglawwatch/headlines.json?_size=1' \
  | jq 'walk(if type=="object" then del(.query_ms,.__time__,.request_duration_ms) else . end)' \
  > /tmp/p07-prod-headlines.json
diff /tmp/p07-prod-headlines.json \
     .planning/baselines/phase-07-pre/sglawwatch__zeeker_schemas.json__size_10.json \
  || echo "(diff is expected — different table; this is just a smoke fetch)"
```

The verifier's Section G is the load-bearing parity gate. Manual diffs are
optional defense-in-depth.

### 3.6 — Manual browser smoke (visual regression — operator)

Open in a browser:
- `https://data.zeeker.sg/` — home renders with dark editorial nav + cards.
- `https://data.zeeker.sg/developers` — italic-accent H1, dark theme.
- `https://data.zeeker.sg/sglawwatch/headlines` — feed cards layout.
- `https://data.zeeker.sg/-/search?q=test` — datasette HTML (D-01 visual proof).
- `https://data.zeeker.sg/-/sql` — datasette HTML.

Confirm: no 404s in browser console; no "missing static asset" errors; no
visible layout breakage; dark editorial theme on aux pages.

---

## Section 4 — Four-category triage (per Phase 2-3 precedent)

Use this triage to interpret any verifier failures during Section 3. Only
Category D blocks the ship; A/B/C are documented and proceed.

| Category | Definition | Action |
|---|---|---|
| **A — Host base URL drift** | Intentional. `https://data.zeeker.sg` vs local `http://localhost`. Some baseline URLs may report different host in absolute links. | **Proceed.** Document in SUMMARY. |
| **B — Daily import drift** | Intentional. Row counts on `/sglawwatch/headlines.json`, `/Zeeker-Judgements/judgments.json` shift between baseline-capture (~April 26) and deploy day. Same content shape, different counts. | **Proceed.** Document the row-count delta in SUMMARY. |
| **C — Datasette version drift** | Intentional ONLY if a tracked Datasette release upgrade is part of this deploy. Otherwise unexpected. Verify `/-/versions.json` `.datasette.version` == `0.65.2` (matches `phase-07-pre/-_versions.json.json`). | If matches: **proceed**. If unexpected version drift: investigate (NOT Phase-7 scope). |
| **D — True regression** | UI plugin reappears in `/-/plugins.json`; `/-/metadata.json` regrows `extra_*_urls`; `/-/search` returns frontend 404 (D-01 broken); aux page returns datasette HTML fallthrough; `/sglawwatch/headlines.json?_size=1` byte-shape changes (not just row count). | **NO-SHIP — ROLLBACK IMMEDIATELY.** Use Section 5 below. |

When triaging, the binding question is: **does the prune appear to have
landed correctly OR is something serving the pre-prune image?** A correct
post-prune deploy serves: 11-key metadata.json, 0 UI plugins, narrowed
plugins/ shape, frontend HTML on aux routes, datasette HTML on `/-/*`.

---

## Section 5 — Rollback procedure (the ship-no-go path)

Three layers, attempt in order. All converge on the `pre-phase-7-prune`
annotated tag (commit SHA `8ddaf95...`) set by Plan 07-01.

### Layer 1 — Compose-level rollback (fastest, ~30s)

If the previous image is still tagged on the host (Section 2 step 2.2 set
this up):

```bash
ssh <prod-host>
cd /path/to/zeeker-datasette

# Stop the just-deployed service
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop zeeker-datasette

# Restore the snapshot image
docker tag zeeker-datasette-zeeker-datasette:pre-phase-7-prune \
           zeeker-datasette-zeeker-datasette:latest

# Bring it back up
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d zeeker-datasette
sleep 30
docker compose ps zeeker-datasette
# Expected: Up (healthy)

# Smoke the rollback
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_06.sh
# Expected: == Phase 6 verifier: PASS == (the chain prior to Phase 7).
```

This restores the pre-deploy image without touching git or rebuilding.
Suitable for hot rollback when the regression is caught within minutes.

### Layer 2 — Image-level rollback (rebuild from pre-prune commit)

If Layer 1 fails (image tag missing or corrupted):

```bash
ssh <prod-host>
cd /path/to/zeeker-datasette

# Check out the pre-prune working tree
git stash --include-untracked  # save any host-side WIP first
git checkout pre-phase-7-prune -- .
# DESTRUCTIVE: this clobbers any local changes to tracked files.
# Verify the working tree:
git status

# Rebuild + redeploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
sleep 30
docker compose ps
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_06.sh
```

After Layer 2, the host's working tree is detached from `master`; restore
with `git checkout master` once a clean revert commit is pushed (Layer 3).

### Layer 3 — Git-level rollback (clean, leaves an audit trail)

Use this when Layer 1 or 2 stabilized prod but you need a clean git state
on master too. From the dev machine:

```bash
# Single revert commit covering Plans 07-02..07-04
# (07-01's verifier rebase is harmless to leave in place — the OR-alt
#  fingerprint absorbs both pre-prune and post-prune eras.)
git revert pre-phase-7-prune..HEAD --no-commit
git commit -m "revert: Phase 7 prune deploy — see SUMMARY for category-D regression"
git push origin master

# On the prod host:
ssh <prod-host>
cd /path/to/zeeker-datasette
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
sleep 30
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_06.sh
```

Layer 3 produces a clean, auditable git history while restoring
production. Preferred for non-emergency rollback once Layer 1 has bought
time.

### Rollback verification

After ANY rollback layer, re-run the Phase-6 verifier (NOT Phase-7) to
confirm production is back at the pre-prune baseline:

```bash
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_06.sh
# Expected: == Phase 6 verifier: PASS ==
```

If the rollback verifier ALSO fails, escalate immediately — production is
in an unknown state.

---

## Section 6 — Post-deploy update sequence (on successful smoke)

After Section 3 reports green and the deploy is declared shipped:

### 6.1 — Update STATE.md

Prepend a Phase 7 SHIPPED narrative section above the existing Phase 6 entry.
Record:
- Local verifier output (`/tmp/p07-final-local.log` final line).
- Production verifier output (`/tmp/p07-prod-smoke.log` final line).
- Browser smoke results (5 named URLs + any visual notes).
- Phase-6 production-smoke UAT item: **RESOLVED** (closed transitively).

### 6.2 — Update ROADMAP.md

Find the Phase 7 section. Append:
```
**Status:** SHIPPED <date>. UI overlay pruned: 5 UI plugins + templates/ + static/ deleted; Dockerfile narrowed; metadata.json cleaned; download_from_s3.py reduced to data-only sync. verify_phase_07.sh PASS locally + against data.zeeker.sg. Phase-6 production-smoke UAT closed transitively. See `.planning/phases/07-prune-zeeker-datasette/07-05-SUMMARY.md`.
```

Tick off each plan list item from `[ ]` to `[x]`.

### 6.3 — Author 07-05-SUMMARY.md

Per the template at `.planning/phases/07-prune-zeeker-datasette/`, with
sections covering: wave/plan structure, verifier outputs, deploy log,
smoke evidence, four-category triage outcome, threat register dispositions
across all 5 plans (T-07-01..05), Phase-6 UAT closure note.

### 6.4 — Atomic commit

Single commit covering 6.1 + 6.2 + 6.3:
```bash
git add .planning/STATE.md .planning/ROADMAP.md \
        .planning/phases/07-prune-zeeker-datasette/07-05-SUMMARY.md
git commit -m "docs(07-05): Phase 7 SHIPPED — verifier PASS local + prod"
git push
```

### 6.5 — Final regression gate (cheap)

After the doc commit, re-run the verifier locally to confirm doc edits
didn't perturb live state:

```bash
bash scripts/verify_phase_07.sh
# Expected: == Phase 7 verifier: PASS ==
```

---

## Appendix A — Diff scope reference (for Section 1.3 audit)

The Phase-7 deploy commit range `pre-phase-7-prune..HEAD` should touch ONLY
these files. Anything outside this surface is a regression candidate:

- `.planning/ROADMAP.md` (07-01 scope rewrite + 07-05 SHIPPED line)
- `scripts/verify_phase_03.sh` (07-01 fingerprint rebase + 07-05 §F.1 fix)
- `metadata.json` (07-02: drop `extra_*_urls`)
- `.planning/baselines/phase-07-pre/` (07-02 capture + 07-05 plugins
  re-capture)
- `scripts/verify_phase_04.sh` (07-02 cascade prepend)
- `scripts/verify_phase_06.sh` (07-02 cascade prepend)
- `scripts/verify_phase_07.sh` (07-05 new file)
- `scripts/download_from_s3.py` (07-03 data-only sync)
- `plugins/` (07-04: 6 deletions; 2 surviving files unchanged)
- `templates/` (07-04: entire dir deleted)
- `static/` (07-04: entire dir deleted)
- `Dockerfile` (07-04: COPY narrowed; mkdir trimmed)
- `entrypoint.sh` (07-04: dropped `--template-dir` + `--static`)
- `tests/conftest.py` + `tests/fixtures.py` (07-04: stale fixture cleanup)
- `.gitignore` (07-02: `docker-compose.no-s3.yml` entry)
- `.planning/phases/07-prune-zeeker-datasette/*` (planning artifacts)
- `.planning/STATE.md` (per-plan SHIPPED narratives)

## Appendix B — Phase-6 UAT closure

Phase-6 SHIPPED 2026-04-26 with one outstanding HUMAN UAT item:
**production smoke against `data.zeeker.sg`**. That item was deferred because
Phase-6 added zero datasette-image changes — the smoke was gated on the next
deploy that hit production. Phase 7 IS that next deploy.

Closing condition: when Section 3.3 (aux routes) + Section 3.4 (D-01) both
report green, the Phase-6 production smoke is implicitly satisfied. The
07-05 SUMMARY records this as closed; STATE.md narrative names it as
RESOLVED transitively by Phase 7.
