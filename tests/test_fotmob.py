import json
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from football_intelligence import alternatives, fotmob, squad_routes
from football_intelligence.api import app


def page(props: dict) -> str:
    data = {"props": {"pageProps": props}}
    script = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'
    return f"<html>{script}</html>"


def league_page() -> str:
    table = [{"id": 1, "name": "Club One"}, {"id": 2, "name": "Club Two"}]
    return page(
        {
            "details": {"id": 47, "selectedSeason": "2026/2027"},
            "table": [{"data": {"table": {"all": table}}}],
        }
    )


def member(pid, name, **extra):
    base = {
        "id": pid, "name": name, "shirtNumber": 7, "ccode": "ENG", "cname": "England",
        "role": {"fallback": "Midfielder"}, "positionIdsDesc": "CM", "injured": False,
        "rating": 6.9, "goals": 1, "assists": 2, "height": 180, "age": 24,
        "dateOfBirth": "2002-05-04T00:00:00.000Z", "transferValue": 25_000_000,
    }
    return {**base, **extra}


def squad_page(team_id=1) -> str:
    squad = [
        {"title": "coach", "members": [member(99, "The Coach")]},
        {"title": "keepers", "members": [member(10, "Keeper One")]},
        {
            "title": "midfielders",
            "members": [
                member(11, "Mid One", injured=True, injury={"expectedReturn": "Doubtful"}),
                member(12, "Mid Two", rating=None),
            ],
        },
    ]
    fallback = {f"team-{team_id}": {"details": {"name": "Club One"}, "squad": {"squad": squad}}}
    return page({"fallback": fallback})


def stat(key, per90, title=None):
    return {
        "localizedTitleId": key, "title": title or key, "statValue": str(per90),
        "per90": per90, "percentileRank": 50, "percentileRankPer90": 60,
    }


def player_page(pid=11, name="Mid One", minutes=400, values=None, family="midfielders") -> str:
    values = values or {f"stat{i}": float(i) for i in range(12)}
    raw = {
        "id": pid, "name": name, "birthDate": {"utcTime": "2002-05-04T00:00:00.000Z"},
        "contractEnd": {"utcTime": "2029-06-30T00:00:00.000Z"},
        "primaryTeam": {"teamId": 1, "teamName": "Club One", "onLoan": False},
        "positionDescription": {
            "positions": [
                {"strPos": {"label": "Central Midfielder"}, "strPosShort": {"label": "CM"},
                 "isMainPosition": True, "occurences": 9}
            ]
        },
        "playerInformation": [
            {"translationKey": "height_sentencecase", "value": {"fallback": "182 cm"}},
            {"translationKey": "preferred_foot", "value": {"fallback": "Right"}},
        ],
        "injuryInformation": None,
        "mainLeague": {
            "leagueId": 47, "leagueName": "Premier League", "season": "2026/2027",
            "stats": [{"title": "Minutes played", "value": minutes}],
        },
        "traits": {"key": f"stats_comparison_{family}", "title": "Compared", "items": []},
        "firstSeasonStats": {
            "statsSection": {
                "items": [{"title": "Passing", "items": [stat(k, v) for k, v in values.items()]}]
            },
            "heatmap": {"coordinates": [{"x": 50.123, "y": 30.987}]},
            "shotmap": [
                {"x": 90, "y": 30, "min": 12, "expectedGoals": 0.3, "eventType": "Goal",
                 "situation": "OpenPlay", "isOnTarget": True}
            ],
        },
        "marketValues": {"values": [{"date": "2025-01-01T00:00:00+00:00", "value": 30_000_000}]},
    }
    return page({"fallback": {f"player:{pid}": raw}})


# ------------------------------------------------------------------ parsing


