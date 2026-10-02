from types import SimpleNamespace

from football_intelligence.events import normalize_statsbomb_event
from football_intelligence.statsbomb_backfill import (
    backfill_statsbomb_season,
    write_season_result,
)


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query):
        return None

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self):
        self.commits = 0

    def cursor(self):
        return FakeCursor()

    def commit(self):
        self.commits += 1


class FakeAdapter:
    def fetch_matches(self, competition_id, season_id):
        return [{"match_id": 123}]

    def fetch_lineups(self, match_id):
        return [
            {
                "team_id": 4,
                "team_name": "Team",
                "lineup": [
                    {
                        "player_id": 5,
                        "player_name": "Player",
                        "player_nickname": None,
                        "country": {"name": "Country"},
                    }
                ],
            }
        ]


def test_statsbomb_database_backfill_is_resumable(tmp_path, monkeypatch):
    event = normalize_statsbomb_event(
        {
            "id": "event-1",
            "match_id": 123,
            "period": 1,
            "minute": 1,
            "second": 2,
            "type": {"name": "Pass"},
            "location": [20, 30],
            "team": {"id": 4},
            "player": {"id": 5},
        }
    )
    canonical = tmp_path / "canonical.jsonl"
    canonical.write_text(event.model_dump_json() + "\n", encoding="utf-8")
    monkeypatch.setattr(
        "football_intelligence.statsbomb_backfill.ingest_statsbomb_match",
        lambda *args, **kwargs: SimpleNamespace(canonical_object_uri=str(canonical)),
    )
    calls = []
    monkeypatch.setattr(
        "football_intelligence.statsbomb_backfill.load_statsbomb_match_metadata",
        lambda cursor, match: calls.append("metadata"),
    )
    monkeypatch.setattr(
        "football_intelligence.statsbomb_backfill.resolve_provider_players",
        lambda connection, players: calls.append("identities"),
    )
    monkeypatch.setattr(
        "football_intelligence.statsbomb_backfill.load_events",
        lambda cursor, events: calls.append(f"events:{len(events)}"),
    )
    monkeypatch.setattr(
        "football_intelligence.statsbomb_backfill.link_statsbomb_events",
        lambda cursor, match_id: calls.append("links"),
    )
    monkeypatch.setattr(
        "football_intelligence.statsbomb_backfill.write_report",
        lambda report, target: calls.append("report"),
    )
    connection = FakeConnection()
    checkpoint = tmp_path / "checkpoint.json"
    kwargs = dict(
        competition_id=9,
        season_id=281,
        raw_root=tmp_path / "raw",
        canonical_root=tmp_path / "events",
        report_root=tmp_path / "reports",
        checkpoint=checkpoint,
        adapter=FakeAdapter(),
    )
    first = backfill_statsbomb_season(connection, **kwargs)
    second = backfill_statsbomb_season(connection, **kwargs)
    assert first.matches_completed == 1
    assert second.matches_skipped == 1
    assert connection.commits == 1
    assert calls == ["metadata", "identities", "events:1", "links", "report"]

    report = tmp_path / "season.json"
    write_season_result(first, report)
    assert '"matches_completed": 1' in report.read_text(encoding="utf-8")
