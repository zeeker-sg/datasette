"""Unit tests for the catalogue-posture helpers in datasette_client:

  - is_hidden_table / is_hidden_table_name — shared hidden predicate
  - protected_columns / is_protected_table — strip-columns config readers
  - compute_display_slots                  — server-side slot heuristic
  - safe_aside_columns                     — row-page short-value list
"""
from __future__ import annotations

from zeeker_frontend.datasette_client import (
    compute_display_slots,
    is_hidden_table,
    is_hidden_table_name,
    is_protected_table,
    protected_columns,
    safe_aside_columns,
)


SITE_METADATA = {
    "plugins": {
        "strip-columns": {
            "default_deny_names": ["content_text", "full_text", "html_raw", "footnote_text"],
            "tables": {
                "sglawwatch": {
                    "headlines": ["text"],
                    "about_singapore_law": ["content"],
                },
                "zeeker-judgements": {
                    "judgments": ["content_text"],
                    "judgments_fragments": ["content_text", "html_raw", "footnote_text"],
                },
                "pdpc": {"enforcement_decisions_fragments": ["text"]},
            },
        }
    }
}


class TestHiddenPredicate:
    def test_zeeker_prefix(self):
        assert is_hidden_table_name("_zeeker_schemas")
        assert is_hidden_table({"name": "_zeeker_updates", "hidden": False})

    def test_fts_anywhere_in_name(self):
        assert is_hidden_table_name("headlines_fts")
        assert is_hidden_table_name("headlines_fts_data")
        assert is_hidden_table_name("headlines_fts_view")

    def test_fragments_suffix(self):
        assert is_hidden_table_name("judgments_fragments")
        assert is_hidden_table({"name": "about_singapore_law_fragments", "hidden": False})

    def test_hidden_flag(self):
        # sglawwatch's `metadata` and `schema_versions` are caught via the
        # hidden flag set in site metadata (no name rule for them).
        assert is_hidden_table({"name": "metadata", "hidden": True})
        assert is_hidden_table({"name": "schema_versions", "hidden": True})
        assert not is_hidden_table({"name": "metadata", "hidden": False})

    def test_private_flag(self):
        assert is_hidden_table({"name": "secret_query", "private": True})

    def test_plain_table_visible(self):
        assert not is_hidden_table_name("headlines")
        assert not is_hidden_table({"name": "judgments", "hidden": False})


class TestProtectedColumns:
    def test_default_deny_names(self):
        cols = ["id", "title", "content_text", "summary"]
        assert protected_columns(SITE_METADATA, "any-db", "any_table", cols) == {"content_text"}

    def test_per_table_deny(self):
        cols = ["id", "title", "text", "summary"]
        assert protected_columns(SITE_METADATA, "sglawwatch", "headlines", cols) == {"text"}
        # `text` only protected where configured
        assert protected_columns(SITE_METADATA, "sglawwatch", "case_summaries", cols) == set()

    def test_db_key_case_insensitive(self):
        """Historic metadata used 'Zeeker-Judgements'; a casing mismatch must
        not disable protection (content measure)."""
        cols = ["id", "content_text", "summary"]
        assert "content_text" in protected_columns(
            SITE_METADATA, "Zeeker-Judgements", "judgments", cols
        )

    def test_is_protected_table(self):
        assert is_protected_table(SITE_METADATA, "sglawwatch", "headlines", ["id", "text"])
        assert not is_protected_table(
            SITE_METADATA, "sglawwatch", "about_singapore_law",
            ["id", "item_url", "title", "section"],  # live shape: no `content`
        )

    def test_empty_metadata_no_protection(self):
        assert protected_columns({}, "db", "t", ["a", "b"]) == set()


HEADLINE_ROWS = [
    {
        "id": "abc",
        "category": "Business Times",
        "title": "A headline",
        "source_link": "https://example.com/x",
        "author": "BT: Someone",
        "date": "2026-04-21T00:01:00",
        "summary": "A short summary.",
        "text": "FULL TEXT " * 50,
        "imported_on": "2026-04-21T05:01:09",
    }
]
HEADLINE_COLS = [
    "id", "category", "title", "source_link", "author", "date",
    "summary", "text", "imported_on",
]


class TestComputeDisplaySlots:
    def test_heuristic_headlines(self):
        slots = compute_display_slots(
            HEADLINE_COLS, HEADLINE_ROWS, ["id"], {"text"},
        )
        assert slots["title"] == "title"
        assert slots["body"] == "summary"
        assert slots["kicker"] == "category"
        assert slots["date"] == "date"
        assert slots["source_url"] == "source_link"

    def test_protected_override_dropped(self):
        """display.columns.body → protected column must be dropped and the
        heuristic must pick a summary-class column instead."""
        slots = compute_display_slots(
            HEADLINE_COLS, HEADLINE_ROWS, ["id"], {"text"},
            overrides={"body": "text", "title": "title"},
        )
        assert slots["body"] == "summary"
        assert slots["title"] == "title"

    def test_pk_never_a_slot(self):
        slots = compute_display_slots(
            ["id", "summary"], [{"id": "x", "summary": "s"}], ["id"], set(),
        )
        assert slots["title"] != "id"

    def test_sort_desc_date_shaped_wins(self):
        rows = [{"id": 1, "imported_on": "2026-04-21T05:01:09", "title": "t"}]
        slots = compute_display_slots(
            ["id", "imported_on", "title"], rows, ["id"], set(),
            table_meta={"sort_desc": "imported_on"},
        )
        assert slots["date"] == "imported_on"

    def test_source_url_requires_http_sample(self):
        rows = [{"id": 1, "title": "t", "link": "not-a-url"}]
        slots = compute_display_slots(["id", "title", "link"], rows, ["id"], set())
        assert slots["source_url"] is None

    def test_title_falls_back_to_first_short_text_col(self):
        rows = [{"rowid": 1, "blurb": "Short text value", "blob": "y" * 5000}]
        slots = compute_display_slots(["rowid", "blurb", "blob"], rows, [], set())
        assert slots["title"] == "blurb"

    def test_extra_override_slots_preserved(self):
        rows = [{"id": 1, "citation": "[2025] SGCA 12", "summary": "s"}]
        slots = compute_display_slots(
            ["id", "citation", "summary"], rows, ["id"], set(),
            overrides={"citation": "citation"},
        )
        assert slots["citation"] == "citation"


class TestSafeAsideColumns:
    def test_excludes_protected_even_when_short(self):
        row = {"id": "x", "text": "short but protected", "court": "CA"}
        cols = ["id", "text", "court"]
        assert safe_aside_columns(cols, row, {"text"}) == ["id", "court"]

    def test_excludes_long_values(self):
        row = {"id": "x", "notes": "y" * 250}
        assert safe_aside_columns(["id", "notes"], row, set()) == ["id"]

    def test_excludes_explicit(self):
        row = {"id": "x", "title": "t", "summary": "s"}
        assert safe_aside_columns(
            ["id", "title", "summary"], row, set(), exclude={"title", "summary"}
        ) == ["id"]

    def test_none_values_allowed(self):
        row = {"id": "x", "maybe": None}
        assert safe_aside_columns(["id", "maybe"], row, set()) == ["id", "maybe"]
