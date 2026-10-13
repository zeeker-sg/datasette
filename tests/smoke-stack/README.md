# Smoke stack — production-shaped disposable gate

A disposable, production-shaped stack (datasette + frontend + caddy) and an
end-to-end checker that together form the **dependency-change gate** for this
repo. Spun up from real images on a loopback port, run, torn down. Never
touches production data, containers, or credentials.

## Purpose

Rule going forward: **no further Datasette dependency changes and no
production rollout without this smoke run green, on identical checks, for
baseline (deployed) and candidate images.**

Two runs constitute a gate pass:

```
# baseline (currently deployed pins) — this MUST be green
tests/smoke-stack/run_smoke_stack.sh \
  ghcr.io/zeeker-sg/zeeker-datasette:sha-b2c15805bb43cd44c52f1ab853843b4e6a3236ca \
  ghcr.io/zeeker-sg/zeeker-frontend:sha-b2c15805bb43cd44c52f1ab853843b4e6a3236ca

# candidate (the change under test) — must be green on the SAME checks
tests/smoke-stack/run_smoke_stack.sh <candidate-datasette-image> <candidate-frontend-image>
```

Exit 0 = gate green. Exit 1 = a check failed — do not roll that dependency
change forward. The checks are the product-shaped contract: routing through
caddy, frontend pages, datasette data API, search-all, strip_columns,
cache_headers, edge lockdown, owner bypass.

## What lives here