def test_league_and_squad_pages_are_parsed():
    league = fotmob.parse_league_teams(league_page())
    assert league["league_id"] == 47 and league["season"] == "2026/2027"
    assert [t["team_id"] for t in league["teams"]] == [1, 2]
    squad = fotmob.parse_squad(squad_page(), 1)
    assert squad["name"] == "Club One"
    assert [m["player_id"] for m in squad["members"]] == [10, 11, 12]  # coach excluded
    mid = squad["members"][1]
    assert mid["position_group"] == "MD" and mid["injured"] and mid["injury_return"] == "Doubtful"
    assert mid["birth_date"] == "2002-05-04" and mid["market_value_eur"] == 25_000_000
    assert squad["members"][2]["rating"] is None  # has not played


def test_pages_without_the_expected_data_raise():
    with pytest.raises(fotmob.FotmobError):
        fotmob.parse_squad(page({"fallback": {}}), 1)
    with pytest.raises(fotmob.FotmobError):
        fotmob.parse_player(page({"fallback": {"player:5": None}}), 5)
    with pytest.raises(fotmob.FotmobError):
        fotmob.parse_league_teams("<html>no data</html>")


def test_player_page_is_compacted():
    player = fotmob.parse_player(player_page(), 11)
    assert player["name"] == "Mid One" and player["team"] == "Club One"
    assert player["foot"] == "Right" and player["height"] == "182 cm"
    assert player["league"]["stats"]["Minutes played"] == 400
    assert player["positions"][0]["main"] and player["contract_end"] == "2029-06-30"
    assert player["heatmap"] == [[50.1, 31.0]]
    assert player["shots"][0]["xg"] == 0.3 and player["shots"][0]["type"] == "Goal"
    assert len(player["stats"]) == 12 and player["market_values"][0]["value"] == 30_000_000


# ------------------------------------------------------------------ fetching and caching


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(fotmob, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.setattr(fotmob, "REQUEST_SPACING_SECONDS", 0.0)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert "FootballIntelligencePortfolio" in request.headers["user-agent"]
        if "/leagues/" in request.url.path:
            return httpx.Response(200, text=league_page())
        if "/teams/" in request.url.path:
            return httpx.Response(200, text=squad_page(int(request.url.path.split("/")[2])))
        return httpx.Response(200, text=player_page(int(request.url.path.split("/")[2])))

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url=fotmob.BASE_URL,
        headers={"User-Agent": fotmob.USER_AGENT},
    )
    return client, calls


def test_pages_are_fetched_once_and_cached_on_disk(isolated):
    client, calls = isolated
    assert fotmob.fetch_squad(1, client)["name"] == "Club One"
    assert fotmob.fetch_squad(1, client)["name"] == "Club One"
    assert fotmob.fetch_player(11, client)["name"] == "Mid One"
    assert fotmob.fetch_player(11, client)["name"] == "Mid One"
    assert fotmob.fetch_league_teams(47, client)["league_name"] == "Premier League"
    assert fotmob.fetch_league_teams(47, client)["teams"][0]["name"] == "Club One"
    assert len(calls) == 3  # one request each for squad, player and league


class FakeCursor:
    def __init__(self, row_sets):
        self.row_sets = row_sets
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split())[:40], params))

    def executemany(self, query, rows):
        self.executed.append((" ".join(query.split())[:40], list(rows)))

    def fetchall(self):
        return self.row_sets.pop(0) if self.row_sets else []


class FakeConnection:
    """Each fetchall() hands back the next prepared result set."""

    def __init__(self, *row_sets):
        self.row_sets = list(row_sets)
        self.cursors = []
        self.commits = 0

    def cursor(self):
        cursor = FakeCursor(self.row_sets)
        self.cursors.append(cursor)
        return cursor

    def commit(self):
        self.commits += 1


def test_load_squads_stores_every_team_and_reports_failures(isolated, monkeypatch):
    client, _ = isolated
    real = fotmob.fetch_squad

    def flaky(team_id, http=None):
        if team_id == 2:
            raise fotmob.FotmobError("no squad")
        return real(team_id, http)

    monkeypatch.setattr(fotmob, "fetch_squad", flaky)
    connection = FakeConnection()
    report = fotmob.load_squads(connection, client, leagues={47: None})
    assert report["teams"] == 1 and report["players"] == 3
    assert report["failures"] == ["Club Two: no squad"]
    assert connection.commits == 1


