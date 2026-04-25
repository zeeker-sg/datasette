"""GET /{db}/{table} — table browse page.

Plan 05-01 stubs the router with the hidden-table guard at the route
boundary (RESEARCH Pitfall 6 / threat T-05-03). Plan 05-02 fills in
fetch_table, metadata merge, next_url rewrite, and the TemplateResponse
rendering of table.html.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

# T-05-03 mitigation — both prefix AND suffix per RESEARCH Pitfall 6.
_HIDDEN_TABLE_PREFIXES = ("_zeeker",)
_HIDDEN_TABLE_SUFFIXES = (
    "_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config",
)


@router.get("/{db}/{table}", response_class=HTMLResponse)
async def table_page(request: Request, db: str, table: str):
    # Block hidden tables at the route boundary — same 404 wording so
    # missing vs. hidden cannot be distinguished by the response.
    if table.startswith(_HIDDEN_TABLE_PREFIXES) or table.endswith(_HIDDEN_TABLE_SUFFIXES):
        raise HTTPException(status_code=404, detail="Table not found")
    # Plan 05-02 replaces this with the real handler body.
    raise HTTPException(status_code=501, detail="Not implemented — Plan 05-02 fills this in")
