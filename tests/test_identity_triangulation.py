from datetime import UTC, date, datetime

import httpx

from football_intelligence.identity_triangulation import triangulate_wyscout_candidates
from football_intelligence.providers.thesportsdb import SportsDBPlayer, TheSportsDBAdapter


class Cursor:
    def __init__(self, candidates):
        self.candidates = candidates
        self.rows = []
        self.rowcount = 0
        self.updates = 0

    def execute(self, query, _params=()):
        compact = " ".join(query.split())
        self.rows = []
        self.rowcount = 0
        if "FROM entity_resolution_candidate" in compact:
            self.rows = self.candidates
        elif "UPDATE entity_resolution_candidate" in compact:
            self.updates += 1
            self.rowcount = 1
        elif "INSERT INTO source_observation" in compact:
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
    def __init__(self, cursor):
        self.value = cursor

    def cursor(self):
        return Context(self.value)


def player(name="Exact Name", born=date(1990, 1, 2)):
    return SportsDBPlayer(
        player_id="third-1",
        name=name,
        team_name="Club",
        nationality="England",
        birth_date=born,
        status="Active",
        position="Midfielder",
        checked_at=datetime(2026, 9, 29, tzinfo=UTC),
        raw_without_artwork={"idPlayer": "third-1", "strPlayer": name},
    )


class Adapter(TheSportsDBAdapter):
    def __init__(self, rows=None, fail=False):
        self.rows = rows or []
        self.fail = fail

    def search_players(self, _name):
        if self.fail:
            request = httpx.Request("GET", "https://example.test")
            raise httpx.HTTPStatusError("blocked", request=request, response=httpx.Response(429))
        return self.rows


def test_exact_name_and_birth_adds_review_evidence_without_auto_merge(tmp_path):
    cursor = Cursor([(1, "provider-1", "exact name", "Exact Name", date(1990, 1, 2))])
    result = triangulate_wyscout_candidates(
        Connection(cursor),
        raw_root=tmp_path,
        minimum_interval_seconds=0,
        adapter=Adapter([player()]),
    )
    assert result.corroborated == 1
    assert cursor.updates == 1
    assert len(list(tmp_path.rglob("*.json"))) == 1


def test_missing_and_provider_failure_remain_unresolved(tmp_path):
    candidates = [(1, "a", "one", "One", None)]
    missing = triangulate_wyscout_candidates(
        Connection(Cursor(candidates)),
        raw_root=tmp_path,
        minimum_interval_seconds=0,
        adapter=Adapter([]),
    )
    failed = triangulate_wyscout_candidates(
        Connection(Cursor(candidates)),
        raw_root=tmp_path,
        minimum_interval_seconds=0,
        adapter=Adapter(fail=True),
    )
    assert missing.no_result == 1
    assert failed.provider_failures == 1
