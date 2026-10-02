import json
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from football_intelligence import laliga, laliga_routes
from football_intelligence.api import app


def line(pid, name, team, position, minutes, **stats):
    base = {
        "minutes": minutes, "goals": 0, "assists": 0, "shots_total": 0, "shots_on": 0,
        "passes_key": 0, "passes_total": 0, "pass_accuracy": 0, "dribbles_success": 0,
        "tackles_total": 0, "interceptions": 0, "duels_won": 0, "yellow_cards": 0,
        "red_cards": 0, "saves": 0, "rating": 7.0, "substitute": "false",
    }
    base.update(stats)
    return {
        "id": pid, "name": name, "team_name": team, "position": position,
        "stats": {key: {"value": str(value)} for key, value in base.items()},
    }


def two_matches():
    first = [
        line("a", "Striker One", "Barcelona", "Attacker", 90, goals=2, shots_total=5,
             passes_total=60, pass_accuracy=45, rating=9.0),
        line("b", "Striker Two", "Barcelona", "Attacker", 90, goals=0, shots_total=1,
             passes_total=40, pass_accuracy=30, rating=6.0),
        line("k", "Keeper One", "Barcelona", "Goalkeeper", 90, saves=4, passes_total=30,
             pass_accuracy=20),
        line("x", "Unused Sub", "Barcelona", "Attacker", 0),
    ]
    second = [
        line("a", "Striker One", "Barcelona", "Attacker", 30, goals=1, substitute="true",
             passes_total=50, pass_accuracy=40, rating=8.0),
        line("b", "Striker Two", "Barcelona", "Attacker", 90, goals=1, shots_total=4,
             passes_total=60, pass_accuracy=50, rating=7.0),
        line("k", "Keeper One", "Barcelona", "Goalkeeper", 90, saves=2),
    ]
    return [first, second]


def test_totals_are_summed_and_zero_minute_players_ignored():
    snapshot = laliga.build_snapshot(two_matches(), rounds=2, season_start=2026)
    by_id = {p["id"]: p for p in snapshot.players}
    assert "x" not in by_id
    one = by_id["a"]
    assert one["minutes"] == 120 and one["goals"] == 3 and one["appearances"] == 2
    assert one["starts"] == 1  # the second appearance was off the bench
    assert one["pass_completion"] == pytest.approx(85 / 110 * 100, abs=0.1)
    assert one["average_rating"] == pytest.approx((9.0 * 90 + 8.0 * 30) / 120, abs=0.01)
    assert snapshot.season_label == "2026-27" and snapshot.matches == 2


def test_rankings_are_per_position_and_respect_the_minutes_floor():
    snapshot = laliga.build_snapshot(two_matches(), rounds=2, season_start=2026)
    by_id = {p["id"]: p for p in snapshot.players}
    assert snapshot.minimum_minutes == 90
    assert by_id["a"]["rankings"]["goals_per_90"]["percentile"] == 100.0
    assert by_id["b"]["rankings"]["goals_per_90"]["percentile"] == 0.0
    assert "saves_per_90" in by_id["k"]["rankings"]
    assert "goals_per_90" not in by_id["k"]["rankings"]  # keepers use their own metric set
    assert by_id["a"]["rankings"]["goals_per_90"]["cohort_size"] == 2
    # pass completion needs 100+ passes before it is ranked
    assert by_id["k"]["metrics"]["pass_completion"] is None


def test_short_samples_are_not_ranked():
    snapshot = laliga.build_snapshot(two_matches(), rounds=10, season_start=2026)
    assert snapshot.minimum_minutes == 360
    assert all(p["rankings"] == {} for p in snapshot.players)


def test_season_start_follows_the_calendar():
    assert laliga.current_season_start(date(2026, 10, 1)) == 2026
    assert laliga.current_season_start(date(2027, 3, 1)) == 2026
    assert laliga.current_season_start(date(2026, 8, 1)) == 2026


def test_club_check_requires_every_team_word_in_the_contract_club():
    assert laliga._same_club("FC Barcelona", "Barcelona")
    assert laliga._same_club("Club Atlético de Madrid", "Atlético Madrid")
    assert not laliga._same_club("Real Madrid", "Barcelona")
    assert not laliga._same_club("", "Barcelona")


def test_rounds_played_uses_the_busiest_team():
    listing = [
        {"home": {"id": "t1"}, "away": {"id": "t2"}},
        {"home": {"id": "t1"}, "away": {"id": "t3"}},
        {"home": {}, "away": None},
    ]
    assert laliga._rounds_played(listing) == 2


def test_finished_matches_are_cached_and_page_through_results(tmp_path, monkeypatch):
    monkeypatch.setattr(laliga, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.setattr(laliga, "REQUEST_SPACING_SECONDS", 0.0)
    laliga._memory.clear()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["offset"])
        size = 100 if request.url.params["offset"] == "0" else 5
        return httpx.Response(200, json={"data": [{"id": str(i)} for i in range(size)]})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=laliga.BASE_URL)
    assert len(laliga.finished_matches(2026, client)) == 105
    assert len(laliga.finished_matches(2026, client)) == 105
    assert calls == ["0", "100"]  # two pages, then served from cache
    laliga._memory.clear()


