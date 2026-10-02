from datetime import UTC, date, datetime

from football_intelligence.openfootball_backfill import backfill_openfootball
from football_intelligence.openfootball_loader import load_openfootball_dataset
from football_intelligence.providers.openfootball import (
    OpenFootballAdapter,
    OpenFootballDataset,
    OpenFootballFixture,
    OpenFootballScore,
)


def dataset() -> OpenFootballDataset:
    observed = datetime(2026, 9, 29, tzinfo=UTC)
    return OpenFootballDataset(
        name="Test League 2026/27",
        competition_code="xx.1",
        season="2026-27",
        source_url="https://example.test/xx.1.json",
        checked_at=observed,
        raw_payload={"name": "Test League", "matches": []},
        fixtures=[
            OpenFootballFixture(
                provider_match_key="2026-27:xx.1:2026-09-29:Home:Away",
                competition_code="xx.1",
                season="2026-27",
                match_date=date(2026, 9, 29),
                home_team="Home",
                away_team="Away",
                score=OpenFootballScore(full_time=(2, 1)),
                status="FINISHED",
                source_url="https://example.test/xx.1.json",
                data_as_of=observed,
            )
        ],
    )


class FakeCursor:
    def __init__(self, existing: bool = False) -> None:
        self.existing = existing
        self.current = None
        self.rows = []
        self.rowcount = 0
        self.next_id = 10
        self.queries: list[str] = []

    def execute(self, query, params=()):
        compact = " ".join(query.split())
        self.queries.append(compact)
        self.current, self.rows, self.rowcount = None, [], 0
        if "RETURNING season_id" in compact:
            self.current = (1,)
        elif "SELECT competition_id FROM bridge_competition_provider" in compact:
            self.current = (2,) if self.existing else None
        elif "RETURNING competition_id" in compact:
            self.current = (2,)
        elif "SELECT team_id FROM bridge_team_provider" in compact:
            if self.existing:
                self.current = (3 if params[0] == "home" else 4,)
        elif "SELECT team_id FROM dim_team" in compact:
            self.rows = []
        elif "RETURNING team_id" in compact:
            self.current = (self.next_id,)
            self.next_id += 1
        elif "SELECT match_id FROM bridge_match_provider" in compact:
            self.current = (5,) if self.existing else None
        elif "RETURNING match_id" in compact:
            self.current = (5,)
        elif "INSERT INTO source_observation" in compact:
            self.rowcount = 0 if self.existing else 1

    def fetchone(self):
        return self.current

    def fetchall(self):
        return self.rows


class CursorContext:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self.value = cursor

    def cursor(self):
        return CursorContext(self.value)


class FakeAdapter(OpenFootballAdapter):
    def __init__(self, value):
        self.value = value

    def fetch_competition(self, season, competition_code):
        assert season == "2026-27"
        assert competition_code == "xx.1"
        return self.value


def test_loader_inserts_new_provider_entities_and_stable_observation():
    cursor = FakeCursor()
    result = load_openfootball_dataset(cursor, dataset(), raw_object_uri="raw/object.json")
    assert result.matches_inserted == 1
    assert result.matches_updated == 0
    assert result.observations_inserted == 1
    observation = next(query for query in cursor.queries if "source_observation" in query)
    assert "ON CONFLICT DO NOTHING" in observation


def test_loader_updates_existing_match_without_duplicating_observation():
    result = load_openfootball_dataset(
        FakeCursor(existing=True), dataset(), raw_object_uri="raw/object.json"
    )
    assert result.matches_inserted == 0
    assert result.matches_updated == 1
    assert result.observations_inserted == 0


def test_backfill_writes_raw_snapshot_and_aggregates_result(tmp_path):
    value = dataset()
    result = backfill_openfootball(
        FakeConnection(FakeCursor()),
        season="2026-27",
        competition_codes=["xx.1"],
        raw_root=tmp_path,
        adapter=FakeAdapter(value),
    )
    assert result.fixtures_seen == 1
    assert result.matches_inserted == 1
    raw_files = list(tmp_path.rglob("*.json"))
    assert len(raw_files) == 1
    assert '"matches":[]' in raw_files[0].read_text(encoding="utf-8")
