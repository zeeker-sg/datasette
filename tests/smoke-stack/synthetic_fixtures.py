#!/usr/bin/env python3
"""
synthetic_fixtures.py — build the disposable smoke-stack fixture databases.

Two tiny SQLite databases that mirror the production schema *shape* (feed
table + content-linked FTS5) with only synthetic, safe content ("smoketest"
markers, nowhere near any real data).

Output layout (SMOKE_DATA_DIR):
  news.db   — sg-gov-newsrooms-shaped: mlaw_news (+ mlaw_news_fts
              content=[mlaw_news], sqlite-utils bracket-quoted content link —
              the form Datasette's FTS detection matches)
  laws.db   — sglawwatch-shaped: headlines (+ headlines_fts content=[headlines])
  metadata.json — root-level override injected by the smoke compose file
              (allow_sql owner-gated + strip-columns config identical to the
              repo metadata.json contract, rewritten for the fixture dbs)

Usage: uv run python tests/smoke-stack/synthetic_fixtures.py <target-dir>
"""

import json
import sqlite3
import sys
from pathlib import Path


NEWS_SCRIPT = """
CREATE TABLE mlaw_news (
    id INTEGER PRIMARY KEY,
    title TEXT,
    summary TEXT,
    content_text TEXT
);
INSERT INTO mlaw_news VALUES
    (1, 'Smoke test article one', 'Smoke summary one', 'SMOKETEST-BODY-ONE unique alpha'),
    (2, 'Smoke test article two', 'Smoke summary two', 'SMOKETEST-BODY-TWO unique beta');
CREATE VIRTUAL TABLE mlaw_news_fts USING fts5(
    title, content_text, content=[mlaw_news]
);
"""

NEWS_FTS_ROWS = [
    (1, 'Smoke test article one', 'SMOKETEST-BODY-ONE unique alpha'),
    (2, 'Smoke test article two', 'SMOKETEST-BODY-TWO unique beta'),
]

LAWS_SCRIPT = """
CREATE TABLE headlines (
    id INTEGER PRIMARY KEY,
    title TEXT,
    date TEXT
);
INSERT INTO headlines VALUES
    (1, 'Smoke test headline one', '2026-10-12'),
    (2, 'Smoke test headline two', '2026-10-12');
CREATE VIRTUAL TABLE headlines_fts USING fts5(title, content=[headlines]);
"""

LAWS_FTS_ROWS = [
    (1, 'Smoke test headline one'),
    (2, 'Smoke test headline two'),
]

# Root-level metadata override served to the datasette container. Contract
# identical to the repo metadata.json: owner-gated SQL + the strip-columns
# block, rewritten for the fixture dbs — so the smoke exercises the SAME
# catalogue-lockdown semantics prod runs.
METADATA_OVERRIDE = {
    "title": "data.zeeker.sg smoke",
    "allow_sql": {"id": "owner"},
    "plugins": {
        "strip-columns": {
            "default_deny_names": ["content_text"],
            "tables": {
                "news": {"mlaw_news": ["content_text"]},
            },
        }
    },
    "databases": {
        "news": {
            "title": "Smoke News",
            "tables": {
                "mlaw_news": {
                    "sort_desc": "id",
                    "title": "Smoke MLAW News",
                    "display": {
                        "table_mode": "feed",
                        "row_mode": "article",
                        "columns": {
                            "kicker": "id",
                            "title": "title",
                            "byline": "summary",
                            "body": "summary",
                            "date": "id",
                            "source_url": "id",
                        },
                    },
                }
            },
        },
        "laws": {"title": "Smoke Laws"},
    },
    "menu_links": [
        {"href": "/", "label": "Home"},
        {"href": "/how-to-use", "label": "Home"},
        {"href": "/status", "label": "Status"},
    ],
}


def _make_news_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(NEWS_SCRIPT)
    for rowid, title, content in NEWS_FTS_ROWS:
        conn.execute(
            "INSERT INTO mlaw_news_fts (rowid, title, content_text) VALUES (?, ?, ?)",
            (rowid, title, content),
        )
    conn.commit()
    conn.close()


def _make_laws_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(LAWS_SCRIPT)
    for rowid, title in LAWS_FTS_ROWS:
        conn.execute(
            "INSERT INTO headlines_fts (rowid, title) VALUES (?, ?)", (rowid, title)
        )
    conn.commit()
    conn.close()


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=True)
    _make_news_db(target / "news.db")
    _make_laws_db(target / "laws.db")
    (target / "metadata.json").write_text(json.dumps(METADATA_OVERRIDE, indent=2))
    print(f"fixtures written: {target}")


if __name__ == "__main__":
    main()