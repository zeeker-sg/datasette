"""Unit tests for zeeker_frontend.filters."""
from jinja2 import Undefined

from zeeker_frontend.filters import (
    filesizeformat, pluralize, safe_format, s, plural,
)


class TestFilesizeformat:
    def test_none_returns_dash(self):
        assert filesizeformat(None) == "—"

    def test_undefined_returns_dash(self):
        assert filesizeformat(Undefined()) == "—"

    def test_zero_bytes(self):
        assert filesizeformat(0) == "0 bytes"

    def test_small_bytes(self):
        assert filesizeformat(512) == "512 bytes"

    def test_kilobytes(self):
        assert filesizeformat(2048) == "2.0 KB"

    def test_megabytes(self):
        # 24666112 bytes = 23.52 MB
        out = filesizeformat(24_666_112)
        assert "MB" in out
        assert out.startswith("23.")

    def test_non_numeric_string_returns_str(self):
        assert filesizeformat("not a number") == "not a number"


class TestPluralize:
    def test_one_with_default_s(self):
        assert pluralize(1) == ""

    def test_two_with_default_s(self):
        assert pluralize(2) == "s"

    def test_one_with_ies_y(self):
        assert pluralize(1, "ies,y") == "y"

    def test_two_with_ies_y(self):
        assert pluralize(2, "ies,y") == "ies"

    def test_none(self):
        assert pluralize(None) == "s"  # n=0 → plural form


class TestSafeFormat:
    def test_int(self):
        assert safe_format(1234) == "1,234"

    def test_none(self):
        assert safe_format(None) == "—"

    def test_str_digit(self):
        assert safe_format("1234") == "1,234"

    def test_undefined(self):
        assert safe_format(Undefined()) == "—"


class TestS:
    def test_returns_default(self):
        assert s("any_key", "default text") == "default text"

    def test_empty_default(self):
        assert s("any_key") == ""


class TestPlural:
    def test_one_database(self):
        assert plural(1, "plural_database", "plural_databases") == "database"

    def test_two_databases(self):
        assert plural(2, "plural_database", "plural_databases") == "databases"

    def test_zero_databases(self):
        assert plural(0, "plural_database", "plural_databases") == "databases"

    def test_unknown_key_fallback(self):
        # Unknown key pair → strip plural_ prefix + naive +s
        assert plural(1, "plural_foo", "plural_foos") == "foo"
        assert plural(3, "plural_foo", "plural_foos") == "foos"
