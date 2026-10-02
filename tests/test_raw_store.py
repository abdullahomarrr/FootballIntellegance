from datetime import UTC, datetime

import pytest

from football_intelligence.raw_store import FileRawStore


def test_raw_write_is_deterministic_and_verified(tmp_path):
    store = FileRawStore(tmp_path)
    now = datetime(2026, 9, 27, tzinfo=UTC)
    arguments = dict(
        provider="statsbomb/open",
        endpoint="competitions",
        parameters={"b": 2, "a": 1},
        payload={"name": "João", "id": 7},
        pipeline_run_id="run-1",
        ingested_at=now,
    )
    first = store.write_json(**arguments)
    second = store.write_json(**arguments)
    assert first.object_uri == second.object_uri
    assert first.checksum_sha256 == second.checksum_sha256
    assert store.read_verified(first) == {"id": 7, "name": "João"}


def test_raw_read_rejects_corruption(tmp_path):
    store = FileRawStore(tmp_path)
    manifest = store.write_json(
        provider="test",
        endpoint="events",
        parameters={},
        payload=[1, 2],
        pipeline_run_id="run-1",
    )
    (tmp_path / manifest.object_uri).write_text("corrupt", encoding="utf-8")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        store.read_verified(manifest)
