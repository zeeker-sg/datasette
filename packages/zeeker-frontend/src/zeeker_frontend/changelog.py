"""Changelog loader — reads data/changelog.yaml at lifespan boot.

Phase 6 (D-12). Replaces the M1 plugins/strings.yaml `recent_updates:`
block; the YAML lives inside the package (data/changelog.yaml) so Phase 7
deletion of plugins/strings.yaml stays safe.

Used once at lifespan boot from main.py — load_changelog() returns a
list[dict] which is stashed on app.state.changelog and read by
routes_aux /status without further file I/O.

Safety: yaml.safe_load ONLY (RESEARCH §Don't Hand-Roll + threat
T-06-02-05). Bare `except Exception` is intentional — we want the
/status page to degrade to "No updates yet" rather than crash the
lifespan if a malformed YAML edit lands on disk.
"""
from __future__ import annotations

from pathlib import Path

import yaml


_DATA_DIR = Path(__file__).parent / "data"


def load_changelog() -> list[dict]:
    """Return list of {date, type, title, description} dicts.

    - Empty list on missing file.
    - Empty list on YAML parse failure (defensive — lifespan must boot).
    - Filters out entries that are not dicts OR are missing the `date` key.
    """
    p = _DATA_DIR / "changelog.yaml"
    if not p.exists():
        return []
    try:
        doc = yaml.safe_load(p.read_text()) or {}
        items = doc.get("recent_updates") or []
        valid = [i for i in items if isinstance(i, dict) and "date" in i]
        # Sort by date desc — ISO-8601 strings sort lexically, so str(date) suffices
        # whether YAML parsed the field as a date or kept it as a string.
        return sorted(valid, key=lambda i: str(i["date"]), reverse=True)
    except Exception:
        return []
