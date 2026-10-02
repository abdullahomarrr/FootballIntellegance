import csv
import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from football_intelligence import fpl, fpl_routes, reep
from football_intelligence.api import app


def element(code, element_type, first, last, **overrides):
    base = {
        "code": code,
        "id": code - 1000,
        "element_type": element_type,
        "first_name": first,
        "second_name": last,
        "web_name": last,
        "known_name": "",
        "team": 1,
        "birth_date": "2000-07-21",
        "minutes": 450,
        "starts": 5,
        "goals_scored": 5,
        "assists": 1,
        "expected_goals": "4.42",
        "expected_assists": "0.53",
        "expected_goal_involvements": "4.95",
        "expected_goals_conceded": "5.0",
        "yellow_cards": 0,
        "red_cards": 0,
        "clean_sheets": 2,
        "saves": 10,
        "goals_conceded": 4,
        "tackles": 3,
        "recoveries": 10,
        "clearances_blocks_interceptions": 4,
        "defensive_contribution": 12,
        "now_cost": 156,
        "selected_by_percent": "60.1",
        "form": "8.0",
        "status": "a",
        "news": "",
        "news_added": None,
        "chance_of_playing_next_round": None,
    }
    return {**base, **overrides}


def bootstrap():
    forwards = [
        element(2000 + i, 4, "F", f"Forward{i}", goals_scored=i, minutes=450)
        for i in range(1, 6)
    ]
    keepers = [
        element(3000 + i, 1, "G", f"Keeper{i}", goals_conceded=i, minutes=450) for i in range(1, 4)
    ]
    star = element(
        1, 4, "Erling", "Haaland", goals_scored=9, news="Knock", status="d",
        chance_of_playing_next_round=75,
    )
    bench = element(2, 4, "Bench", "Player", minutes=20, goals_scored=2)
    return {
        "teams": [{"id": 1, "name": "Man City"}],
        "events": [
            {"id": 1, "finished": True},
            {"id": 2, "finished": True},
            {"id": 3, "finished": False},
        ],
        "elements": [star, bench, *forwards, *keepers],
    }


def test_snapshot_ranks_players_per_position_with_a_minutes_floor():
    snapshot = fpl.build_snapshot(bootstrap())
    assert snapshot.gameweek == 2 and snapshot.minimum_minutes == 90
    star = next(p for p in snapshot.players if p["web_name"] == "Haaland")
    assert star["position_group"] == "FW" and star["age"] is not None
    assert star["rankings"]["goals_per_90"]["percentile"] == 100.0
    assert star["rankings"]["goals_per_90"]["cohort_size"] == 6  # bench player excluded
    bench = next(p for p in snapshot.players if p["web_name"] == "Player")
    assert bench["rankings"] == {}  # too few minutes to be ranked
    assert star["status_label"] == "Doubtful" and star["chance_of_playing"] == 75


def test_goalkeepers_use_their_own_metrics_and_lower_conceded_is_better():
    snapshot = fpl.build_snapshot(bootstrap())
    keepers = sorted(
        (p for p in snapshot.players if p["position_group"] == "GK"), key=lambda p: p["web_name"]
    )
    assert "goals_conceded_per_90" in keepers[0]["rankings"]
    assert "goals_per_90" not in keepers[0]["rankings"]
    assert keepers[0]["rankings"]["goals_conceded_per_90"]["percentile"] == 100.0
    assert keepers[-1]["rankings"]["goals_conceded_per_90"]["percentile"] == 0.0


def test_age_and_percentile_edge_cases():
    assert fpl.age_on("2000-07-21", date(2026, 7, 20)) == 25
    assert fpl.age_on("2000-07-21", date(2026, 7, 21)) == 26
    assert fpl.age_on(None) is None and fpl.age_on("garbage") is None
    assert fpl._percentile(5, [5], True) == 50.0
    assert fpl._percentile(5, [1, 5, 9], True) == 50.0


def test_season_and_gameweek_tables_are_parsed_safely():
    summary = {
        "history_past": [
            {"season_name": "2024/25", "minutes": 2700, "goals_scored": 22, "assists": 3,
             "expected_goals": "21.9", "expected_assists": "0", "clean_sheets": 10,
             "total_points": 200}
        ],
        "history": [
            {"round": 1, "minutes": 90, "goals_scored": 2, "assists": 0, "expected_goals": "1.2",
             "expected_assists": "0.1", "was_home": True, "opponent_team": 7}
        ],
    }
    assert fpl.season_table(summary)[0]["expected_goals"] == 21.9
    assert fpl.season_table(summary)[0]["expected_assists"] is None
    assert fpl.gameweek_table(summary)[0]["expected_goals"] == 1.2
    assert fpl.season_table({}) == [] and fpl.gameweek_table({}) == []


