import json

import pytest

from football_intelligence import backfill
from football_intelligence.backfill import run_backfill


def test_backfill_checkpoints_each_success_and_resumes(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    calls: list[int] = []
    first = run_backfill([1, 2], checkpoint_path=checkpoint, ingest_match=calls.append)
    second = run_backfill([1, 2, 3], checkpoint_path=checkpoint, ingest_match=calls.append)
    assert (first.succeeded, second.skipped, second.succeeded) == (2, 2, 1)
    assert calls == [1, 2, 3]
    assert json.loads(checkpoint.read_text())["completed"] == ["1", "2", "3"]


def test_backfill_persists_failure_and_can_retry(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"

    def fail_second(match_id: int) -> None:
        if match_id == 2:
            raise RuntimeError("provider unavailable")

    result = run_backfill([1, 2, 3], checkpoint_path=checkpoint, ingest_match=fail_second)
    assert result.failed == 1
    assert "RuntimeError" in result.failures["2"]
    retry = run_backfill([2], checkpoint_path=checkpoint, ingest_match=lambda _: None)
    assert retry.succeeded == 1
    assert retry.failures == {}


def test_backfill_rejects_duplicates_and_corrupt_checkpoint(tmp_path):
    with pytest.raises(ValueError, match="unique"):
        run_backfill([1, 1], checkpoint_path=tmp_path / "x", ingest_match=lambda _: None)
    bad = tmp_path / "bad.json"
    bad.write_text('{"completed": "not-a-list"}')
    with pytest.raises(ValueError, match="Invalid"):
        run_backfill([1], checkpoint_path=bad, ingest_match=lambda _: None)


def test_checkpoint_replace_retries_transient_windows_lock(tmp_path, monkeypatch):
    real_replace = backfill.os.replace
    attempts = 0

    def flaky_replace(source, target):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("temporarily locked")
        return real_replace(source, target)

    monkeypatch.setattr(backfill.os, "replace", flaky_replace)
    monkeypatch.setattr(backfill.time, "sleep", lambda _: None)
    result = run_backfill(
        [1], checkpoint_path=tmp_path / "checkpoint.json", ingest_match=lambda _: None
    )
    assert result.succeeded == 1
    assert attempts == 3
