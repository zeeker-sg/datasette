# Phase 2: Dual-service bring-up — Research

**Researched:** 2026-04-20
**Domain:** Docker Compose multi-service topology; FastAPI scaffolding with uv; Caddy v2 reverse proxy; healthchecks for slim containers; API byte-parity verification
**Confidence:** HIGH (versions verified against PyPI + Docker Hub registries 2026-04-20; Caddy/Compose/FastAPI patterns cross-verified against official docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Frontend service stack** (PRD §7.2 / DEC-3, DEC-5):
- FastAPI + Jinja2 + httpx + uv + black-formatted code
- Frontend reads data exclusively via internal HTTP to `http://datasette:8001/...json`
- **No SQLite client in frontend container. No `./data` volume mount on frontend.**
- This phase: only the placeholder route is needed, but the package skeleton must already enforce no-SQLite discipline.

**Reverse proxy** (PRD §7.3 / DEC-4):
- Caddy — off-the-shelf image, single Caddyfile at repo root
- Phase 2 Caddyfile is the simplest possible: one site block, all traffic → `datasette:8001`. **No suffix matchers yet** — those are Phase 3.
- Caddy publishes `:80` and `:443`; no other service publishes ports.
- TLS auto-provisioned by Caddy from a persistent named volume.

**Datasette service changes (this phase only):**
- Remove `ports:` mapping → datasette becomes internal-only at `datasette:8001`
- Healthcheck remains `GET /-/versions.json` returns 200
- `--cors` flag preserved
- Read-only mode preserved
- **Do NOT delete templates/, static/, or UI plugins** — Phase 7's job

**Frontend package layout** — under `packages/zeeker-frontend/` (the new package; existing flat datasette layout stays put, the rename to `packages/zeeker-datasette/` is Phase 7).

**docker-compose layout (this phase):**
- Three services: `datasette` (existing, ports removed), `frontend` (new, internal-only), `caddy` (new, only public service)
- Default bridge network is fine; explicit `networks:` block not required
- Caddy `depends_on` both backends with `condition: service_healthy`
- Persistent volume for Caddy's `data` and `config` directories
- Frontend healthcheck targets `/frontend-test`

**Verification approach:**
- `docker compose ps` shows all three services healthy
- `curl https://localhost/sglawwatch.json` returns identical JSON to baseline
- `curl https://localhost/frontend-test` returns 404 (Caddy still routes everything to datasette in Phase 2)
- Frontend route is reachable only via `docker compose exec frontend curl http://localhost:8000/frontend-test`

### Claude's Discretion

- Exact Caddyfile syntax — PRD specifies behavior, not literal text
- Choice of Python base image (slim vs alpine vs distroless — preference for `python:3.12-slim`)
- Whether to use Caddy auto-HTTPS in local dev (skip in `docker-compose.yml`; use `docker-compose.prod.yml` overlay)
- Internal port for frontend container (suggest 8000)
- Whether to add a `.dockerignore` for the new package (yes, recommended)

### Deferred Ideas (OUT OF SCOPE — Phase 2 must NOT touch these)

- Suffix-based routing flip (`*.json|*.csv|*.db|/-/* → datasette`, else → frontend) — **Phase 3**
- Real frontend HTML pages — **Phases 4–6**
- Deletion of `templates/`, `static/`, UI plugins — **Phase 7**
- Matomo migration / overlay decision — **Phase 8**
- Restructuring root into `packages/zeeker-datasette/` — **Phase 7**
- TLS auto-provisioning at the real `data.zeeker.sg` domain — production overlay, not local
- Per-database overlay mechanism for the frontend — **Phase 8** (open question per PRD R5)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-incremental-migration | Each phase deployable on its own; site never fully down; un-ported pages fall back to legacy Datasette HTML during transition | Phase 2's Caddyfile is "100% to datasette" → site behavior is byte-identical from the user's perspective. Topology change is independently rollback-able by reverting `docker-compose.yml`. See Architecture Patterns → Pattern 1. |
| REQ-internal-only-datasette-exposure | `docker compose config` shows datasette has no `ports:` mapping; only Caddy exposes ports | Verified by removing the existing `ports: ["127.0.0.1:8001:8001"]` line from the datasette service. See Standard Stack → Compose layout. Verification recipe in Validation Architecture. |
| REQ-frontend-data-via-http | Frontend container has no SQLite client and no volume mount of `./data` | `pyproject.toml` for the frontend MUST NOT include `sqlite3-dev`-requiring deps; `python:3.12-slim` does not include `sqlite3` headers; compose service for frontend has zero volume mounts of `./data`. Verification check in Validation Architecture. |
| REQ-preserve-zeeker-cli | `zeeker init/add/build/deploy` and S3 deployment pipeline continue to work unchanged | Phase 2 only adds two services — does not touch `scripts/download_from_s3.py`, `entrypoint.sh`, `metadata.json`, or any zeeker CLI surface. Verified by inspecting the diff: nothing inside the existing datasette service definition changes except removal of `ports:`. |
| REQ-api-byte-parity | `diff` of `curl -s https://data.zeeker.sg/sglawwatch/headlines.json` pre- and post-migration shows no meaningful changes | Recipe in Validation Architecture → Phase Requirements Test Map. Capture baseline BEFORE removing `ports:`; verify AFTER bring-up that traffic through Caddy yields byte-identical JSON. Datasette version string and timestamps are excepted. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No hardcoded database references** — phase 2 introduces nothing database-specific. Caddyfile and frontend placeholder are generic.
- **Three-pass merge system** — preserved unchanged; datasette continues to download from S3 at startup via `download_from_s3.py`.
- **Self-hosted fonts** in `static/fonts/` — not touched in Phase 2 (those move to frontend in Phases 4–6, not now).
- **`uv` for Python dependency management** — frontend MUST use `uv sync --frozen` like the existing datasette image does.
- **Test framework: pytest** — frontend `pyproject.toml` should add pytest as a dev dep so future phases can extend.
- **`metadata.json` is authoritative data metadata** — preserved; not touched in Phase 2.

## Summary

Phase 2 is a **pure topology change**: introduce two new Docker services (`frontend` placeholder + `caddy` reverse proxy) alongside the existing `datasette` service, and stop exposing datasette directly. From the user's perspective the site MUST be unchanged because Caddy's Phase-2 Caddyfile transparently proxies 100% of traffic to datasette. The routing flip is Phase 3.

The technical risk surface is small but real:
1. **Healthchecks must use the right tool** — the official Caddy Alpine image ships `curl` (verified) but not `wget`; `python:3.12-slim` ships neither `curl` nor `wget` by default, so the frontend healthcheck must either install curl OR use `python -c 'import urllib.request; ...'`. We pick the urllib approach to avoid bloating the slim image.
2. **`depends_on: condition: service_healthy` has a known footgun** — `start_period` does NOT short-circuit early; dependent services wait at least the full `start_period` even if the dependency goes healthy sooner. Datasette's S3 download takes 10–30s per CON-healthcheck; budget `start_period: 60s` to be safe.
3. **Caddy auto-HTTPS at `:80`** — using `:80 { ... }` (port-only site address) tells Caddy to serve plain HTTP and skip cert provisioning. Using a hostname like `localhost` triggers Caddy's internal CA — fine for local TLS, but we prefer `:80` in `docker-compose.yml` and overlay HTTPS in `docker-compose.prod.yml`.
4. **Default Compose bridge network gives DNS-by-service-name for free** — no `networks:` block required; `frontend`, `datasette`, `caddy` resolve each other by service name out of the box.

**Primary recommendation:** Use `python:3.12-slim` + `uv` for the frontend (Dockerfile pattern matches existing datasette image), `caddy:2.11.2-alpine` for the proxy (verified current stable, ~57MB), Python `urllib.request` one-liner for the frontend healthcheck (no extra apt-get needed), the official Caddy Alpine image's bundled `curl` for the Caddy healthcheck (curl IS present in the official Caddy Alpine image — verified from upstream Dockerfile), and the existing datasette healthcheck unchanged except switching the test target from `/` to `/-/versions.json` per CON-healthcheck.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Public TLS termination | Caddy (proxy) | — | Only public service per PRD §7.3; auto-TLS is Caddy's design center |
| URL routing decisions | Caddy (proxy) | — | Phase 2: trivial single-backend; Phase 3: suffix matchers added here |
| Data API (`.json`/`.csv`/`.db`/`/-/*`) | Datasette (backend) | — | DEC-1 says don't re-implement; datasette already owns this surface |
| HTML rendering (future) | Frontend (FastAPI) | — | Phase 2 only stubs `/frontend-test`; HTML pages arrive in Phases 4–6 |
| SQLite reads | Datasette (backend) | — | DEC-5: frontend NEVER touches SQLite directly; only HTTP to datasette |
| S3 database hydration on boot | Datasette (backend) | — | Existing `download_from_s3.py` mechanism — unchanged |
| Service-mesh-style health gating | Compose's `depends_on: service_healthy` | — | No service-mesh; Compose primitive is sufficient at this scale |
| Internal service discovery | Compose default bridge network DNS | — | Service names resolve out of the box on user-defined bridge (which Compose creates by default) |
| Cert/key persistence | Named Docker volume mounted at `/data` and `/config` in Caddy | — | Standard Caddy persistence pattern from official image docs |

## Standard Stack

### Core (frontend service)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi[standard]` | 0.136.0 | Web framework | DEC-3 locked; `[standard]` extra pulls uvicorn + jinja2 + python-multipart automatically (per uv official FastAPI guide) |
| `jinja2` | 3.1.6 | Templating | DEC-3 locked; reuses Datasette template Jinja knowledge. (Pulled transitively by fastapi[standard], but pin explicitly.) |
| `httpx` | 0.28.1 | Async HTTP client for internal calls to datasette | DEC-3 locked; modern async-native HTTP client; not used in Phase 2 placeholder but installed so the package skeleton enforces "this is how the frontend talks to datasette" |
| `uvicorn[standard]` | 0.44.0 | ASGI server | Pulled by fastapi[standard]; pin explicitly so future phases can rely on the version |

[VERIFIED: PyPI registry, queried 2026-04-20]

### Supporting (frontend dev deps)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.0.3 | Test runner | Required by CLAUDE.md; phase 2 only needs a smoke test for `/frontend-test` |
| `black` | 26.3.1 | Formatter | DEC-3 / CON-frontend-stack explicitly require black-formatted code |
| `ruff` | 0.15.11 | Linter | Standard Python lint pairing with black; cheap insurance against drift |
| `httpx` (test) | 0.28.1 | Already in runtime deps; doubles as FastAPI test client transport | FastAPI's `TestClient` from `fastapi.testclient` uses httpx under the hood |

[VERIFIED: PyPI registry, queried 2026-04-20]

### Core (proxy service)

| Image | Tag | Purpose | Why Standard |
|-------|-----|---------|--------------|
| `caddy` | `2.11.2-alpine` | Reverse proxy | DEC-4 locked. Alpine variant (~57MB) is the official recommendation when image size matters; ships `curl`, exposes 80/443/443-udp/2019; no built-in HEALTHCHECK so we add one. |

[VERIFIED: Docker Hub registry, queried 2026-04-20 — `2.11.2`, `2.11.2-alpine`, `2.11`, `2`, `latest` all currently published]

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Decision |
|------------|-----------|----------|----------|
| `python:3.12-slim` (frontend base) | `python:3.12-alpine` | Alpine is smaller (~50MB vs ~120MB) but musl libc breaks some C-extension wheels; FastAPI/uvicorn work but not worth the troubleshooting tax for the savings | **Use slim.** Matches existing datasette Dockerfile (consistency). |
| `python:3.12-slim` (frontend base) | `gcr.io/distroless/python3` | Smaller still and no shell, but no `python` CLI at runtime → can't run the urllib healthcheck one-liner; would force an external check sidecar | **Use slim.** Distroless is a Phase-7+ optimization, not now. |
| `caddy:2.11.2-alpine` | `caddy:2.11.2` (Debian-based) | Debian is ~150MB vs Alpine ~57MB; same `curl` availability | **Use alpine.** No reason to ship the bigger one. |
| `caddy:2-alpine` (rolling) | `caddy:2.11.2-alpine` (pinned) | Rolling tags break in CI/CD when upstream cuts a new minor | **Pin to `2.11.2-alpine`.** Update via PR like any other dep. |
| `uvicorn` direct | `fastapi run` (newer Tiangolo wrapper) | `fastapi run` is the official 2026 invocation but is just `uvicorn` underneath; for a placeholder service the difference is cosmetic | **Use `uvicorn` directly** — fewer layers of indirection; matches what most production deployments do. |
| Compose default bridge network | Explicit `networks:` block with custom name | Explicit network gives a stable name and isolation; default also works fine and is one less thing to maintain | **Use default.** Phase 2 is "minimum viable change" per R7. Explicit network is a nice-to-have we can add later if needed. |

### Installation (frontend pyproject.toml)

```bash
# Inside packages/zeeker-frontend/
uv init --package --no-readme   # then edit pyproject.toml
uv add 'fastapi[standard]==0.136.0' 'httpx==0.28.1' 'jinja2==3.1.6' 'uvicorn[standard]==0.44.0'
uv add --dev 'pytest==9.0.3' 'black==26.3.1' 'ruff==0.15.11'
uv lock
```

**Version verification:** All package versions in this section were verified against the PyPI JSON API (`curl -s https://pypi.org/pypi/{name}/json | jq -r .info.version`) and Docker Hub tags API (`curl -s 'https://hub.docker.com/v2/repositories/library/caddy/tags?page_size=15' | jq -r '.results[].name'`) on 2026-04-20. The planner should re-verify before commit if more than ~30 days have passed.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────────┐
                    │  HOST  (developer laptop / prod box) │
                    │                                       │
   curl https://    │   :80   :443                          │
   localhost/sg…  ──┼─►┌──────────────────┐                 │
                    │  │  caddy (public)  │                 │
                    │  │  caddy:2.11.2-   │                 │
                    │  │  alpine          │                 │
                    │  │  EXPOSE 80/443   │                 │
                    │  └─────┬────────────┘                 │
                    │        │                              │
                    │        │ Phase 2: 100% to datasette   │
                    │        │ Phase 3: suffix-routes split │
                    │        ▼                              │
                    │  ┌──────────────────┐                 │
                    │  │ default bridge   │                 │
                    │  │ network (DNS by  │                 │
                    │  │ service name)    │                 │
                    │  └─┬─────────────┬──┘                 │
                    │    │             │                    │
                    │    ▼             ▼                    │
                    │  ┌─────────┐   ┌────────────┐         │
                    │  │datasette│   │  frontend  │         │
                    │  │ :8001   │   │  :8000     │         │
                    │  │ NO HOST │   │  (FastAPI) │         │
                    │  │ PORTS   │   │  /frontend │         │
                    │  └────┬────┘   │  -test only│         │
                    │       │        └────────────┘         │
                    │       │                               │
                    │       ▼                               │
                    │   ./data (SQLite from S3 at boot)     │
                    │   — datasette ONLY                    │
                    └───────────────────────────────────────┘

   Healthcheck wiring (Compose-side):
   caddy.depends_on:
     datasette: service_healthy   (waits for /-/versions.json → 200)
     frontend:  service_healthy   (waits for /frontend-test → 200)
```

**Trace the primary use case (Phase 2):** Browser → host port `:443` → caddy container → caddy reverse_proxy directive → docker bridge DNS lookup `datasette` → datasette container `:8001` → response → browser. Frontend container exists, is healthy, but is unreachable from outside (Caddy doesn't route to it yet — that's Phase 3).

### Component Responsibilities

| Component | Path in repo | Responsibility | Phase 2 status |
|-----------|--------------|----------------|----------------|
| `caddy` service | `Caddyfile` (repo root, NEW) | Public TLS + reverse proxy | NEW in Phase 2 |
| `frontend` service | `packages/zeeker-frontend/` (NEW) | Will own all HTML in later phases; placeholder only in Phase 2 | NEW in Phase 2 |
| `datasette` service | `Dockerfile`, `entrypoint.sh`, `metadata.json` (root) | Data API; serves all HTML in Phase 2 (still); shrinks in Phase 7 | EXISTING; only `ports:` removed |

### Recommended Project Structure

After Phase 2 (additions only — nothing is renamed/moved):

```
zeeker-datasette/                       # repo root (current flat layout preserved)
├── Caddyfile                           # NEW — Phase 2 single-backend proxy
├── docker-compose.yml                  # EDITED — three services, datasette ports removed
├── docker-compose.prod.yml             # NEW (optional) — production overlay with auto-HTTPS
├── Dockerfile                          # UNCHANGED — datasette image
├── entrypoint.sh                       # UNCHANGED
├── metadata.json                       # UNCHANGED
├── packages/                           # NEW directory
│   └── zeeker-frontend/                # NEW package
│       ├── pyproject.toml              # NEW — fastapi+jinja2+httpx+uvicorn deps
│       ├── uv.lock                     # NEW — generated by `uv lock`
│       ├── Dockerfile                  # NEW — python:3.12-slim + uv
│       ├── .dockerignore               # NEW — excludes .venv, __pycache__, .pytest_cache
│       ├── README.md                   # NEW — "this is the M2 placeholder; see roadmap"
│       ├── src/
│       │   └── zeeker_frontend/
│       │       ├── __init__.py
│       │       ├── main.py             # FastAPI app + /frontend-test
│       │       ├── templates/          # empty dir, scaffolded for Phases 4–6
│       │       └── static/             # empty dir, scaffolded for Phases 4–6
│       └── tests/
│           └── test_frontend.py        # smoke test of /frontend-test
└── (existing datasette files unchanged)
```

### Pattern 1: Compose three-service topology with health-gated startup

**What:** Compose spins up datasette and frontend in parallel; caddy waits for both to be `healthy` before starting; only caddy publishes ports.

**When to use:** Anytime you need a reverse proxy + N backends and want zero-downtime / no-503 startup.

**Example (full `docker-compose.yml` for Phase 2):**

```yaml
# Source pattern: docker.com Compose docs (depends_on with service_healthy)
# https://docs.docker.com/compose/how-tos/startup-order/

services:
  datasette:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: zeeker-datasette
    # NOTE: ports: removed (REQ-internal-only-datasette-exposure).
    # Datasette is reachable only via the internal bridge network at datasette:8001.
    environment:
      - S3_BUCKET=${S3_BUCKET}
      - S3_PREFIX=${S3_PREFIX:-latest}
      - S3_ENDPOINT_URL=${S3_ENDPOINT_URL}
      - AWS_REGION=${AWS_REGION:-default}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - DATASETTE_MATOMO_SERVER_URL=${DATASETTE_MATOMO_SERVER_URL}
      - DATASETTE_MATOMO_SITE_ID=${DATASETTE_MATOMO_SITE_ID}
    restart: unless-stopped
    healthcheck:
      # CON-healthcheck: GET /-/versions.json returns 200 = healthy.
      # The current healthcheck targets / which is fine but less specific;
      # switch to /-/versions.json so it survives Phase 7 template deletion.
      test: ["CMD", "curl", "-fsS", "http://localhost:8001/-/versions.json"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s   # S3 download is 10–30s per CON-healthcheck; 60s gives margin

  frontend:
    build:
      context: ./packages/zeeker-frontend
      dockerfile: Dockerfile
    container_name: zeeker-frontend
    # No ports published; reachable only at frontend:8000 internally.
    # Crucially: NO volume mount of ./data (REQ-frontend-data-via-http).
    restart: unless-stopped
    healthcheck:
      # python:3.12-slim has neither curl nor wget; use stdlib urllib.
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/frontend-test', timeout=2).status==200 else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s   # FastAPI/uvicorn cold start is sub-second; 10s is generous

  caddy:
    image: caddy:2.11.2-alpine
    container_name: zeeker-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"   # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      datasette:
        condition: service_healthy
      frontend:
        condition: service_healthy
    healthcheck:
      # Official caddy:2.11.2-alpine ships curl (verified from upstream Dockerfile).
      test: ["CMD", "curl", "-fsS", "http://localhost:2019/metrics"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 5s

volumes:
  caddy_data:
  caddy_config:
```

Note: the Caddy admin endpoint is on port 2019 by default (verified — `EXPOSE 2019` in the upstream Caddy Alpine Dockerfile) and serves `/metrics` and `/config/` etc. Using `/metrics` as the healthcheck target is cheaper than proxying through `/`.

### Pattern 2: Caddyfile transparent proxy (Phase 2)

**What:** Single site block, all traffic to one backend, plain HTTP only (TLS handled by overlay in production).

**When to use:** First step of an incremental cutover before you start splitting traffic.

**Example (`Caddyfile` at repo root, Phase 2 version):**

```caddyfile
# Source: caddyserver.com/docs/quick-starts/reverse-proxy
# Phase 2: 100% of traffic goes to datasette (no routing flip yet).
# Phase 3 will replace the body of this site block with suffix matchers.

{
    # Disable auto-HTTPS for local dev (we'll override in docker-compose.prod.yml)
    auto_https off
}

:80 {
    # Phase 3 hook (commented stub for Phase 3's reference):
    # @datasette_api {
    #     path *.json *.csv *.db /-/*
    # }
    # reverse_proxy @datasette_api datasette:8001
    # reverse_proxy frontend:8000

    # Phase 2: everything → datasette, byte-identical to today's direct exposure.
    reverse_proxy datasette:8001
}
```

**Phase 3 forward-compat sketch** (do NOT include in Phase 2's Caddyfile; just informs the layout):

```caddyfile
:80 {
    @datasette_api {
        path *.json *.csv *.db /-/*
    }
    reverse_proxy @datasette_api datasette:8001
    reverse_proxy frontend:8000
}
```

The Phase-2 file is structured so Phase 3's diff is "delete one line, add four" — minimal blast radius.

### Pattern 3: FastAPI placeholder app

**What:** Single-file FastAPI app with one endpoint, designed to grow without restructuring.

**Example (`packages/zeeker-frontend/src/zeeker_frontend/main.py`):**

```python
# Source: docs.astral.sh/uv/guides/integration/fastapi/
"""Zeeker frontend (placeholder).

This is the M2 Phase 2 placeholder. It exposes only /frontend-test so the
container has something to healthcheck against. Real HTML routes arrive in
Phases 4–6.

Deliberately does NOT touch SQLite (REQ-frontend-data-via-http / DEC-5).
All future data access goes via httpx → http://datasette:8001/...json.
"""
from fastapi import FastAPI

app = FastAPI(
    title="zeeker-frontend",
    description="Placeholder — see .planning/ROADMAP.md M2 Phases 4–6 for real routes.",
    version="0.1.0",
)


@app.get("/frontend-test")
def frontend_test() -> dict[str, str]:
    """Healthcheck/liveness probe target.

    Returns JSON (not HTML) deliberately: this phase intentionally avoids
    template work so we don't pay rendering costs in M2 Phase 2.
    """
    return {"status": "ok", "service": "zeeker-frontend"}
```

### Pattern 4: Frontend Dockerfile (uv + slim)

**Example (`packages/zeeker-frontend/Dockerfile`):**

```dockerfile
# Source: docs.astral.sh/uv/guides/integration/fastapi/
# Pattern matches existing root Dockerfile (uv from astral image, slim base).

FROM python:3.12-slim

# Pull uv binary from the official image (no apt-get needed for uv itself).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy lockfile first for layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-install-project

# Now copy source and install the package itself.
COPY src/ ./src/
RUN uv sync --frozen --no-cache

# Internal port; not published to host.
EXPOSE 8000

# Run uvicorn directly (simpler than `fastapi run` indirection).
# --host 0.0.0.0 so the container's bridge IP can receive traffic from caddy.
CMD ["uv", "run", "uvicorn", "zeeker_frontend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**No system packages installed** — explicitly NOT installing `sqlite3`, `libsqlite3-dev`, `curl`, or `wget`. This is the architectural fence (REQ-frontend-data-via-http) made physical in the Dockerfile. The healthcheck uses `python -c 'import urllib.request; ...'` instead of `curl`.

### Pattern 5: Frontend `pyproject.toml`

**Example (`packages/zeeker-frontend/pyproject.toml`):**

```toml
[project]
name = "zeeker-frontend"
version = "0.1.0"
description = "FastAPI frontend for data.zeeker.sg (placeholder; see roadmap M2)."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]==0.136.0",
    "httpx==0.28.1",
    "jinja2==3.1.6",
    "uvicorn[standard]==0.44.0",
]

[dependency-groups]
dev = [
    "black==26.3.1",
    "pytest==9.0.3",
    "ruff==0.15.11",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/zeeker_frontend"]

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

### Anti-Patterns to Avoid

- **Mounting `./data` on the frontend service** — silently violates DEC-5 / REQ-frontend-data-via-http even if the code never opens it. The compose-level fence is what makes the constraint enforceable.
- **Installing `sqlite3-dev` in the frontend Dockerfile** — same as above; if it's installed, someone will eventually `import sqlite3` and the architectural boundary is gone. Don't install it.
- **Using `localhost` as the site address in the Caddyfile** — triggers Caddy's internal CA which generates a self-signed cert; browsers will warn. For local dev, use `:80` (port-only) which serves plain HTTP.
- **Setting `condition: service_started` instead of `service_healthy`** — `service_started` returns immediately when the container process starts, before datasette has finished its 10–30s S3 download. Caddy will start, get traffic, proxy to datasette, get connection refused, and 502.
- **Putting `start_period` too low on datasette** — known Compose footgun: dependent services don't start until the *full* `start_period` has elapsed even if the dep goes healthy sooner ([docker/compose#11131](https://github.com/docker/compose/issues/11131)). 60s on datasette is a reasonable balance.
- **Removing `ports:` from datasette and forgetting to remove the `127.0.0.1:` host-binding annotation** — the existing line is `"127.0.0.1:8001:8001"` so removing it cleanly is just deleting two lines.
- **Pinning Caddy to `:latest`** — rolling tag, breaks reproducibility. Pin to `2.11.2-alpine`.
- **Using `wget` in the Caddy healthcheck** — official Caddy Alpine image ships curl, not wget (verified from upstream Dockerfile). Use `curl`.
- **Using `curl` in the frontend healthcheck** — `python:3.12-slim` doesn't ship curl; using it would require an `apt-get install curl` layer. Use the urllib one-liner instead.
- **Adding an explicit `networks:` block "for safety"** — Compose's default project network already gives DNS-by-service-name; an explicit network is one more thing to maintain for zero benefit at this scale.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TLS certificate provisioning + renewal | A cron + certbot setup | Caddy auto-HTTPS (in `docker-compose.prod.yml`) | Caddy was designed around this; ACME edge cases are deep |
| Service-startup ordering | A `wait-for-it.sh` shell loop | Compose `depends_on: condition: service_healthy` | Built-in primitive; no external script needed |
| Internal service discovery | Hardcoded IPs or `extra_hosts` | Default Compose bridge network DNS | DNS-by-service-name is automatic and free |
| HTTP healthcheck inside slim image | `apt-get install curl` for one healthcheck | `python -c 'import urllib.request; ...'` | stdlib is already in the image; no extra layer, no extra attack surface |
| Reverse proxy URL routing | nginx with regex `location` blocks | Caddyfile `path` matcher | DEC-4 locked; Caddy syntax is simpler and the `path` matcher supports both prefix (`/-/*`) and suffix (`*.json`) wildcards in one named matcher |
| API regression diffing | Hand-rolled assertion script | A captured baseline of `curl -s` output + `diff` (with a `jq`-based filter for timestamps) | The job is "exact bytes after filtering version-strings" — `diff` is the right tool; no library needed |
| Frontend lockfile management | `pip install` + `pip freeze` | `uv lock` + `uv sync --frozen` | Already the project standard (existing datasette uses it); reproducible installs |

**Key insight:** Phase 2 has zero novel infrastructure problems. Every problem in the phase has an off-the-shelf primitive: Compose for orchestration, Caddy for proxy, urllib for healthcheck, uv for deps. The phase's value is in *combining* these primitives correctly — the failure mode is gluing them wrong (e.g., wrong healthcheck command for the wrong base image), not building bespoke code.

## Runtime State Inventory

> Phase 2 is partly an infrastructure topology change. Although it doesn't rename or migrate stored data, it does change network exposure and adds containers — those have runtime-state implications worth checking explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — datasette's `./data` directory and S3-hydrated SQLite files are not touched. Frontend deliberately has no data. | None. |
| Live service config | None new in this phase. The Caddyfile is in git. The frontend's metadata is in `pyproject.toml`. The datasette service config in `docker-compose.yml` is in git. | Code-only; no out-of-git config introduced. |
| OS-registered state | `docker compose` will create new container names: `zeeker-frontend`, `zeeker-caddy`. If a previous run left orphan containers with these names, `docker compose up` will fail with "name already in use." | Phase-2 task should include `docker compose down --remove-orphans` as a pre-step the first time the new compose is brought up. |
| Secrets/env vars | No new secrets in this phase. Existing AWS / S3 / Matomo env vars are unchanged. (Frontend doesn't need any of them — it's stateless and talks only to datasette over the internal network.) | None. The frontend container should NOT inherit AWS creds — keep its `environment:` block empty in compose to enforce that. |
| Build artifacts / installed packages | New: `packages/zeeker-frontend/.venv/`, `packages/zeeker-frontend/uv.lock`, `packages/zeeker-frontend/src/zeeker_frontend.egg-info/` (if hatchling generates one). New Docker images: `zeeker-datasette_frontend`, plus a pulled `caddy:2.11.2-alpine`. | Add `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/` to `.dockerignore` and to the package's `.gitignore` (or extend repo-root `.gitignore`). |

**Network exposure change:** Removing `ports: ["127.0.0.1:8001:8001"]` from datasette is the one runtime-state change that must be communicated. Anyone hitting `http://localhost:8001` directly today (browser bookmark, local script, IDE plugin) will get connection-refused after this phase. Caddy on `:80`/`:443` is the new entry point. **Action: include this in the phase's release-notes/CHANGELOG.**

## Common Pitfalls

### Pitfall 1: `start_period` doesn't short-circuit early

**What goes wrong:** You set `start_period: 60s` on datasette. Datasette becomes healthy at the 15s mark. Caddy still doesn't start until 60s have elapsed.

**Why it happens:** Confirmed Compose behavior (see [docker/compose#11131](https://github.com/docker/compose/issues/11131)). `start_period` is a *minimum* grace window during which failed checks don't count, NOT a maximum window after which dependents proceed early.

**How to avoid:** Set `start_period` to a realistic estimate of slow boot (60s for datasette per CON-healthcheck), not "as long as it could possibly take." For frontend (cold start <1s), use `start_period: 10s`.

**Warning signs:** `docker compose up -d` blocks for noticeably longer than expected. `docker compose ps` shows `(healthy)` on backends but `caddy` is `Created` not `Running` for tens of seconds.

### Pitfall 2: `python:3.12-slim` lacks curl/wget

**What goes wrong:** You write `test: ["CMD", "curl", "-f", "http://localhost:8000/frontend-test"]`. Container starts, healthcheck immediately reports `unhealthy`, Caddy never starts because it's waiting on `frontend.condition: service_healthy`.

**Why it happens:** Slim images are minimal — neither `curl` nor `wget` is installed.

**How to avoid:** Use the Python urllib one-liner in the healthcheck (Pattern 1, frontend service). It uses only stdlib and adds no install layers.

**Warning signs:** `docker inspect zeeker-frontend --format '{{json .State.Health}}' | jq` shows `"ExitCode": 127` ("command not found") in `Log`.

### Pitfall 3: Caddy auto-HTTPS at `localhost` produces a self-signed cert

**What goes wrong:** You write `localhost { reverse_proxy ... }` in the Caddyfile. Caddy provisions an internal-CA cert and serves HTTPS. Browser warns "your connection is not private."

**Why it happens:** Caddy treats any hostname (including `localhost`) as a signal to enable auto-HTTPS using its internal CA when public ACME isn't available.

**How to avoid:** Use port-only site address `:80 { ... }` plus `{ auto_https off }` global option for local dev. Production overlay (`docker-compose.prod.yml`) can use the real hostname `data.zeeker.sg { ... }` and let Caddy obtain a real cert via ACME.

**Warning signs:** Browser shows "Not Secure" or cert warnings when hitting `https://localhost`. Solved by using `http://localhost` (port 80) in dev.

### Pitfall 4: Forgetting to remove host-port annotation

**What goes wrong:** You delete `- "8001:8001"` from datasette's `ports:` but leave the `127.0.0.1:` prefix on a different line, or leave the `ports:` key with an empty list.

**Why it happens:** The current value is `"127.0.0.1:8001:8001"` — single line with the bind IP baked in. Easy to over-edit.

**How to avoid:** Delete both the `ports:` key AND its single child entry. Verify with `docker compose config | grep -A1 'datasette:' | grep ports` — should produce no match.

**Warning signs:** `docker compose config` still shows a `ports:` block under datasette. REQ-internal-only-datasette-exposure verification fails.

### Pitfall 5: Frontend container inheriting AWS credentials by accident

**What goes wrong:** You copy-paste the datasette service's `environment:` block into the frontend service "for symmetry." Now the frontend has S3 creds it should never have.

**Why it happens:** Convenience copy-paste.

**How to avoid:** Frontend's `environment:` block should be empty (or only `PYTHONUNBUFFERED=1`). The frontend has no business with S3.

**Warning signs:** `docker compose exec frontend env | grep -i aws` returns anything.

### Pitfall 6: Caddy admin endpoint exposed publicly

**What goes wrong:** You publish `2019:2019` from the caddy container thinking "it's just metrics." Anyone who reaches the box can `POST /load` to the admin API and reconfigure Caddy live.

**Why it happens:** The official Caddy image `EXPOSE`s 2019, but `EXPOSE` is documentary only — you only publish ports that you list in compose's `ports:`. Easy to add it accidentally.

**How to avoid:** In `docker-compose.yml`, only publish `80` and `443`. Use port `2019` only for the in-container healthcheck (not published).

**Warning signs:** `docker compose ps` shows `0.0.0.0:2019->2019/tcp` for caddy.

### Pitfall 7: Bridge-network name resolution silently broken

**What goes wrong:** `caddy` logs "dial tcp: lookup datasette on 127.0.0.11:53: no such host." Caddy can't find datasette by name.

**Why it happens:** Custom networking with `network_mode: bridge` (the *default* docker0 bridge, not Compose's user-defined bridge) disables DNS-by-name. This shouldn't happen with stock Compose but does happen if someone copy-pastes `network_mode: bridge` from a tutorial.

**How to avoid:** Don't set `network_mode:` at all. Compose's default is a per-project user-defined bridge that DOES support DNS by service name.

**Warning signs:** `docker compose exec caddy nslookup datasette` returns "server can't find datasette: NXDOMAIN."

### Pitfall 8: `uv sync --frozen` fails because lockfile is missing

**What goes wrong:** Frontend Dockerfile has `RUN uv sync --frozen` but `uv.lock` doesn't exist yet (first build).

**Why it happens:** `--frozen` requires a lockfile; first-time setup needs `uv lock` to be run on the host before the first `docker build`.

**How to avoid:** Phase-2 task list MUST include "run `uv lock` on host" before "run `docker compose build frontend`." Alternatively, add a fallback: `RUN uv sync --frozen 2>/dev/null || uv sync` — but this hides drift, so prefer the explicit task.

**Warning signs:** `docker compose build frontend` fails with "uv.lock not found" or "the lockfile is out of date."

## Code Examples

### Verifying API byte-parity (REQ-api-byte-parity)

**Recipe:** Capture baseline JSON before the topology change; capture again after; diff with a `jq` filter to strip the volatile fields.

```bash
# BEFORE Phase 2 deployment (current single-service setup running on :8001)
mkdir -p /tmp/zeeker-baseline
for path in \
    /-/versions.json \
    /sg-gov-newsrooms/mlaw_news.json?_size=10 \
    /sg-gov-newsrooms/judiciary_news.json?_size=10 \
    /sg-gov-newsrooms.json \
  ; do
    safe=$(echo "$path" | tr '/?=&' '_')
    curl -fsS "http://localhost:8001${path}" \
      | jq 'walk(if type == "object" then del(.query_ms, .__time__) else . end)' \
      > "/tmp/zeeker-baseline/${safe}.json"
done

# AFTER Phase 2 deployment (caddy on :80, datasette internal-only)
mkdir -p /tmp/zeeker-after
for path in \
    /-/versions.json \
    /sg-gov-newsrooms/mlaw_news.json?_size=10 \
    /sg-gov-newsrooms/judiciary_news.json?_size=10 \
    /sg-gov-newsrooms.json \
  ; do
    safe=$(echo "$path" | tr '/?=&' '_')
    curl -fsS "http://localhost${path}" \
      | jq 'walk(if type == "object" then del(.query_ms, .__time__) else . end)' \
      > "/tmp/zeeker-after/${safe}.json"
done

# Diff
diff -ur /tmp/zeeker-baseline /tmp/zeeker-after
# Expected output: empty (no differences). REQ-api-byte-parity gate.
```

**Notes:**
- `walk` is a `jq` builtin that recurses into the response and strips out timing fields per PRD §3 ("timestamps and Datasette version strings excepted"). Adjust the strip-list if other volatile fields appear.
- For `-/versions.json` specifically, the version string IS the payload — that endpoint is exempt from the diff. Filter it out by checking only structural shape:
  ```bash
  diff <(jq 'keys' /tmp/zeeker-baseline/_-_versions.json_.json) \
       <(jq 'keys' /tmp/zeeker-after/_-_versions.json_.json)
  ```

### Verifying internal-only datasette exposure (REQ-internal-only-datasette-exposure)

```bash
# 1. Compose-config check: datasette MUST have no ports
docker compose config \
  | python3 -c "
import yaml, sys
c = yaml.safe_load(sys.stdin)
ds = c['services']['datasette']
assert 'ports' not in ds or not ds['ports'], 'REQ-internal-only-datasette-exposure FAIL: datasette has ports'
print('OK: datasette internal-only')
"

# 2. Runtime check: datasette container should have no published ports
docker inspect zeeker-datasette --format '{{json .NetworkSettings.Ports}}'
# Expected: "{}"

# 3. Caddy MUST be the only service with published ports
docker compose ps --format json | jq -r 'select(.Publishers | length > 0) | .Service'
# Expected output: "caddy" (and only "caddy")
```

### Verifying frontend has no SQLite (REQ-frontend-data-via-http)

```bash
# 1. No sqlite3 binary inside the container
docker compose exec frontend sh -c 'which sqlite3 || echo NO_SQLITE'
# Expected: "NO_SQLITE"

# 2. Python sqlite3 module IS in stdlib so it'll import — but the package
# itself MUST NOT have any explicit sqlite-related deps:
docker compose exec frontend cat /app/pyproject.toml | grep -iE 'sqlite|datasette' || echo "OK: no sqlite/datasette deps"

# 3. No ./data mount on frontend
docker inspect zeeker-frontend --format '{{json .Mounts}}' | jq '.[] | select(.Source | contains("/data"))'
# Expected: empty
```

### Verifying healthcheck status

```bash
# Compose-side
docker compose ps
# Expected (steady state):
#   NAME                  STATUS
#   zeeker-caddy          Up X minutes (healthy)
#   zeeker-datasette      Up X minutes (healthy)
#   zeeker-frontend       Up X minutes (healthy)

# Per-service detail
for svc in datasette frontend caddy; do
    echo "=== $svc ==="
    docker inspect "zeeker-${svc}" --format '{{json .State.Health}}' | jq '{Status, FailingStreak, LastLog: (.Log | last | .Output)}'
done
```

### Frontend smoke test (`packages/zeeker-frontend/tests/test_frontend.py`)

```python
# Source: fastapi.tiangolo.com/tutorial/testing/
"""Phase 2 smoke test for the frontend placeholder."""
from fastapi.testclient import TestClient

from zeeker_frontend.main import app


client = TestClient(app)


def test_frontend_test_returns_ok():
    response = client.get("/frontend-test")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "zeeker-frontend"}


def test_unknown_path_returns_404():
    """Phase 2 frontend has only one route; everything else is 404 (Caddy
    routes nothing to it yet, but if it did, 404 is correct)."""
    response = client.get("/some-other-path")
    assert response.status_code == 404
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `wait-for-it.sh` shell loops | Compose `depends_on: condition: service_healthy` | Compose v2 (long-form depends_on syntax) | Built-in primitive removes the need for a startup-ordering shell script |
| `pip install -r requirements.txt` | `uv sync --frozen` | uv landed late 2024; mainstream by 2025 | 10–100× faster installs; deterministic lockfile; existing datasette image already uses it |
| `gunicorn -k uvicorn.workers.UvicornWorker app:app` | `uvicorn app:app` directly (or `fastapi run`) | uvicorn added native `--workers` support; 2025+ | Single-process container (one worker per container) is the modern pattern; let the orchestrator scale by spawning more containers, not more workers |
| nginx + manual cert renewal | Caddy with `auto_https` | 2019+; Caddy v2 made it default | Eliminates an entire class of "cert expired Saturday at 3am" outages |
| Rolling Docker tags (`:latest`) | Pinned digests or pinned semver tags | Industry default since Supply-chain attacks of 2021+ | Pin to `caddy:2.11.2-alpine` for reproducibility |

**Deprecated/outdated:**
- `links:` in compose — superseded by Compose's default network DNS years ago; never use `links:` in new code.
- `tiangolo/uvicorn-gunicorn-fastapi` Docker image — Tiangolo himself now recommends running uvicorn directly without gunicorn; the combined image is unnecessary for new projects.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The existing repo's `pyproject.toml` is the *datasette* package's pyproject (i.e., the existing flat repo is implicitly the datasette package per CONTEXT decision). The frontend gets its own `pyproject.toml` under `packages/zeeker-frontend/`. | Architecture Patterns → Recommended Project Structure | If we should ALSO restructure the existing root into `packages/zeeker-datasette/` in this phase, the compose `build.context` for the datasette service breaks. Mitigation: CONTEXT.md explicitly says "option (b) for this phase — minimum disruption" so this should be safe, but planner should sanity-check. |
| A2 | The Caddy admin endpoint at `localhost:2019/metrics` returns 200 by default in `caddy:2.11.2-alpine`. | Pattern 1 (Caddy healthcheck) | If `/metrics` requires explicit enablement in the Caddyfile, the Caddy healthcheck will report unhealthy. Mitigation: planner verification task should `docker compose exec caddy curl -fsS http://localhost:2019/metrics` before declaring the healthcheck good. Fallback: use `curl -fsS http://localhost:80/` (proxies to datasette). |
| A3 | The current datasette healthcheck command `curl -f http://localhost:8001/` returns 200. The proposed change to `curl -fsS http://localhost:8001/-/versions.json` is per CON-healthcheck. | Pattern 1 (datasette healthcheck) | Low risk — `/-/versions.json` is a stock Datasette endpoint that always exists. But planner should run the new healthcheck once before declaring victory. |
| A4 | `python:3.12-slim` with no extra apt-gets has `python -c 'import urllib.request'` working out of the box. | Pattern 1 (frontend healthcheck) | Effectively zero — `urllib` is stdlib and slim images include the Python stdlib. |
| A5 | Removing `ports:` from datasette has no other side-effects (CORS, S3 download, etc. all unaffected). | Architecture Patterns → Pattern 1 | Very low risk: `ports:` is purely a host-binding directive; removing it doesn't change anything inside the container. `--cors` controls response headers regardless of who's calling. The S3 download happens at startup before any port matters. |
| A6 | Default Compose project network DNS resolves `datasette`, `frontend`, `caddy` correctly without an explicit `networks:` block. | Anti-Patterns + Pitfall 7 | Very low risk — this is the documented Compose default behavior. Verifiable in 5 seconds with `docker compose exec caddy nslookup datasette`. |
| A7 | `caddy:2.11.2-alpine` is the appropriate version to pin to as of 2026-04-20. | Standard Stack | Verified 2026-04-20 against Docker Hub tags API. May drift over time; planner should re-verify if more than ~30 days have passed. |
| A8 | The `walk` jq filter for stripping `query_ms` / `__time__` is sufficient to make the byte-parity diff meaningful. | Code Examples → byte-parity | Medium — there may be other volatile fields (request IDs, etc.) we haven't observed. Mitigation: first run the diff and inspect any deltas; expand the filter if more volatile fields appear. The recipe is correct in shape; the filter list is the part that may need iteration. |

**The planner SHOULD verify items A1, A2, and A8** before locking task descriptions, since they have the highest cost-if-wrong.

## Open Questions

1. **Should Phase 2 also create `docker-compose.prod.yml`?**
   - What we know: CONTEXT.md says auto-HTTPS in local dev should be skipped; production needs it.
   - What's unclear: Whether the production overlay should land in Phase 2 or Phase 3 (after the routing flip is real).
   - Recommendation: Land the local `docker-compose.yml` in Phase 2; defer `docker-compose.prod.yml` until the production deploy actually happens (could be Phase 2.5 or Phase 3). For Phase 2 it's enough that the local compose works.

2. **What's the canonical path for the baseline JSON capture?**
   - What we know: REQ-api-byte-parity needs baseline-vs-post diff.
   - What's unclear: Whether baseline files should be committed to the repo (`.planning/baselines/phase-02/`) or kept ephemeral in `/tmp`.
   - Recommendation: Commit baselines under `.planning/baselines/phase-02/` so future phases can re-diff against them when they touch the API surface again.

3. **Should the phase include a smoke-test CI workflow that runs the byte-parity diff?**
   - What we know: REQ-api-byte-parity is an "every phase boundary" requirement, so it'll need re-running often.
   - What's unclear: Whether scripting it now (a `make verify-parity` target) is in scope for Phase 2, or is its own phase deliverable.
   - Recommendation: Include a `scripts/verify_api_parity.sh` script in Phase 2 that automates the recipe in Code Examples. It's low cost and pays for itself starting at Phase 3.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Building/running all three services | ✓ | 29.3.0 | — |
| Docker Compose | Multi-service orchestration | ✓ | v5.1.0 | — |
| `curl` | Healthcheck inside Caddy + datasette containers; baseline-capture script on host | ✓ | 8.7.1 (host); bundled in caddy:2.11.2-alpine and the existing datasette image | — |
| `jq` | Strip volatile fields from baseline JSON | ✓ | 1.7.1 | python `json` module if needed |
| `uv` | Frontend dependency management | ✓ | 0.7.17 (host); installed inside frontend image from `ghcr.io/astral-sh/uv:latest` | — |
| Python 3.12+ | Frontend runtime | ✓ | 3.13.5 (host); 3.12-slim image base | — |
| Caddy image (`caddy:2.11.2-alpine`) | Reverse proxy | Pulled at first `docker compose up`; ~57MB | 2.11.2 verified live on Docker Hub 2026-04-20 | — |
| `ghcr.io/astral-sh/uv:latest` | Source for `uv` binary in frontend Dockerfile | Pulled at first build | rolling | Pin to a digest if reproducibility is critical (`uv:0.7.17` tag also published) |
| AWS credentials (for datasette S3 download) | Existing datasette boot path | Inherited from existing setup | — | Without S3 creds, datasette starts but `/data` is empty; it'll still serve `/-/versions.json` so healthcheck passes, but no databases. Affects byte-parity gate (no databases to diff). |

**Missing dependencies with no fallback:** None — the dev box already has everything needed.

**Missing dependencies with fallback:**
- AWS creds for the datasette S3 download — if developer doesn't have them, baseline diff against an empty datasette is meaningless. Mitigation: drop a local `.db` file in `./data/` for testing if S3 isn't reachable.

## Validation Architecture

> Section included because `.planning/config.json` does not exist; per the agent rules, absence of `workflow.nyquist_validation` defaults to **enabled**.

### Test Framework

| Property | Value |
|----------|-------|
| Frontend tests | `pytest 9.0.3` (declared as dev dep in `packages/zeeker-frontend/pyproject.toml`) |
| Frontend test command (host) | `cd packages/zeeker-frontend && uv run pytest -q` |
| Frontend test command (inside container) | `docker compose exec frontend uv run pytest -q` |
| Compose-config validation | `docker compose config -q` (no exit code = valid) |
| Healthcheck status snapshot | `docker compose ps --format json` |
| Existing repo's test framework | `pytest>=8.4.0` already in root `pyproject.toml`; root tests live in `tests/` and are unaffected by Phase 2 |
| Quick run command | `cd packages/zeeker-frontend && uv run pytest -q && docker compose config -q` |
| Full suite command | `bash scripts/verify_phase_02.sh` (created by phase 2 — see Wave 0 Gaps) |

### Phase Requirements → Test Map

The "automated check" column distinguishes Phase 2 done correctly from Phase 2 looks done but isn't. Each test must be runnable from a developer laptop with the stack up.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-incremental-migration | Site behavior unchanged from user perspective; rollback is a one-line revert | smoke | `bash scripts/verify_api_parity.sh` (uses pre-captured baseline) | ❌ Wave 0 |
| REQ-internal-only-datasette-exposure | `docker compose config` shows no `ports:` on datasette | static | `docker compose config \| python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); assert not d['services']['datasette'].get('ports'), 'datasette has ports'"` | ❌ Wave 0 (script wraps it) |
| REQ-internal-only-datasette-exposure | At runtime, only Caddy publishes ports | runtime | `docker compose ps --format json \| jq -e 'all(.[] ; if .Service == "caddy" then .Publishers \| length > 0 else .Publishers \| length == 0 end)'` | ❌ Wave 0 |
| REQ-frontend-data-via-http | Frontend container has no `sqlite3` binary | runtime | `docker compose exec frontend sh -c '! command -v sqlite3'` | ❌ Wave 0 |
| REQ-frontend-data-via-http | Frontend `pyproject.toml` declares no sqlite-related deps | static | `! grep -iE 'sqlite\|datasette' packages/zeeker-frontend/pyproject.toml` | ❌ Wave 0 (or covered by code review) |
| REQ-frontend-data-via-http | Frontend container has no `./data` mount | runtime | `docker inspect zeeker-frontend --format '{{json .Mounts}}' \| jq -e 'all(.[] ; .Source \| contains("/data") \| not)'` | ❌ Wave 0 |
| REQ-preserve-zeeker-cli | `zeeker init/add/build/deploy` continue to work | manual / out-of-band | Run `zeeker deploy` against a test database; verify it still produces a queryable result. (CLI lives in `houfu/zeeker` workspace, not this repo.) | manual-only |
| REQ-api-byte-parity | `curl -s https://localhost/sg-gov-newsrooms/mlaw_news.json` returns identical bytes pre/post (modulo timestamps + version strings) | smoke | `bash scripts/verify_api_parity.sh` (compares `.planning/baselines/phase-02/*.json` to live responses through Caddy) | ❌ Wave 0 |
| Internal: Caddy can reach datasette by name | DNS-by-service-name works | runtime | `docker compose exec caddy nslookup datasette \| grep -q "Address.*datasette"` | covered by health-gate startup, but explicit script is cheap |
| Internal: Frontend container is independently reachable internally | The frontend container is alive even though Caddy doesn't route to it in Phase 2 | runtime | `docker compose exec frontend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/frontend-test').status)"` should print `200` | ❌ Wave 0 |
| Internal: Phase-3 forward-compat | `/frontend-test` returns 404 when curled through Caddy (proves Caddy is still routing 100% to datasette) | smoke | `[ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost/frontend-test)" = "404" ]` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd packages/zeeker-frontend && uv run pytest -q` + `docker compose config -q` (~2s; no docker build)
- **Per wave merge:** `bash scripts/verify_phase_02.sh` — full bring-up + healthcheck snapshot + byte-parity diff (~2 min)
- **Phase gate:** Full suite green, then `/gsd-verify-work` confirms each REQ-* item maps to a passing test in this matrix.

### Wave 0 Gaps

The following test infrastructure does NOT exist yet and must be created before downstream waves can claim "done":

- [ ] `scripts/verify_phase_02.sh` — wraps all the runtime checks above into one exit-code-driven script. ~50 lines of bash.
- [ ] `scripts/verify_api_parity.sh` — captures or compares-against-baseline JSON for the four representative endpoints in Code Examples. ~30 lines of bash.
- [ ] `scripts/capture_baseline.sh` — one-shot script run BEFORE removing `ports:` from datasette, captures baseline JSON to `.planning/baselines/phase-02/`. ~20 lines of bash. **Critical: must run while the OLD compose is still up — i.e., as the first task in the phase, before any compose edits.**
- [ ] `.planning/baselines/phase-02/` — directory and committed baseline files (small JSON, suitable for git).
- [ ] `packages/zeeker-frontend/tests/test_frontend.py` — covers `/frontend-test` returns expected JSON and unknown paths return 404 (smoke level).
- [ ] `packages/zeeker-frontend/tests/conftest.py` — minimal; just a TestClient fixture if more tests are added later.
- [ ] Framework install: `cd packages/zeeker-frontend && uv sync` — first-time setup.

## Sources

### Primary (HIGH confidence)
- [Caddy Docker Hub registry](https://hub.docker.com/_/caddy) — verified `2.11.2`, `2.11.2-alpine` published, image variants and ports
- [Caddyserver: reverse-proxy quick start](https://caddyserver.com/docs/quick-starts/reverse-proxy) — minimum viable reverse_proxy + auto_https semantics
- [Caddyserver: request matchers](https://caddyserver.com/docs/caddyfile/matchers) — `path` matcher with suffix wildcards (`*.json`); multiple paths OR'd; named matcher syntax
- [Caddyserver: common patterns](https://caddyserver.com/docs/caddyfile/patterns) — multi-handle layout for the Phase-3 forward-compat sketch
- [Docker Compose: control startup order](https://docs.docker.com/compose/how-tos/startup-order/) — `depends_on: condition: service_healthy` syntax
- [Docker Compose services reference](https://docs.docker.com/reference/compose-file/services/) — healthcheck fields (interval, timeout, retries, start_period)
- [uv: integration with FastAPI](https://docs.astral.sh/uv/guides/integration/fastapi/) — official Dockerfile pattern, pyproject.toml shape, `uv sync --frozen` invocation
- [PyPI registry](https://pypi.org/) — verified versions of fastapi (0.136.0), httpx (0.28.1), jinja2 (3.1.6), uvicorn (0.44.0), pytest (9.0.3), black (26.3.1), ruff (0.15.11)
- [Caddy Docker GitHub: Alpine Dockerfile](https://github.com/caddyserver/caddy-docker) — verified curl is bundled, EXPOSE 80/443/443-udp/2019, no built-in HEALTHCHECK
- Repository inspection (existing `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, `metadata.json`, `pyproject.toml`) — direct read

### Secondary (MEDIUM confidence)
- [Caddy Community: best practice for healthchecks](https://caddy.community/t/what-is-the-best-practise-for-doing-a-health-check-for-caddy-containers/12995) — confirms curl/wget tradeoffs in Caddy images
- [Docker Compose healthchecks guide (Last9)](https://last9.io/blog/docker-compose-health-checks/) — corroborates official `start_period` semantics
- [docker/compose#11131](https://github.com/docker/compose/issues/11131) — confirmed `start_period` does not short-circuit early (Pitfall 1)
- [Docker bridge network driver](https://docs.docker.com/engine/network/drivers/bridge/) — confirms default Compose project network is user-defined bridge with DNS-by-name
- Python urllib.request healthcheck pattern — multiple corroborating community posts ([oneuptime](https://oneuptime.com/blog/post/2026-01-23-docker-health-checks-effectively/view), [muratcorlu](https://muratcorlu.com/docker-healthcheck-without-curl-or-wget/))

### Tertiary (LOW confidence — none used as load-bearing claims)
- General "FastAPI cold start" benchmarks — directional only, not cited as a hard number; the Phase-2 healthcheck `start_period: 10s` is generous regardless.

## Metadata

**Confidence breakdown:**
- Standard stack versions: **HIGH** — every version cross-verified against PyPI / Docker Hub registry on 2026-04-20
- Architecture (compose layout, Caddyfile, Dockerfile patterns): **HIGH** — derived from official docs, not training data
- Pitfalls (start_period, slim-image healthcheck, auto-HTTPS at localhost): **HIGH** — each pitfall traced to a specific upstream issue or doc
- Byte-parity recipe: **MEDIUM** — recipe shape is correct; the `jq` filter list (timestamps, version strings) may need expansion when first run reveals other volatile fields. Flagged as A8.
- Caddy admin-endpoint healthcheck path (`/metrics`): **MEDIUM** — Caddy docs imply enablement is needed; planner should verify before locking. Flagged as A2.

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 for versions; 2026-10-20 for patterns and pitfalls (Caddy + Compose patterns are very stable).