| File | Role |
|---|---|
| `docker-compose.smoke.yml` | Production-shaped override: separate compose project (`-p smoke-stack`), own network + project-scoped volumes, loopback-only port, temp data dir, blanked S3/AWS env, throwaway owner token, `restart: "no"`, `container_name`/`ports` neutralized so prod and smoke can coexist. |
| `synthetic_fixtures.py` | Builds `news.db` + `laws.db` + metadata override into the smoke data dir: feed-table shape, content-linked FTS5 (bracket-quoted, sqlite-utils style — the form Datasette's FTS detection matches), `SMOKETEST` markers **only** in protected columns. |
| `smoke_checks.py` | The gate checker — see the checked layers below. |
| `run_smoke_stack.sh` | One-shot driver: fixtures → compose up `--wait` (gated on the real healthchecks) → checks → teardown (even on failure). |
| `run_regressions.sh` | Negative control: injects the deliberately broken metadata (protection stripped) and asserts the smoke FAILS with exactly the expected check failures. Must stay green forever. |
| `fixtures/broken-metadata.json` | The deliberate breakage variant for the negative control. |
| `test_smoke_stack.py` | Dockerless unit/integration tests for the tooling (fixtures, metadata contract, regression gate wiring). Docker end-to-end class is opt-in (`SMOKE_STACK_DOCKER=1`) so CI stays green without Docker. |

## Checks performed (smoke_checks.py)

- caddy → datasette routing (`/-/versions.json`), version reported
- caddy catch-all → frontend (`/frontend-test`, `/` HTML rendering)
- frontend → datasette over the internal bridge (`/{db}` pages, boot probes)
- data API: table JSON (200 + shape + **protected columns stripped**), row JSON, staff metadata
- CSV: 403 on protected tables (with .json hint), 200 on clean tables
- cross-DB search (datasette-search-all): `/-/search` lists searchable tables; `?_search=` returns matches with the protected column stripped
- lockdown + headers at the edge: arbitrary `?sql=` 403, FTS-shadow paths 403, `cache_headers` contract (`public, max-age=300, s-maxage=3600` on API paths, `no-store` on `/-/`)
- owner-token bypass returns full rows (the full `ZEEKER_FULL_ACCESS_TOKEN` path) and cache_headers marks it `no-store, private` (via the Authorization-header branch)
- `/status` rendering

## Isolation guarantees

- `docker compose -p smoke-stack` → own project, own network, own project-scoped volumes; teardown `down -v` is prod-project-neutral.
- `container_name: !reset null` on all three services — fixed names released; service-name DNS (`zeeker-datasette`, `frontend`) keeps the root Caddyfile upstreams byte-identical.
- Caddy publishes `127.0.0.1:8891:80` only (host-wide prod ports untouched).
- Data dir is a per-run `mktemp -d`, mounted `./data`-free; **no prod volume mount**. Fixture content is synthetic (`SMOKETEST`, "Smoke test …").
- S3/AWS env blanked — smoke containers cannot reach prod buckets.
- `restart: "no"` so teardown leaves nothing behind; healthcheck-gated `up --wait` guarantees readiness assertions run only when the stack is healthy.

## Known limitations (documented, not hidden)

- The smoke stack does **not** cover S3-based metadata/DB delivery (blanked env, `entrypoint.sh` skips the download when DBs exist). That path stays covered by `scripts/download_from_s3.py`'s unit tests.
- Single caddy entry (loopback :80) — no TLS/HTTP3/Cloudflare-cache layers; those live at the edge in prod and are exercised there by the `cf-cache-status` headers, out of scope for a disposable stack.
- `!reset`/`!override` compose tags require recent compose (verified on Compose v5.6.0); older CLI versions won't parse the override.
- `smoke_checks.py` runs via urllib (no extra deps). It is deliberately independent of pytest so the gate can run standalone in pipelines.

## CI automation (the gate, made automatic and PR-relevant)

`.github/workflows/smoke-gate.yml` runs on **every relevant PR** — dependency
manifests, Dockerfiles, compose, Caddyfiles, `entrypoint.sh`, `metadata.json`,
plugins, frontend source, smoke-stack itself:

- **Smoke (PR) — built PR-head images**: builds this PR's datasette +
  frontend images **from the checked-out PR head** and runs the disposable
  stack + 24 checks against THEM (the actual changed code — green checks on
  fixed baseline images are not regression protection for a PR). Evidence
  artifact `smoke-pr-evidence-<run>`: PR number + head sha, built image IDs,
  in-image datasette version, pre-teardown runtime provenance, full check
  log (90-day retention). Teardown safety net included.
- **Release gate — compose-pin refs, derived expectations**: zero hardcoded
  ids. Image refs are derived from the compose pins in `docker-compose.yml`
  (the intended release), the expected datasette version from the
  `datasette==` pin in `pyproject.toml`; optional digest expectations can be
  passed (observed digests are always recorded, flagged `not-supplied` when
  no expectation exists). Pulls + digest-reads the exact refs, verifies the
  in-image version, then runs the identical smoke stack + negative control
  against those refs. `tests/smoke-stack/release_gate.sh` is reusable
  locally with the same semantics. NOTE the designed behaviour (defer/strict
  modes): on **PRs the gate defers with recorded evidence** when the intended
  release cannot be verified yet (compose pin lags the pyproject pin during
  the normal bump-merge → pin-bump-merge window, or the bumped sha images
  are not published until the bump PR merges); on **master pushes it fails
  hard** — that strict run is the real pre-deployment blocker PRs must not
  circumvent. Explicit refs+version always run full verification, also on
  PRs. Evidence artifact `smoke-release-evidence-<run>`.
- **Master pushes** touching the gate run the release gate too — after a
  compose pin-bump merge it verifies the actually published images against
  the (moved) compose pin + pyproject expectation, no workflow edits needed.
- Making `Smoke (PR)` / `Release gate` **required** checks needs a
  ruleset/branch-protection change — deliberately NOT part of this PR; it is
  a separate approval step.

## Coverage boundary (explicit, and stable)

Covered by the disposable stack: routing, frontend pages, the frontend→
datasette client hop, data API, strip_columns, cache_headers, edge lockdown,
owner bypass, search-all — through a real compose stack, on runner (automatic
per relevant PR) and release-image identities (release gate).

Covered by the negative control: the checker's ability to detect deliberate
content-protection breakage (master pushes + release gate).

**Explicitly NOT covered (documented, not hidden):**
- **S3 bootstrap/download** — smoke env blanks S3/AWS so fixtures mount
  directly; `scripts/download_from_s3.py` has its own unit tests; CI cannot
  safely exercise the real bucket path without credentials this repo
  deliberately does not hold. Bounded future option: a local-only profile
  (moto-based S3 stub container) or an explicit `SMOKE_S3=1` local profile —
  proposed, not implemented.
- **External TLS / Cloudflare edge** — the smoke caddy publishes plain HTTP
  on loopback; TLS termination and CF caching are edge behaviors out of the
  disposable stack's scope. Bounded future options: a self-signed TLS smoke
  profile, or post-deploy header probes (cf-cache-status observations) as a
  monitored ops runbook item — proposed, not implemented.