import json

import httpx
import respx

from football_intelligence.ingestion import ingest_statsbomb_match
from football_intelligence.providers.statsbomb_open import EVENTS_URL


@respx.mock
def test_match_ingestion_preserves_raw_and_writes_canonical_jsonl(tmp_path):
    match_id = 123
    payload = [
        {
            "id": "a",
            "period": 1,
            "minute": 1,
            "second": 2,
            "type": {"name": "Shot"},
            "team": {"id": 10},
            "player": {"id": 20},
            "location": [100, 40],
            "shot": {"statsbomb_xg": 0.25, "end_location": [120, 40]},
        },
        {
            "id": "b",
            "period": 1,
            "minute": 1,
            "second": 5,
            "type": {"name": "Pressure"},
            "team": {"id": 11},
        },
        {
            "id": "outside-pitch",
            "period": 1,
            "minute": 2,
            "second": 0,
            "type": {"name": "Pass"},
            "team": {"id": 11},
            "location": [120.2, 79.5],
        },
    ]
    respx.get(EVENTS_URL.format(match_id=match_id)).mock(
        return_value=httpx.Response(200, json=payload)
    )
    report = ingest_statsbomb_match(
        match_id, raw_root=tmp_path / "raw", canonical_root=tmp_path / "canonical"
    )
    assert report.raw_event_count == 3
    assert report.canonical_event_count == 3
    assert report.quarantined_event_count == 0
    assert report.events_with_coordinates == 1
    assert report.events_with_xg == 1
    assert report.event_type_counts == {"Pass": 1, "Pressure": 1, "Shot": 1}
    canonical_lines = (
        (tmp_path / "canonical" / "statsbomb_match_123.jsonl").read_text().splitlines()
    )
    assert len(canonical_lines) == 3
    assert json.loads(canonical_lines[0])["provider_match_id"] == "123"
    outside = json.loads(canonical_lines[2])
    assert outside["normalized_x_m"] is None
    assert "outside statsbomb_120_80" in outside["qualifiers"]["coordinate_validation_errors"][0]
