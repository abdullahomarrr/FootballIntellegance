from football_intelligence import alternatives
from football_intelligence.head_to_head import head_to_head


def profile(player_id, name, family, minutes, **per90):
    stats = [
        {"key": key, "title": key.title(), "group": group, "per90": value}
        for key, (group, value) in per90.items()
    ]
    return {
        "player_id": player_id,
        "name": name,
        "team": "Club",
        "team_id": 1,
        "positions": [{"label": "Winger", "main": True}],
        "league": {"name": "League", "season": "2026/2027", "stats": {"Minutes played": minutes}},
        "traits": {"key": f"stats_comparison_{family}"},
        "stats": stats,
        "market_values": [{"date": "2026-10-01", "value": 50_000_000}],
        "heatmap": [[10.0, 10.0], [100.0, 60.0], [100.0, 60.0]],
    }


def pool_with(*profiles):
    filler = [
        profile(
            100 + i,
            f"P{i}",
            "att_mid_wingers",
            900,
            goals=("Shooting", i / 10),
            chances_created=("Passing", i / 5),
            dispossessed=("Possession", i / 4),
        )
        for i in range(10)
    ]
    return alternatives.build_pool([*filler, *profiles])


def test_each_stat_goes_to_the_clearly_higher_ranked_player():
    a = profile(
        1,
        "Striker A",
        "att_mid_wingers",
        900,
        goals=("Shooting", 0.9),
        chances_created=("Passing", 0.1),
        dispossessed=("Possession", 2.0),
    )
    b = profile(
        2,
        "Creator B",
        "att_mid_wingers",
        300,
        goals=("Shooting", 0.1),
        chances_created=("Passing", 1.9),
        dispossessed=("Possession", 0.5),
    )
    result = head_to_head(pool_with(a, b), a, b)
    rows = {r["key"]: r for g in result["groups"] for r in g["stats"]}
    assert rows["goals"]["winner"] == "a"
    assert rows["chances_created"]["winner"] == "b"
    assert rows["dispossessed"]["winner"] == "b"  # fewer is better
    assert rows["dispossessed"]["lower_is_better"] is True
    assert result["summary"] == {"a": 1, "b": 2, "even": 0, "compared": 3}
    assert result["same_role"] is True
    assert result["low_minutes"] == ["Creator B"]
    assert result["biggest_edges"]["a"][0]["key"] == "goals"
    assert result["a"]["heatmap_points"] == 3
    assert {c["events"] for c in result["a"]["heatmap"]} == {1, 2}


def test_near_identical_numbers_are_even_and_one_sided_groups_are_hidden():
    a = profile(
        1,
        "A",
        "att_mid_wingers",
        900,
        goals=("Shooting", 0.5),
        physical_metrics_running=("Physical", 9.0),
    )
    b = profile(2, "B", "att_mid_wingers", 900, goals=("Shooting", 0.5))
    result = head_to_head(pool_with(a, b), a, b)
    assert [g["group"] for g in result["groups"]] == ["Shooting"]
    assert result["groups"][0]["stats"][0]["winner"] == "even"


def test_players_without_stats_are_not_compared():
    a = profile(1, "A", "att_mid_wingers", 900, goals=("Shooting", 0.5))
    empty = {**profile(2, "B", "att_mid_wingers", 0), "traits": {}}
    result = head_to_head(pool_with(a), a, empty)
    assert result["comparable"] is False and result["groups"] == []
