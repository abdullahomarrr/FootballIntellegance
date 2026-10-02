from football_intelligence.cross_source import (
    MatchFact,
    compare_match_facts,
    normalize_team_name,
    statsbomb_match_facts,
    wyscout_match_facts,
)


def test_team_normalization_handles_provider_affixes_without_fuzzy_matching():
    assert normalize_team_name("Celta de Vigo") == normalize_team_name("Celta Vigo")
    assert normalize_team_name("Levante UD") == normalize_team_name("Levante")
    assert normalize_team_name("RC Deportivo La Coruña") == "deportivo coruna"
    assert normalize_team_name("Atl�tico Madrid") == normalize_team_name("Atlético Madrid")
    assert normalize_team_name(r"Legan\u00e9s") == "leganes"


def test_provider_fact_parsers_and_comparison_preserve_disagreements():
    statsbomb = statsbomb_match_facts(
        [
            {
                "match_id": 1,
                "match_date": "2018-04-14",
                "home_team": {"home_team_name": "Barcelona"},
                "away_team": {"away_team_name": "Valencia"},
                "home_score": 2,
                "away_score": 1,
            }
        ]
    )
    wyscout = wyscout_match_facts(
        [
            {
                "wyId": 2,
                "dateutc": "2018-04-14 14:15:00",
                "teamsData": {
                    "10": {"side": "home", "teamId": 10, "score": 2},
                    "20": {"side": "away", "teamId": 20, "score": 0},
                },
            }
        ],
        [{"wyId": 10, "name": "Barcelona"}, {"wyId": 20, "name": "Valencia"}],
    )

    report = compare_match_facts("statsbomb_open", statsbomb, "wyscout_open", wyscout)

    assert report["overlapping_matches"] == 1
    assert report["score_agreements"] == 0
    assert report["score_mismatches"][0]["statsbomb_open"]["away_score"] == 1


def test_non_overlapping_match_is_not_forced_into_comparison():
    report = compare_match_facts(
        "a",
        [MatchFact("1", "2018-01-01", "A", "B", 1, 0)],
        "b",
        [MatchFact("2", "2018-01-02", "A", "B", 1, 0)],
    )
    assert report["overlapping_matches"] == 0
