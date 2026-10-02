from datetime import UTC, datetime

import pytest

from football_intelligence.database import EVENT_UPSERT, event_parameters, load_events
from football_intelligence.events import CanonicalEvent


class RecordingCursor:
    def __init__(self):
        self.query = ""
        self.rows = []

    def executemany(self, query, params_seq):
        self.query = query
        self.rows = list(params_seq)


def item(event_id="1", match_id="m1"):
    return CanonicalEvent(
        provider="statsbomb_open",
        provider_event_id=event_id,
        provider_match_id=match_id,
        provider_player_id="p1",
        provider_team_id="t1",
        period=1,
        minute=2,
        second=3.5,
        event_type="Pass",
        event_subtype=None,
        outcome=None,
        raw_x=60,
        raw_y=40,
        raw_end_x=80,
        raw_end_y=40,
        coordinate_system="statsbomb_120_80",
        normalized_x_m=52.5,
        normalized_y_m=34,
        normalized_end_x_m=70,
        normalized_end_y_m=34,
        shot_xg=None,
        qualifiers={"under_pressure": True},
    )


def test_event_parameters_preserve_provider_ids_and_json():
    values = event_parameters(item(), datetime(2026, 9, 28, tzinfo=UTC))
    assert values[0:5] == ("statsbomb_open", "1", "m1", "p1", "t1")
    assert values[21] == '{"under_pressure":true}'


def test_load_events_is_single_match_idempotent_upsert_contract():
    cursor = RecordingCursor()
    result = load_events(cursor, [item("1"), item("2")])
    assert result.attempted == 2
    assert cursor.query == EVENT_UPSERT
    assert "ON CONFLICT" in cursor.query
    assert len(cursor.rows) == 2


def test_load_events_rejects_mixed_matches():
    with pytest.raises(ValueError, match="one provider and one match"):
        load_events(RecordingCursor(), [item("1", "m1"), item("2", "m2")])


def test_load_events_accepts_empty_batch():
    assert load_events(RecordingCursor(), []).attempted == 0
