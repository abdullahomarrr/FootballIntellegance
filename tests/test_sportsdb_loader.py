from datetime import UTC, date, datetime

from football_intelligence.providers.thesportsdb import SportsDBEvent, TheSportsDBAdapter
from football_intelligence.sportsdb_loader import ingest_sportsdb_day, load_sportsdb_events


def event(home_score=2, away_score=1):
    return SportsDBEvent(
        event_id="99",
        name="Home vs Away",
        league_id="1",
        league_name="Test League",
        season="2026-27",
        home_team="Home",
        away_team="Away",
        date="2026-09-29",
        time="19:00:00",
        status="Match Finished",
        home_score=home_score,
        away_score=away_score,
        checked_at=datetime(2026, 9, 29, tzinfo=UTC),
        raw={"idEvent": "99", "strHomeTeam": "Home", "strAwayTeam": "Away"},
    )


class FakeCursor:
    def __init__(self, candidates=None, duplicate=False):
        self.candidates = candidates or []
        self.duplicate = duplicate
        self.rows = []
        self.rowcount = 0

    def execute(self, query, _params=()):
        compact = " ".join(query.split())
        self.rows = []
        self.rowcount = 0
        if "INSERT INTO source_observation" in compact:
            self.rowcount = 0 if self.duplicate else 1
        elif "SELECT m.match_id" in compact:
            self.rows = self.candidates
        elif "INSERT INTO source_conflict" in compact:
            self.rowcount = 1

    def fetchall(self):
        return self.rows


class Context:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, *_args):
        return False


class Connection:
    def __init__(self, value):
        self.value = value

    def cursor(self):
        return Context(self.value)


class Adapter(TheSportsDBAdapter):
    def __init__(self, rows):
        self.rows = rows

    def events_by_day(self, day, sport="Soccer"):
        assert day == "2026-09-29"
        assert sport == "Soccer"
        return self.rows


def test_secondary_event_corroborates_exact_match_and_preserves_equal_score():
    result = load_sportsdb_events(
        FakeCursor(candidates=[(7, 2, 1)]), [event()], raw_object_uri="raw/day.json"
    )
    assert result.observations_inserted == 1
    assert result.matches_corroborated == 1
    assert result.score_conflicts == 0


def test_secondary_event_records_score_conflict_without_overwriting_canonical():
    result = load_sportsdb_events(
        FakeCursor(candidates=[(7, 0, 0)]), [event()], raw_object_uri="raw/day.json"
    )
    assert result.score_conflicts == 1


def test_day_ingestion_is_raw_backed_and_reports_unmatched_event(tmp_path):
    result = ingest_sportsdb_day(
        Connection(FakeCursor()),
        day=date(2026, 9, 29),
        raw_root=tmp_path,
        adapter=Adapter([event(None, None)]),
    )
    assert result.events_seen == 1
    assert result.matches_corroborated == 0
    assert len(list(tmp_path.rglob("*.json"))) == 1
