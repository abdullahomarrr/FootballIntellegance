import json
import zipfile
from types import SimpleNamespace

from football_intelligence.wyscout_backfill import backfill_wyscout_country


class Cursor:
    def execute(self, query, parameters):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


class Connection:
    def cursor(self):
        return Cursor()


def test_country_backfill_reconciles_real_input_grains(tmp_path, monkeypatch):
    events_archive = tmp_path / "events.zip"
    matches_archive = tmp_path / "matches.zip"
    event = {
        "id": 1,
        "matchId": 10,
        "playerId": 20,
        "teamId": 30,
        "eventSec": 2.0,
        "eventName": "Pass",
        "subEventName": "Simple pass",
        "matchPeriod": "1H",
        "positions": [{"x": 10, "y": 20}, {"x": 30, "y": 40}],
        "tags": [],
    }
    invalid_event = {**event, "id": 2, "positions": [{"x": 28, "y": 101}]}
    with zipfile.ZipFile(events_archive, "w") as zipped:
        zipped.writestr("events_Test.json", json.dumps([event, invalid_event]))
    with zipfile.ZipFile(matches_archive, "w") as zipped:
        zipped.writestr("matches_Test.json", json.dumps([{"wyId": 10}]))
    players = tmp_path / "players.json"
    teams = tmp_path / "teams.json"
    competitions = tmp_path / "competitions.json"
    players.write_text(
        json.dumps([{"wyId": 20, "firstName": "Real", "lastName": "Player"}]),
        encoding="utf-8",
    )
    teams.write_text("[]", encoding="utf-8")
    competitions.write_text("[]", encoding="utf-8")

    monkeypatch.setattr("football_intelligence.wyscout_backfill.load_events", lambda *args: None)
    monkeypatch.setattr(
        "football_intelligence.wyscout_backfill.load_wyscout_match_metadata",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "football_intelligence.wyscout_backfill.resolve_provider_players",
        lambda *args, **kwargs: SimpleNamespace(
            seeded=1, auto_linked=0, review_candidates=0, existing=0
        ),
    )

    result = backfill_wyscout_country(
        Connection(),
        country="Test",
        events_archive=events_archive,
        matches_archive=matches_archive,
        players_path=players,
        teams_path=teams,
        competitions_path=competitions,
    )
    assert result.matches_loaded == 1
    assert result.events_loaded == 1
    assert result.events_quarantined == 1
    assert result.quarantine_reasons == {"NORMALIZATION_ERROR_VALUEERROR": 1}
    assert result.provider_players_seen == 1
    assert result.identities_seeded == 1
