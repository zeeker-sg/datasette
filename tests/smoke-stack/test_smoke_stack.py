"""Unit and integration tests for the smoke-stack tooling.

These run WITHOUT Docker (fast, CI-friendly). They cover:
  - synthetic fixture generation is valid, safe, and mirrors prod shape
  - generated metadata preserves the lockdown contract (owner-gated SQL,
    strip-columns config) while the broken variant provably does NOT
  - smoke_checks helper behavior (failure collection, exit path)
  - the end-to-end regression gate itself (run_regressions.sh), opt-in via
    SMOKE_STACK_DOCKER=1 — skipped silently in CI where Docker is limited
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from synthetic_fixtures import METADATA_OVERRIDE, main as fixtures_main  # noqa: E402

SMOKE_DIR = Path(__file__).parent


# ------------------------------------------------------------- fixtures


def _generate_strict(tmp_path):
    from synthetic_fixtures import _make_laws_db, _make_news_db

    _make_news_db(tmp_path / "news.db")
    _make_laws_db(tmp_path / "laws.db")
    (tmp_path / "metadata.json").write_text(json.dumps(METADATA_OVERRIDE, indent=2))


@pytest.fixture
def fixtures(tmp_path):
    _generate_strict(tmp_path)
    return tmp_path


class TestSyntheticFixtures:
    def test_writes_both_dbs_and_metadata(self, fixtures):
        assert (fixtures / "news.db").exists()
        assert (fixtures / "laws.db").exists()
        assert (fixtures / "metadata.json").exists()

    def test_news_db_shape(self, fixtures):
        import sqlite3

        conn = sqlite3.connect(str(fixtures / "news.db"))
        cols = [r[1] for r in conn.execute("PRAGMA table_info(mlaw_news)")]
        assert cols == ["id", "title", "summary", "content_text"]
        # protected column holds the ONLY SMOKETEST marker on these rows
        for summary, in conn.execute("SELECT summary FROM mlaw_news"):
            assert "SMOKETEST-BODY" not in summary  # summary is NOT protected
        conn.close()

    def test_metadata_preserves_lockdown_contract(self, fixtures):
        meta = json.loads((fixtures / "metadata.json").read_text())
        assert meta["allow_sql"] == {"id": "owner"}
        strip = meta["plugins"]["strip-columns"]
        assert "content_text" in strip["default_deny_names"]
        assert strip["tables"]["news"]["mlaw_news"] == ["content_text"]

    def test_fixture_values_are_synthetic(self, fixtures):
        """No fixture value should look like real production data."""
        import sqlite3

        for db in ("news.db", "laws.db"):
            conn = sqlite3.connect(str(fixtures / db))
            for (title,) in conn.execute("SELECT title FROM mlaw_news" if db == "news.db" else "SELECT title FROM headlines"):
                assert "smoke test" in title.lower()
            conn.close()

    def test_broken_metadata_disables_protection(self):
        """The regression-scenario variant is DIFFERENT from the good config —
        this is what makes the regression gate meaningful."""
        broken = json.loads((SMOKE_DIR / "fixtures" / "broken-metadata.json").read_text())
        good = METADATA_OVERRIDE
        assert broken["plugins"]["strip-columns"]["default_deny_names"] == []
        assert broken["plugins"]["strip-columns"]["tables"] == {}
        assert good["plugins"]["strip-columns"]["default_deny_names"] != []


# ------------------------------------------------------------ smoke_checks


class TestSmokeChecksHelpers:
    def test_module_imports_clean(self):
        import smoke_checks

        assert callable(smoke_checks.run_checks)
        assert isinstance(smoke_checks.BASE, str)
        assert smoke_checks.BASE.startswith("http")

    def test_expect_collects_failures(self):
        import smoke_checks

        smoke_checks.FAILS.clear()
        smoke_checks.expect("always-true", True)
        assert smoke_checks.FAILS == []
        smoke_checks.expect("always-false", False, "detail-here")
        assert smoke_checks.FAILS == ["always-false"]
        smoke_checks.FAILS.clear()


# ------------------------------------------- end-to-end regression gate


@pytest.mark.skipif(
    os.environ.get("SMOKE_STACK_DOCKER") != "1",
    reason="needs Docker daemon + host port 8891; run locally with SMOKE_STACK_DOCKER=1",
)
class TestEndToEndRegressionGate:
    """Runs run_regressions.sh against the pinned prod images — the same run
    smoke_stack.sh performs — proving the smoke gate catches a silently-broken
    strip-columns lockdown."""

    @staticmethod
    def _images():
        return (
            os.environ.get(
                "SMOKE_DATASETTE_IMAGE",
                "ghcr.io/zeeker-sg/zeeker-datasette:sha-b2c15805bb43cd44c52f1ab853843b4e6a3236ca",
            ),
            os.environ.get(
                "SMOKE_FRONTEND_IMAGE",
                "ghcr.io/zeeker-sg/zeeker-frontend:sha-b2c15805bb43cd44c52f1ab853843b4e6a3236ca",
            ),
        )

    def test_regression_gate_catches_broken_protection(self):
        script = SMOKE_DIR / "run_regressions.sh"
        ds_image, fe_image = self._images()
        result = subprocess.run(
            ["bash", str(script), ds_image, fe_image],
            capture_output=True,
            text=True,
            timeout=580,
        )
        assert result.returncode == 0, f"regression gate failed:\n{result.stdout}\n{result.stderr}"
        assert "REGRESSIONS-PASSED" in result.stdout