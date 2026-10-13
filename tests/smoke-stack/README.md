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

## Future work candidates

- Wire the gate into CI as a job on dependency-affecting PRs (needs GitHub-hosted runners with compose + a free port; not yet configured per user's scope — a separately reviewable follow-up).
- Extend fixtures with a second protected table + FTS shadow variants for wider negative coverage.
- A CI-anchored negative control run (`run_regressions.sh`) on every smoke-gate change, so the checker itself can't rot.