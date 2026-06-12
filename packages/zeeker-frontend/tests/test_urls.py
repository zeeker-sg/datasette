"""Unit tests for zeeker_frontend.urls.

Mirrors test_filters.py style — class-per-function, pure-function tests.
"""
from zeeker_frontend.urls import (
    path_with_added_args,
    path_with_replaced_args,
    path_with_removed_args,
    toggle_facet_value,
    clear_facet_value,
    export_url,
    tilde_encode,
    row_url,
)

# NOTE: set_sort tests were removed with the tabular table mode (catalogue
# posture). The function survives only as dead code pending the main.py:96
# Jinja-global deregistration owned by another workstream.


class TestPathWithAddedArgs:
    def test_add_to_empty_qs(self):
        assert path_with_added_args("/a/b", "", {"_size": "25"}) == "/a/b?_size=25"

    def test_preserve_existing_keys(self):
        r = path_with_added_args("/p", "x=1", {"y": "2"})
        assert "x=1" in r and "y=2" in r

    def test_none_value_deletes_key(self):
        r = path_with_added_args("/p", "_search=foo&x=1", {"_search": None})
        assert "_search" not in r and "x=1" in r

    def test_replaces_existing_key(self):
        # Adding an existing key replaces (not duplicates)
        r = path_with_added_args("/p", "_size=10", {"_size": "50"})
        assert r.count("_size") == 1 and "_size=50" in r

    def test_url_encodes_special_chars(self):
        r = path_with_added_args("/p", "", {"category": "Straits Times"})
        assert "Straits+Times" in r or "Straits%20Times" in r


class TestPathWithReplacedArgs:
    def test_replaces_only_specified_key(self):
        r = path_with_replaced_args("/p", "x=1&y=2", {"x": "9"})
        assert "x=9" in r and "y=2" in r and "x=1" not in r

    def test_preserves_when_not_present(self):
        r = path_with_replaced_args("/p", "y=2", {"x": "9"})
        assert "x=9" in r and "y=2" in r


class TestPathWithRemovedArgs:
    def test_removes_specified_keys(self):
        r = path_with_removed_args("/p", "_search=foo&_sort=col&x=1", {"_search", "_sort"})
        assert "_search" not in r and "_sort" not in r and "x=1" in r

    def test_returns_path_only_when_qs_empty(self):
        r = path_with_removed_args("/p", "x=1", {"x"})
        assert r == "/p"


class TestToggleFacetValue:
    def test_adds_when_absent(self):
        r = toggle_facet_value("/p", "", "category", "Straits Times")
        assert "category=Straits+Times" in r or "category=Straits%20Times" in r

    def test_removes_when_present(self):
        r = toggle_facet_value("/p", "category=Straits+Times", "category", "Straits Times")
        assert "category" not in r


class TestClearFacetValue:
    def test_removes_only_matching_pair(self):
        r = clear_facet_value("/p", "category=A&category=B", "category", "A")
        assert "category=B" in r and "category=A" not in r


class TestExportUrl:
    def test_with_qs(self):
        assert export_url("db", "tbl", "csv", "_size=10") == "/db/tbl.csv?_size=10"

    def test_empty_qs(self):
        assert export_url("db", "tbl", "json", "") == "/db/tbl.json"


class TestTildeEncode:
    def test_alphanumeric_passthrough(self):
        assert tilde_encode("abc123XYZ") == "abc123XYZ"

    def test_safe_chars_passthrough(self):
        assert tilde_encode("a-b._c") == "a-b._c"

    def test_slash_encoded(self):
        assert tilde_encode("a/b") == "a~2Fb"

    def test_space_encoded(self):
        assert tilde_encode("a b") == "a~20b"

    def test_percent_encoded(self):
        assert tilde_encode("a%b") == "a~25b"

    def test_unicode_byte_per_byte(self):
        # 'é' is 0xC3 0xA9 in UTF-8 -> ~C3~A9
        assert tilde_encode("é") == "~C3~A9"


class TestRowUrl:
    def test_single_pk(self):
        assert row_url("db", "tbl", ["abc123"]) == "/db/tbl/abc123"

    def test_compound_pk(self):
        assert row_url("db", "tbl", ["2026", "hello"]) == "/db/tbl/2026,hello"

    def test_compound_pk_tilde_encodes_each(self):
        # /world has '/' which must be tilde-encoded per Pitfall 5
        assert row_url("db", "tbl", ["2026", "hello/world"]) == "/db/tbl/2026,hello~2Fworld"

    def test_empty_pk_values_returns_none(self):
        # Pitfall 4: rowid-only tables; caller must fall back to row.rowid
        assert row_url("db", "tbl", []) is None

    def test_none_pk_values_returns_none(self):
        assert row_url("db", "tbl", None) is None

    def test_int_pk_coerces_to_str(self):
        assert row_url("db", "tbl", [42]) == "/db/tbl/42"