def test_warm_profiles_skips_cached_pages_and_stops_when_refused(isolated, monkeypatch):
    client, _ = isolated
    fotmob.fetch_player(1, client)  # already cached
    connection = FakeConnection([(1,), (2,), (3,)])
    report = fotmob.warm_profiles(connection, client)
    assert report["already_cached"] == 1 and report["fetched"] == 2

    def refused(player_id, http=None):
        raise httpx.ConnectError("blocked")

    monkeypatch.setattr(fotmob, "fetch_player", refused)
    monkeypatch.setattr(fotmob, "_read_cache", lambda path, max_age=0: None)
    many = FakeConnection([(n,) for n in range(20)])
    stopped = fotmob.warm_profiles(many, client)
    assert stopped["stopped_early"] and len(stopped["failures"]) == fotmob.MAX_CONSECUTIVE_FAILURES


def test_warm_profiles_respects_the_limit(isolated):
    client, _ = isolated
    report = fotmob.warm_profiles(FakeConnection([(7,), (8,), (9,)]), client, limit=1)
    assert report["fetched"] == 1


# ------------------------------------------------------------------ linking


def test_links_need_the_same_birth_date_and_exactly_one_name_fit():
    born = date(2002, 5, 4)
    theirs = [
        (1, "Lamine Yamal", born),
        (2, "Twin Name", born),
        (3, "Someone Else", date(1990, 1, 1)),
        (4, "Joao Neves", born),
    ]
    ours = [
        (100, "Lamine Yamal Nasraoui Ebana", None, born),
        (101, "Twin Name", None, born),
        (102, "Twin Name", None, born),
        (103, "Someone Else", None, date(1991, 1, 1)),  # different birth date
        (104, "Joao Neves", None, born),
    ]
    links = fotmob.link_players(FakeConnection(theirs, ours))
    assert links == {
        1: (100, "BIRTH_DATE_AND_NAME_WORDS"),
        4: (104, "BIRTH_DATE_AND_NAME"),
    }


def test_links_are_persisted():
    connection = FakeConnection()
    assert fotmob.persist_links(connection, {1: (10, "X"), 2: (20, "Y")}) == 2
    assert connection.commits == 1


# ------------------------------------------------------------------ alternatives engine


def profile(pid, name, scale, minutes=400, family="midfielders", offset=0.0):
    values = {f"stat{i}": scale * (i + 1) + offset for i in range(12)}
    return fotmob.parse_player(
        player_page(pid, name, minutes=minutes, values=values, family=family), pid
    )


def test_stronger_similar_players_are_upgrades_and_weaker_ones_are_not():
    profiles = [profile(1, "Target", 1.0)]
    profiles += [profile(10 + n, f"Peer{n}", 0.5 + n * 0.1) for n in range(10)]
    pool = alternatives.build_pool(profiles)
    result = alternatives.alternatives(pool, 1, limit=20)
    assert result["status"] == "OK" and result["family"] == "midfielders"
    names_up = [row["name"] for row in result["upgrades"]]
    assert names_up and all(row["overall_difference"] >= alternatives.UPGRADE_MARGIN
                            for row in result["upgrades"])
    assert "Peer0" not in names_up  # a weaker player is never an upgrade
    assert result["similar"][0]["similarity"] >= result["similar"][-1]["similarity"]
    top = result["upgrades"][0]
    assert top["better_at"] and top["stats_compared"] == 12


def test_role_families_are_never_mixed_and_short_samples_are_excluded():
    profiles = [profile(1, "Target", 1.0)]
    profiles += [profile(10 + n, f"Peer{n}", 1.0 + n * 0.1) for n in range(6)]
    profiles += [profile(30, "Striker", 9.0, family="strikers")]
    profiles += [profile(31, "Bench", 9.0, minutes=20)]
    pool = alternatives.build_pool(profiles)
    names = {row["name"] for row in alternatives.alternatives(pool, 1, 20)["similar"]}
    assert "Striker" not in names and "Bench" not in names
    assert alternatives.alternatives(pool, 31)["status"] == "TARGET_TOO_FEW_MINUTES"
    assert alternatives.alternatives(pool, 12345)["status"] == "TARGET_NOT_IN_POOL"


