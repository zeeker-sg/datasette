#!/usr/bin/env python3
"""
Regression tests for the S3 ETag-race retry (fix/s3-download-etag-retry).

Production incident: the 6-hourly zeeker-judgements build deploys its ~3 GB
database to latest/ at :07, and the :10 datasette refresh downloads it with
s3transfer's ranged reader. When the deploy lands mid-download, the provider
answers a later ranged GET's If-Match check with 412 PreconditionFailed and
the whole download — previously the whole 3-hourly refresh slot — is lost
with "did not match expected ETag" (3 occurrences Oct 28-29, always on the
judgements DB, always in a slot touching a :07 build deploy).

The retry contract under test:
  - an ETag race is retried with growing backoff (30s, 60s, ...);
  - any other error is re-raised on its first attempt (nothing masked);
  - after max_attempts the original error propagates to the caller.
"""

import logging
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from s3transfer.exceptions import S3DownloadFailedError

from scripts import manage
from scripts.download_from_s3 import (
    download_file_with_etag_retry,
    is_etag_race_error,
)

ETAG_ERR = (
    'Contents of stored object "latest/zeeker-judgements.db" in bucket '
    '"zeeker" did not match expected ETag.'
)


def etag_download_error():
    """The s3transfer-side failure surface (raised out of s3.download_file)."""
    return S3DownloadFailedError(ETAG_ERR)


def precondition_client_error():
    """The raw provider-side failure surface (412 PreconditionFailed)."""
    return ClientError(
        {"Error": {"Code": "PreconditionFailed", "Message": ETAG_ERR}},
        "GetObject",
    )


class TestIsEtagRaceError:
    def test_s3transfer_download_failed_error(self):
        assert is_etag_race_error(etag_download_error()) is True

    def test_precondition_failed_client_error(self):
        assert is_etag_race_error(precondition_client_error()) is True

    def test_generic_errors_are_not_etag_race(self):
        assert is_etag_race_error(Exception("boom")) is False

    def test_slow_down_is_not_etag_race(self):
        slow = ClientError(
            {"Error": {"Code": "SlowDown", "Message": "please reduce your rate"}},
            "ListObjectsV2",
        )
        assert is_etag_race_error(slow) is False


class TestDownloadFileWithEtagRetry:
    def test_recovers_after_one_race(self):
        client = Mock()
        client.download_file.side_effect = [etag_download_error(), None]

        with patch("scripts.download_from_s3.time.sleep") as mock_sleep:
            download_file_with_etag_retry(
                client, "test-bucket", "latest/x.db", "/tmp/never-written.x.db"
            )

        assert client.download_file.call_count == 2
        mock_sleep.assert_called_once_with(30.0)

    def test_backoff_grows_and_gives_up_after_max_attempts(self):
        client = Mock()
        client.download_file.side_effect = etag_download_error()

        with patch("scripts.download_from_s3.time.sleep") as mock_sleep:
            with pytest.raises(S3DownloadFailedError):
                download_file_with_etag_retry(
                    client,
                    "test-bucket",
                    "latest/x.db",
                    "/tmp/never-written.x.db",
                    max_attempts=3,
                )

        assert client.download_file.call_count == 3
        assert [c.args[0] for c in mock_sleep.call_args_list] == [30.0, 60.0]

    def test_non_etag_error_fails_immediately_without_retry(self):
        client = Mock()
        client.download_file.side_effect = ClientError(
            {"Error": {"Code": "SlowDown", "Message": "please reduce your rate"}},
            "ListObjectsV2",
        )

        with patch("scripts.download_from_s3.time.sleep") as mock_sleep:
            with pytest.raises(ClientError):
                download_file_with_etag_retry(
                    client, "test-bucket", "latest/x.db", "/tmp/never-written.x.db"
                )

        assert client.download_file.call_count == 1
        mock_sleep.assert_not_called()


class TestRefreshDownloadLoop:
    """The refresh slot self-heals when a build deploy races the reader.

    These drive manage.download_from_s3_to_dir — the code the 3-hourly
    host cron refresh actually runs — against fake S3 clients only.
    """

    def _fake_s3(self, download_side_effect):
        s3 = Mock()
        paginator = Mock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "latest/zeeker-judgements.db"}]}
        ]
        s3.get_paginator.return_value = paginator
        s3.download_file.side_effect = download_side_effect
        return s3

    @pytest.fixture
    def refresh_env(self, monkeypatch):
        monkeypatch.setenv("S3_BUCKET", "test-bucket")

    def test_refresh_recovers_from_etag_race(self, refresh_env, tmp_path):
        s3 = self._fake_s3([etag_download_error(), None])

        with patch.object(manage, "get_s3_client", return_value=s3):
            with patch("scripts.download_from_s3.time.sleep") as mock_sleep:
                ok = manage.download_from_s3_to_dir(
                    tmp_path, logging.getLogger("test-refresh")
                )

        assert ok is True
        # One aborted ranged download + one successful re-download
        assert s3.download_file.call_count == 2
        mock_sleep.assert_called_once_with(30.0)

    def test_refresh_fails_loudly_when_race_persists(self, refresh_env, tmp_path):
        s3 = self._fake_s3(etag_download_error())

        with patch.object(manage, "get_s3_client", return_value=s3):
            with patch("scripts.download_from_s3.time.sleep") as mock_sleep:
                ok = manage.download_from_s3_to_dir(
                    tmp_path, logging.getLogger("test-refresh")
                )

        # The download wrapper still reports failure → refresh aborts as
        # before (the caller-level shell retry in the cron scripts covers
        # slot-level self-healing when even the in-place retries exhaust).
        assert ok is False
        assert s3.download_file.call_count == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2

    def test_refresh_fails_immediately_on_unrelated_error(self, refresh_env, tmp_path):
        s3 = self._fake_s3(
            ClientError(
                {"Error": {"Code": "SlowDown", "Message": "please reduce your rate"}},
                "ListObjectsV2",
            )
        )

        with patch.object(manage, "get_s3_client", return_value=s3):
            with patch("scripts.download_from_s3.time.sleep") as mock_sleep:
                ok = manage.download_from_s3_to_dir(
                    tmp_path, logging.getLogger("test-refresh")
                )

        assert ok is False
        assert s3.download_file.call_count == 1
        mock_sleep.assert_not_called()