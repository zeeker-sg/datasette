"""Zeeker frontend (placeholder).

This is the M2 Phase 2 placeholder. It exposes only /frontend-test so the
container has something to healthcheck against. Real HTML routes arrive in
Phases 4–6.

Deliberately does NOT import or touch SQLite (DEC-5 / REQ-frontend-data-via-http).
All future data access will go via httpx → http://zeeker-datasette:8001/...json.
"""
from fastapi import FastAPI

app = FastAPI(
    title="zeeker-frontend",
    description="Placeholder — see .planning/ROADMAP.md M2 Phases 4-6 for real routes.",
    version="0.1.0",
)


@app.get("/frontend-test")
def frontend_test() -> dict[str, str]:
    """Healthcheck / liveness probe target.

    Returns JSON (not HTML) deliberately: this phase intentionally avoids
    template work so we don't pay rendering costs in M2 Phase 2.
    """
    return {"status": "ok", "service": "zeeker-frontend"}