def test_budget_filter_and_unvalued_players():
    profiles = [profile(1, "Target", 1.0)]
    profiles += [profile(10 + n, f"Peer{n}", 1.0 + n * 0.1) for n in range(8)]
    pool = alternatives.build_pool(profiles)
    pool.entries[17].market_value = 5_000_000
    pool.entries[16].market_value = None
    capped = alternatives.alternatives(pool, 1, 20, max_value_eur=10_000_000)
    assert {row["name"] for row in capped["upgrades"]} <= {"Peer7"}  # only the valued, cheap one


def test_lower_is_better_stats_are_inverted():
    profiles = [profile(1, "Target", 1.0)]
    pool = alternatives.build_pool(
        [
            fotmob.parse_player(
                player_page(
                    10 + n, f"P{n}", values={**{f"s{i}": 1.0 for i in range(11)}, "fouls": float(n)}
                ),
                10 + n,
            )
            for n in range(6)
        ]
        + profiles
    )
    fewest = pool.entries[10]
    most = pool.entries[15]
    assert alternatives.percentile(pool, "midfielders", "fouls", fewest.values["fouls"]) > \
        alternatives.percentile(pool, "midfielders", "fouls", most.values["fouls"])


def test_load_pool_reads_the_cache_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(fotmob, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.setattr(alternatives, "_pool", None)
    monkeypatch.setattr(alternatives, "_entries_from_database", lambda: {})
    (tmp_path / "players").mkdir()
    (tmp_path / "players" / "1.json").write_text(json.dumps(profile(1, "Cached", 1.0)))
    (tmp_path / "players" / "bad.json").write_text("{not json")
    pool = alternatives.load_pool()
    assert list(pool.entries) == [1]
    monkeypatch.setattr(alternatives, "_pool", None)


def test_load_pool_merges_stored_profiles_with_fresher_disk_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(fotmob, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.setattr(alternatives, "_pool", None)
    stored = [profile(1, "Stored", 1.0), profile(2, "Only stored", 1.0)]
    monkeypatch.setattr(
        alternatives,
        "_entries_from_database",
        lambda: {e.player_id: e for e in map(alternatives.entry_from_profile, stored) if e},
    )
    (tmp_path / "players").mkdir()
    (tmp_path / "players" / "1.json").write_text(json.dumps(profile(1, "Fresh", 1.0)))
    pool = alternatives.load_pool()
    assert sorted(pool.entries) == [1, 2]
    assert pool.entries[1].name == "Fresh"
    monkeypatch.setattr(alternatives, "_pool", None)


def test_newly_cached_page_does_not_reload_stored_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(fotmob, "CACHE_DIRECTORY", tmp_path)
    monkeypatch.setattr(alternatives, "_pool", None)
    calls = []

    def stored():
        calls.append(1)
        entry = alternatives.entry_from_profile(profile(2, "Stored", 1.0))
        assert entry is not None
        return {2: entry}

    monkeypatch.setattr(alternatives, "_entries_from_database", stored)
    (tmp_path / "players").mkdir()
    alternatives.load_pool()
    (tmp_path / "players" / "1.json").write_text(json.dumps(profile(1, "New click", 1.0)))
    pool = alternatives.load_pool()
    assert sorted(pool.entries) == [1, 2]
    assert len(calls) == 1
    monkeypatch.setattr(alternatives, "_pool", None)


# ------------------------------------------------------------------ routes


def test_league_squad_and_player_routes(monkeypatch):
    def fake_query(query, params):
        if "FROM fotmob_team t" in query and "GROUP BY" in query:
            return [
                {"league_id": 47, "league_name": "Premier League", "season": "2026/2027",
                 "team_id": 1, "team_name": "Club One", "players": 3},
            ]
        if "FROM fotmob_team WHERE" in query:
            return [{"team_id": 1, "name": "Club One", "league_id": 47,
                     "league_name": "Premier League", "season": "2026/2027"}]
        if "FROM fotmob_squad_member m" in query and "JOIN fotmob_team" in query:
            return [{"team_id": 1, "team_name": "Club One", "league_name": "Premier League",
                     "event_profile_player_id": 5, "link_basis": "BIRTH_DATE_AND_NAME"}]
        if "FROM fotmob_squad_member m" in query:
            return [{"player_id": 11, "name": "Mid One", "position_group": "MD"}]
        return [{"player_id": 5}]  # bridge lookup

    monkeypatch.setattr(squad_routes, "_query_all", fake_query)
    monkeypatch.setattr(squad_routes.alternatives, "load_pool",
                        lambda: alternatives.build_pool([profile(11, "Mid One", 1.0)]))
    monkeypatch.setattr(squad_routes.fotmob, "fetch_player", lambda pid: profile(pid, "Mid One", 1))
    monkeypatch.setattr(squad_routes, "similar_players", lambda pid, limit=6: [{"player_id": 9}])
    client = TestClient(app)
    leagues = client.get("/squads/leagues").json()
    assert leagues["data"][0]["teams"][0]["name"] == "Club One"
    assert "personal use" in leagues["meta"]["source_note"]
    squad = client.get("/squads/teams/1").json()["data"]
    assert squad["players"][0]["current_stats_cached"] is True
    detail = client.get("/squads/players/11").json()["data"]
    assert detail["name"] == "Mid One" and detail["squad"]["event_profile_player_id"] == 5
    alts = client.get("/squads/players/11/alternatives").json()
    assert alts["data"]["status"] == "OK" and alts["data"]["event_similar"] == [{"player_id": 9}]
    assert "not how a player would perform" in alts["meta"]["alternatives_note"]


def test_unknown_club_and_unavailable_pages(monkeypatch):
    monkeypatch.setattr(squad_routes, "_query_all", lambda query, params: [])
    assert TestClient(app).get("/squads/teams/999").status_code == 404

    def down(pid):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(squad_routes.fotmob, "fetch_player", down)
    assert TestClient(app).get("/squads/players/1").status_code == 503
    assert TestClient(app).get("/squads/players/1/alternatives").status_code == 503


def test_noisy_rate_stats_are_left_out_but_volume_rates_stay():
    assert alternatives.is_noisy("long_ball_succeeeded_accuracy")
    assert alternatives.is_noisy("aerials_won_percent")
    assert alternatives.is_noisy("penalty_won_title")
    assert alternatives.is_noisy("won_contest_subtitle")  # dribbles success rate
    assert not alternatives.is_noisy("non_penalty_xg")
    assert not alternatives.is_noisy("successful_passes_accuracy")
    assert not alternatives.is_noisy("save_percentage")
    values = {f"s{i}": float(i) for i in range(11)} | {"long_ball_succeeeded_accuracy": 100.0}
    built = alternatives.entry_from_profile(
        fotmob.parse_player(player_page(50, "X", values=values), 50)
    )
    assert built is not None and "long_ball_succeeeded_accuracy" not in built.values


def test_upgrades_are_weighted_toward_the_clicked_players_strengths():
    # The target is elite at the first six stats and poor at the last six.
    pool_profiles = [
        profile(1, "Target", 1.0),
        profile(2, "Specialist", 1.0),  # placeholder replaced below
    ]
    peers = []
    for n in range(10):
        values = {f"stat{i}": float(n + 1) * (1 if i < 6 else 0.1) + i for i in range(12)}
        peers.append(
            fotmob.parse_player(player_page(10 + n, f"Peer{n}", values=values), 10 + n)
        )
    target_values = {f"stat{i}": (11.0 if i < 6 else 0.0) + i for i in range(12)}
    target = fotmob.parse_player(player_page(1, "Target", values=target_values), 1)
    # Strong where the target is weak, equal elsewhere: should not look like an upgrade.
    defender_like = {f"stat{i}": (0.0 if i < 6 else 11.0) + i for i in range(12)}
    rival = fotmob.parse_player(player_page(99, "OtherStyle", values=defender_like), 99)
    pool = alternatives.build_pool([target, rival, *peers, *pool_profiles[1:]])
    result = alternatives.alternatives(pool, 1, limit=30)
    by_name = {row["name"]: row for row in result["similar"]}
    assert by_name["OtherStyle"]["overall_difference"] < 0  # worse where the target is strong
    for row in result["similar"]:
        for gap in row["better_at"] + row["weaker_at"]:
            assert abs(gap["percentile_gap"]) >= alternatives.MIN_LISTED_GAP


def test_keeper_errors_count_lower_and_tiny_gaps_are_hidden():
    def keeper(pid, name, errors, saves):
        values = {f"k{i}": float(i + pid) for i in range(11)}
        values.update({"error_led_to_goal": errors, "saves": saves, "goals_conceded": 9.0})
        return fotmob.parse_player(
            player_page(pid, name, values=values, family="keepers"), pid
        )

    profiles = [keeper(i, f"K{i}", float(i % 3), 3.0 + i * 0.1) for i in range(1, 9)]
    pool = alternatives.build_pool(profiles)
    clean = pool.entries[3]  # 0 errors
    sloppy = pool.entries[2]  # 2 errors
    fewer = alternatives.percentile(pool, "keepers", "error_led_to_goal", 0.0)
    more = alternatives.percentile(pool, "keepers", "error_led_to_goal", 2.0)
    assert fewer is not None and more is not None and fewer > more
    assert "goals_conceded" not in clean.values and "goals_conceded" not in sloppy.values
    a = alternatives.Entry(1, "A", None, "x", None, 300, {"v": 0.001})
    b = alternatives.Entry(2, "B", None, "x", None, 300, {"v": 0.002})
    assert not alternatives._meaningful(a, b, "v")
    c = alternatives.Entry(3, "C", None, "x", None, 300, {"v": 1.0})
    assert alternatives._meaningful(a, c, "v")


def test_players_without_a_birth_date_link_on_exact_name_and_club():
    members = [
        (1, "Lamine Yamal", "Barcelona"),
        (2, "Pedro Gonzalez", "Barcelona"),  # name fits but our record is at another club
        (3, "Already Linked", "Barcelona"),
        (4, "Twin Name", "Barcelona"),  # two of ours fit, so ambiguous
    ]
    ours = [
        (100, "Lamine Yamal Nasraoui Ebana", None, "FC Barcelona"),
        (101, "Pedro Gonzalez", None, "Real Madrid"),
        (102, "Twin Name", None, "FC Barcelona"),
        (103, "Twin Name", None, "FC Barcelona"),
        (104, "No Club", None, None),
    ]
    links = fotmob._link_by_name_and_club(FakeConnection(members, ours), {3})
    assert links == {1: (100, "NAME_WORDS_AND_CLUB")}


def test_current_season_route_returns_linked_profile_or_a_reason(monkeypatch):
    from football_intelligence import current_season_routes

    monkeypatch.setattr(current_season_routes, "person_member_ids", lambda pid: [pid])
    client = TestClient(app)
    monkeypatch.setattr(current_season_routes, "_query_all", lambda query, params: [])
    none = client.get("/players/5/current-season").json()
    assert none["data"] is None and none["meta"]["status"] == "NOT_IN_CURRENT_TOP_FIVE_SQUADS"

    link = {"fotmob_id": 11, "link_basis": "NAME_AND_CLUB", "team_name": "Club One"}
    monkeypatch.setattr(current_season_routes, "_query_all", lambda query, params: [link])
    monkeypatch.setattr(
        current_season_routes.fotmob, "fetch_player", lambda pid: profile(pid, "Mid One", 1.0)
    )
    ok = client.get("/players/5/current-season").json()
    assert ok["meta"]["status"] == "AVAILABLE" and ok["data"]["name"] == "Mid One"
    assert ok["data"]["squad"]["team_name"] == "Club One"
    assert "personal" in ok["meta"]["source_note"]

    def down(pid):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(current_season_routes.fotmob, "fetch_player", down)
    assert client.get("/players/5/current-season").json()["meta"]["status"] == "FOTMOB_UNAVAILABLE"
