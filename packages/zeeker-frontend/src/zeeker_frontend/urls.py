"""Querystring helpers + tilde-encoded row URL builder.

Direct ports of datasette/utils/__init__.py:268-331 (path_with_*_args) and
:1173-1186 (tilde_encode). Pure functions; no I/O.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode


def path_with_added_args(path: str, query_string: str, args) -> str:
    """Add (and replace) keys in `args`. None values delete the key.

    `args` may be a dict or a list of (key, value) pairs.
    """
    if isinstance(args, dict):
        args = list(args.items())
    args_to_remove = {k for k, v in args if v is None}
    keys_being_added = {k for k, v in args if v is not None}
    current = [
        (k, v) for k, v in parse_qsl(query_string)
        if k not in args_to_remove and k not in keys_being_added
    ]
    current.extend([(k, v) for k, v in args if v is not None])
    qs = urlencode(current)
    return f"{path}?{qs}" if qs else path


def path_with_replaced_args(path: str, query_string: str, args) -> str:
    """Replace specific keys, preserving everything else."""
    if isinstance(args, dict):
        args = list(args.items())
    keys = {k for k, _ in args}
    current = [(k, v) for k, v in parse_qsl(query_string) if k not in keys]
    current.extend([(k, v) for k, v in args if v is not None])
    qs = urlencode(current)
    return f"{path}?{qs}" if qs else path


def path_with_removed_args(path: str, query_string: str, keys) -> str:
    keys = set(keys)
    current = [(k, v) for k, v in parse_qsl(query_string) if k not in keys]
    qs = urlencode(current)
    return f"{path}?{qs}" if qs else path


def toggle_facet_value(path: str, qs: str, col: str, val: str) -> str:
    """If (col, val) already in qs, remove it; else add it."""
    present = any(k == col and v == val for k, v in parse_qsl(qs))
    if present:
        current = [(k, v) for k, v in parse_qsl(qs) if not (k == col and v == val)]
        new_qs = urlencode(current)
        return f"{path}?{new_qs}" if new_qs else path
    return path_with_added_args(path, qs, [(col, val)])


def clear_facet_value(path: str, qs: str, col: str, val: str) -> str:
    """Always remove (col, val) — used by × chip."""
    current = [(k, v) for k, v in parse_qsl(qs) if not (k == col and v == val)]
    new_qs = urlencode(current)
    return f"{path}?{new_qs}" if new_qs else path


def export_url(db: str, table: str, ext: str, query_string: str) -> str:
    """Build /{db}/{table}.{ext}?{qs} — Caddy @datasette intercepts.

    D-05 LOCKED: never proxy CSV/JSON through frontend; this is a plain anchor href.
    """
    base = f"/{db}/{table}.{ext}"
    return f"{base}?{query_string}" if query_string else base


def tilde_encode(s: str) -> str:
    """Port of datasette.utils.tilde_encode (utils/__init__.py:1173-1186).

    Hex-encodes any byte outside SAFE with `~XX`. Used for URL path
    segments where '/' would otherwise be misinterpreted.
    """
    SAFE = set(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._")
    out = []
    for byte in s.encode("utf-8"):
        if byte in SAFE:
            out.append(chr(byte))
        else:
            out.append(f"~{byte:02X}")
    return "".join(out)


def row_url(db: str, table: str, pk_values) -> str | None:
    """Build /{db}/{table}/{pk1},{pk2},... with tilde-encoded segments.

    Returns None when pk_values is empty (caller should fall back to rowid;
    Pitfall 4 in RESEARCH).
    """
    pk_values = list(pk_values) if pk_values else []
    if not pk_values:
        return None
    encoded = ",".join(tilde_encode(str(v)) for v in pk_values)
    return f"/{db}/{table}/{encoded}"
