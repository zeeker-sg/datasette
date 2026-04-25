"""GET /{db}/{table}/{pk} — single row view.

Plan 05-01 stubs the router with the hidden-table guard. Plan 05-03 fills
in fetch_row + row.html rendering with mode dispatch.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

_HIDDEN_TABLE_PREFIXES = ("_zeeker",)
_HIDDEN_TABLE_SUFFIXES = (
    "_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config",
)


@router.get("/{db}/{table}/{pk}", response_class=HTMLResponse)
async def row_page(request: Request, db: str, table: str, pk: str):
    if table.startswith(_HIDDEN_TABLE_PREFIXES) or table.endswith(_HIDDEN_TABLE_SUFFIXES):
        raise HTTPException(status_code=404, detail="Table not found")
    raise HTTPException(status_code=501, detail="Not implemented — Plan 05-03 fills this in")
