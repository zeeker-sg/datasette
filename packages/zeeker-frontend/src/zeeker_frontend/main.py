"""Zeeker frontend (M2 Phase 4 scaffolding).

Lifespan-scoped httpx.AsyncClient for Datasette API access
(REQ-frontend-data-via-http / DEC-5). Jinja2Templates with the M1-ported
custom filters + helper globals registered. StaticFiles mount at /static.

This module boots the FastAPI app and wires the three dependencies every
route handler needs:
  - request.app.state.http — shared async HTTP client
  - templates — Jinja2Templates instance (with filters/globals)
  - DATASETTE_URL — configurable via env, defaults to the docker-compose service name

The `/` and `/{db}` route handlers are added in Plans 04-03 and 04-04. This
module intentionally keeps only /frontend-test at this plan boundary.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from zeeker_frontend import filters as zfilters

DATASETTE_URL = os.environ.get(
    "ZEEKER_DATASETTE_URL", "http://zeeker-datasette:8001"
)

_PKG_DIR = Path(__file__).parent
_TEMPLATES_DIR = _PKG_DIR / "templates"
_STATIC_DIR = _PKG_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connection pool sized for phase 4 traffic + room for phases 5-6.
    # Timeout rationale (RESEARCH §Pattern 1): internal docker bridge is <5ms;
    # 10s total with 2s connect covers an S3 cold-start on datasette.
    app.state.http = httpx.AsyncClient(
        base_url=DATASETTE_URL,
        timeout=httpx.Timeout(10.0, connect=2.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    try:
        yield
    finally:
        await app.state.http.aclose()


app = FastAPI(
    title="zeeker-frontend",
    description="FastAPI/Jinja frontend for data.zeeker.sg — M2 Phase 4.",
    version="0.4.0",
    lifespan=lifespan,
)

# Static asset mount. Caddy's suffix matcher forwards /static/*.css and
# /static/*.woff2 here because .css and .woff2 are NOT in the @datasette
# matcher (verified RESEARCH §Static-asset Routing).
_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Jinja environment. Starlette's Jinja2Templates auto-enables autoescape
# for .html/.htm/.xml — do NOT construct a raw jinja2.Environment
# (RESEARCH Pitfall 7).
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# Register M1-ported filters + helper globals so Jinja templates port
# without modification. See filters.py for the port notes.
templates.env.filters["filesizeformat"] = zfilters.filesizeformat
templates.env.filters["pluralize"] = zfilters.pluralize
templates.env.filters["safe_format"] = zfilters.safe_format
templates.env.globals["s"] = zfilters.s
templates.env.globals["plural"] = zfilters.plural

# Expose templates on app.state so route modules can render without importing
# `templates` directly (avoids circular imports once 04-04 adds its own router).
app.state.templates = templates

from zeeker_frontend.routes_home import router as home_router
app.include_router(home_router)


@app.get("/frontend-test")
def frontend_test() -> dict[str, str]:
    """Phase-2 healthcheck target (preserved).

    Returns JSON (not HTML) deliberately; used by docker healthcheck
    and by verify_phase_0{2,3}.sh as a frontend-reachability probe.
    """
    return {"status": "ok", "service": "zeeker-frontend"}