def test_match_lines_are_cached_forever(tmp_path, monkeypatch):
    monkeypatch.setattr(laliga, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.setattr(laliga, "REQUEST_SPACING_SECONDS", 0.0)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"data": {"players": [{"id": "a"}]}})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=laliga.BASE_URL)
    assert laliga.match_player_lines("m1", client) == [{"id": "a"}]
    assert laliga.match_player_lines("m1", client) == [{"id": "a"}]
    assert len(calls) == 1
    assert json.loads((tmp_path / "matches" / "m1.json").read_text()) == [{"id": "a"}]


def test_missing_key_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(laliga, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.delenv("BIGBALLS_API_KEY", raising=False)
    with pytest.raises(laliga.MissingApiKey):
        laliga.match_player_lines("never-cached-match-id")


@pytest.fixture
def fake_feed(monkeypatch):
    snapshot = laliga.build_snapshot(two_matches(), rounds=2, season_start=2026)
    links = {"a": (777, "NAME_AND_CLUB")}
    monkeypatch.setattr(laliga_routes, "current_snapshot", lambda: (snapshot, links))
    return snapshot


def test_search_and_detail_routes(fake_feed):
    client = TestClient(app)
    rows = client.get("/laliga/players", params={"search": "striker"}).json()["data"]
    assert [r["id"] for r in rows] == ["b", "a"]  # most minutes first (180 vs 120)
    assert rows[1]["event_profile_player_id"] == 777 and rows[0]["event_profile_player_id"] is None
    assert client.get("/laliga/players", params={"search": ""}).json()["data"] == []
    detail = client.get("/laliga/players/a").json()
    assert detail["data"]["goals"] == 3 and detail["data"]["link_basis"] == "NAME_AND_CLUB"
    assert "no event locations" in detail["meta"]["source_note"]
    assert detail["meta"]["season"] == "2026-27"
    assert client.get("/laliga/players/nope").status_code == 404


def test_outage_and_missing_key_are_reported(monkeypatch):
    def down():
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(laliga_routes, "current_snapshot", down)
    assert TestClient(app).get("/laliga/players", params={"search": "x"}).status_code == 503

    def unconfigured():
        raise laliga.MissingApiKey("no key")

    monkeypatch.setattr(laliga_routes, "current_snapshot", unconfigured)
    response = TestClient(app).get("/laliga/players/a")
    assert response.status_code == 503 and "not configured" in response.json()["detail"]


def test_players_listed_at_a_club_outside_the_league_are_kept_but_marked_unclear():
    lines = [
        [
            line("a", "Striker One", "Barcelona", "Attacker", 90),
            line("m", "Moved Player", "Arsenal", "Attacker", 90, goals=1),
            line("n", "No Club", None, "Attacker", 90),
        ]
    ]
    snapshot = laliga.build_snapshot(lines, 1, 2026, {"Barcelona", "Real Madrid"})
    by_id = {p["id"]: p for p in snapshot.players}
    assert by_id["a"]["team"] == "Barcelona" and not by_id["a"]["club_unclear"]
    assert by_id["m"]["team"] == laliga.UNCLEAR_CLUB and by_id["m"]["feed_club"] == "Arsenal"
    assert by_id["m"]["goals"] == 1  # the La Liga minutes still count
    assert by_id["n"]["club_unclear"]


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query):
        pass

    def fetchall(self):
        return self.rows


def test_links_need_a_unique_name_and_a_matching_club():
    rows = [
        (1, "Lamine Yamal Nasraoui Ebana", None, "FC Barcelona"),
        (2, "Pedri Gonzalez Lopez", "Pedri", "FC Barcelona"),
        (3, "Sergio Gomez Martin", None, "Real Sociedad"),
        (4, "Sergio Gomez Ruiz", None, "Real Sociedad"),
        (5, "Joao Cancelo", None, "Manchester City"),
        (6, "Old Timer", None, None),
    ]
    players = [
        {"id": "y", "name": "Lamine Yamal", "team": "Barcelona"},  # words fit one Barcelona player
        {"id": "g", "name": "Sergio Gomez", "team": "Real Sociedad"},  # two fit, so ambiguous
        {"id": "c", "name": "Joao Cancelo", "team": "Barcelona"},  # right name, wrong club
        {"id": "o", "name": "Old Timer", "team": "Barcelona"},  # no contract club on record
        {"id": "u", "name": "Lost Player", "team": laliga.UNCLEAR_CLUB, "club_unclear": True},
        {"id": "p", "name": "Pedri", "team": "Barcelona"},  # too short to match
    ]
    links = laliga.link_players(FakeConnection(rows), players)
    assert links == {"y": (1, "NAME_WORDS_AND_CLUB")}
