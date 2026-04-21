"""Jinja custom filters + helpers for the zeeker-frontend Jinja environment.

Ports M1's plugins/template_filters.py (filesizeformat, pluralize, safe_format)
and stubs plugins/string_manager.py's s() + plural() helpers so M1 templates
render 1:1 without requiring strings.yaml. Per RESEARCH (Jinja binding port
map §"Net result" + Pitfall 5): every s() call in phase-4 templates has a
literal default argument, so the stub returning `default` is behavior-preserving.
If Phase 6 needs real i18n, swap in a YAML-backed implementation later.
"""
from jinja2 import Undefined


# Plural mapping mirrors strings.yaml keys used in phase-4 templates.
# If a key isn't here, we fall back to "pluralize" default behavior.
_PLURALS = {
    ("plural_database", "plural_databases"): ("database", "databases"),
    ("plural_table", "plural_tables"): ("table", "tables"),
    ("plural_row", "plural_rows"): ("row", "rows"),
    ("plural_column", "plural_columns"): ("column", "columns"),
}


def filesizeformat(value) -> str:
    """Bytes → human-readable (matches M1 behavior exactly)."""
    if isinstance(value, Undefined) or value is None:
        return "—"
    try:
        b = float(value)
    except (ValueError, TypeError):
        return str(value)
    if b < 1024:
        return f"{b:.0f} bytes"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:
        return f"{b / (1024 ** 2):.1f} MB"
    return f"{b / (1024 ** 3):.1f} GB"


def pluralize(value, arg: str = "s") -> str:
    """{{ count }} item{{ count|pluralize }} — M1 port."""
    try:
        n = int(value) if value is not None else 0
    except (ValueError, TypeError):
        n = 0
    if "," not in str(arg):
        return "" if n == 1 else str(arg)
    plural_suffix, singular_suffix = str(arg).split(",", 1)
    return singular_suffix.strip() if n == 1 else plural_suffix.strip()


def safe_format(value, format_string: str = "{:,}") -> str:
    """Safely format numbers, returning '—' on undefined/failure."""
    if isinstance(value, Undefined) or value is None:
        return "—"
    try:
        if isinstance(value, str):
            value = int(value) if value.isdigit() else float(value)
        return format_string.format(value)
    except (ValueError, TypeError):
        return str(value) if not isinstance(value, Undefined) else "—"


def s(key: str, default: str = "") -> str:
    """String lookup — stub; returns default (no strings.yaml in frontend).

    M1's templates always pass a literal default, so this preserves
    rendered output 1:1. See RESEARCH Pitfall 5.
    """
    return default


def plural(n, singular_key: str, plural_key: str) -> str:
    """String-key-based pluralizer — M1 string_manager port.

    Matches M1's {{ plural(count, 'plural_database', 'plural_databases') }} call
    sites. Falls back to naive singular/plural derivation if the key pair is
    unknown.
    """
    try:
        count = int(n) if n is not None else 0
    except (ValueError, TypeError):
        count = 0
    mapping = _PLURALS.get((singular_key, plural_key))
    if mapping:
        singular, plural_word = mapping
        return singular if count == 1 else plural_word
    # Fallback: strip "plural_" prefix and pluralize the stem.
    stem = singular_key.removeprefix("plural_")
    return stem if count == 1 else (stem + "s")