def test_requests_are_cached_and_identify_the_client(tmp_path, monkeypatch):
    monkeypatch.setattr(fpl, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.setattr(fpl, "_last_request", 0.0)
    fpl.clear_cache()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers.get("user-agent"))
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fpl.fetch_bootstrap(client) == {"ok": True}
    assert fpl.fetch_bootstrap(client) == {"ok": True}
    assert len(calls) == 1  # second call is served from cache
    assert (tmp_path / "bootstrap.json").is_file()
    fpl.clear_cache()
    assert fpl.fetch_bootstrap(client) == {"ok": True}  # disk cache survives a restart
    assert len(calls) == 1
    fpl.clear_cache()


@pytest.fixture
def fake_feed(monkeypatch):
    snapshot = fpl.build_snapshot(bootstrap())
    links = {1: (777, "ID_CROSSWALK_WYSCOUT")}
    monkeypatch.setattr(fpl_routes, "current_snapshot", lambda: (snapshot, links))
    return snapshot


def test_search_returns_current_players_and_flags_event_profiles(fake_feed):
    payload = TestClient(app).get("/fpl/players", params={"search": "erling haaland"}).json()
    assert payload["data"][0]["name"] == "Erling Haaland"
    assert payload["data"][0]["event_profile_player_id"] == 777
    assert "no stated licence" in payload["meta"]["source_note"]
    assert TestClient(app).get("/fpl/players", params={"search": ""}).json()["data"] == []


def test_player_detail_includes_rankings_availability_and_history(fake_feed, monkeypatch):
    monkeypatch.setattr(fpl, "fetch_summary", lambda element_id: {})
    payload = TestClient(app).get("/fpl/players/1").json()
    data = payload["data"]
    assert data["status_label"] == "Doubtful" and data["chance_of_playing"] == 75
    assert data["rankings"]["goals_per_90"]["percentile"] == 100.0
    assert data["link_basis"] == "ID_CROSSWALK_WYSCOUT"
    assert payload["meta"]["gameweek"] == 2
    assert TestClient(app).get("/fpl/players/424242").status_code == 404


def test_feed_outage_is_reported_not_hidden(monkeypatch):
    def down():
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(fpl_routes, "current_snapshot", down)
    assert TestClient(app).get("/fpl/players", params={"search": "x"}).status_code == 503


def test_availability_uses_the_linked_feed_record(fake_feed, monkeypatch):
    monkeypatch.setattr(fpl_routes, "person_member_ids", lambda player_id: [player_id])
    monkeypatch.setattr(fpl_routes, "_query_all", lambda query, parameters: [{"fpl_code": 1}])
    payload = TestClient(app).get("/players/777/availability").json()
    assert payload["data"]["news"] == "Knock" and payload["data"]["chance_of_playing"] == 75
    monkeypatch.setattr(fpl_routes, "_query_all", lambda query, parameters: [])
    unlinked = TestClient(app).get("/players/778/availability").json()
    assert unlinked["data"] is None
    assert unlinked["meta"]["status"] == "NOT_IN_CURRENT_PREMIER_LEAGUE_FEED"


def test_reep_loader_keeps_only_players_with_usable_ids(tmp_path: Path):
    path = tmp_path / "people.csv"
    columns = ["reep_id", "type", "name", "date_of_birth", "key_opta_numeric",
               "key_wyscout", "key_transfermarkt"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        blank = dict.fromkeys(columns, "")
        for row in (
            {"reep_id": "a", "type": "player", "date_of_birth": "2000-07-21",
             "key_opta_numeric": "154561", "key_transfermarkt": "418560"},
            {"reep_id": "b", "type": "player", "date_of_birth": "bad", "key_wyscout": "123"},
            {"reep_id": "c", "type": "player", "key_transfermarkt": "9"},
            {"reep_id": "d", "type": "coach", "key_opta_numeric": "5"},
        ):
            writer.writerow({**blank, **row})
    rows = reep.read_crosswalk(path)
    assert [row[0] for row in rows] == ["a", "b"]
    assert rows[0][2] == 418560 and rows[0][5] == date(2000, 7, 21)
    assert rows[1][5] is None  # an unparseable birth date is dropped, not guessed
    assert json.dumps(rows[0][1]) == '"154561"'
