import json
import zipfile
from pathlib import Path

import pytest

from football_intelligence.wyscout_ingestion import ingest_wyscout_match, read_json_member


def raw_event(event_id: int, match_id: int) -> dict:
    return {
        "id": event_id,
        "matchId": match_id,
        "playerId": 4,
        "teamId": 5,
        "matchPeriod": "1H",
        "eventSec": 12.0,
        "eventName": "Pass",
        "subEventName": "Simple pass",
        "positions": [{"x": 10, "y": 20}, {"x": 30, "y": 20}],
        "tags": [],
    }


def archive(path, member, payload):
    with zipfile.ZipFile(path, "w") as zipped:
        zipped.writestr(member, json.dumps(payload))


def test_wyscout_match_ingestion_reconciles_raw_and_canonical(tmp_path):
    source = tmp_path / "events.zip"
    archive(source, "events_England.json", [raw_event(1, 10), raw_event(2, 11)])
    report = ingest_wyscout_match(
        10,
        country="England",
        events_archive=source,
        raw_root=tmp_path / "raw",
        canonical_root=tmp_path / "canonical",
    )
    assert report.raw_event_count == report.canonical_event_count == 1
    assert report.quarantined_event_count == 0
    assert Path(report.canonical_object_uri).exists()


def test_zip_member_reader_rejects_missing_or_unsafe_member(tmp_path):
    source = tmp_path / "events.zip"
    archive(source, "events_England.json", [])
    with pytest.raises(ValueError, match="unsafe"):
        read_json_member(source, "../events_England.json")
    with pytest.raises(ValueError, match="No Wyscout events"):
        ingest_wyscout_match(
            10,
            country="England",
            events_archive=source,
            raw_root=tmp_path / "raw",
            canonical_root=tmp_path / "canonical",
        )
