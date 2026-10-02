from football_intelligence.events import normalize_statsbomb_event, normalize_wyscout_event


def test_statsbomb_pass_preserves_raw_and_normalizes_coordinates():
    event = normalize_statsbomb_event(
        {
            "id": "event-1",
            "match_id": 12,
            "period": 1,
            "minute": 3,
            "second": 4.5,
            "type": {"name": "Pass"},
            "team": {"id": 1},
            "player": {"id": 2},
            "location": [60, 40],
            "pass": {"end_location": [120, 80], "outcome": {"name": "Incomplete"}},
            "unexpected": "preserved",
        }
    )
    assert event.normalized_x_m == 52.5
    assert event.normalized_end_x_m == 105
    assert event.outcome == "Incomplete"
    assert event.qualifiers == {"unexpected": "preserved"}


def test_wyscout_event_keeps_tags_and_null_end_location():
    event = normalize_wyscout_event(
        {
            "id": 7,
            "matchId": 8,
            "playerId": 0,
            "teamId": 9,
            "matchPeriod": "1H",
            "eventSec": 61.5,
            "eventName": "Duel",
            "subEventName": "Ground duel",
            "positions": [{"x": 50, "y": 50}],
            "tags": [{"id": 1801}],
        }
    )
    assert event.minute == 1
    assert event.second == 1.5
    assert event.provider_player_id is None
    assert event.normalized_end_x_m is None
    assert event.qualifiers == {"tags": [{"id": 1801}]}
