from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from football_intelligence import repository
from football_intelligence.api import app
from football_intelligence.archetypes import CATALOGUE, assess_archetype, metric_label

client = TestClient(app)


def test_every_catalogue_metric_has_a_football_label_and_a_position_family():
    for position, definitions in CATALOGUE.items():
        assert len(definitions) >= 3
        for definition in definitions:
            for metric in definition.weights:
                assert metric_label(metric) != metric.replace("_", " ").capitalize(), metric
                goalkeeper_metric = metric.startswith(("goalkeeper", "claims", "sweeper")) or (
                    metric == "goals_conceded_per_90"
                )
                assert goalkeeper_metric == (position == "GK"), (position, metric)


def test_assessment_ranks_profiles_and_reports_a_credible_secondary():
    assessment = assess_archetype(
        {
            "xg_per_90": 95,
            "average_shot_xg": 90,
            "box_entries_per_90": 80,
            "successful_dribbles_per_90": 88,
            "progressive_carries_per_90": 84,
            "xt_added_per_90": 82,
        },
        "FW",
    )
    assert assessment.primary is not None
    assert assessment.primary.name == "Penalty-area goal threat"
    assert assessment.secondary is not None
    assert assessment.secondary.name == "Dribbling ball-carrier"
    assert [fit.score for fit in assessment.ranked] == sorted(
        (fit.score for fit in assessment.ranked), reverse=True
    )


def test_assessment_is_unavailable_for_unknown_positions_and_empty_evidence():
    assert assess_archetype({"xg_per_90": 90}, "XX").clarity == "UNAVAILABLE"
    empty = assess_archetype({"xg_per_90": None}, "FW")
    assert empty.primary is None
    assert empty.clarity == "UNAVAILABLE"


def test_blended_profiles_are_flagged():
    assessment = assess_archetype(
        {
            "recoveries_per_90": 80,
            "defensive_duels_per_90": 78,
            "defensive_actions_per_90": 80,
            "pressures_per_90": 78,
            "progressive_carries_per_90": 80,
            "successful_dribbles_per_90": 80,
            "xt_added_per_90": 78,
        },
        "MD",
    )
    assert assessment.clarity == "BLENDED"
    assert any("hybrid" in note for note in assessment.notes)


def test_spatial_query_exposes_action_layers_and_threat_cells(monkeypatch):
    captured = {}

    def query_one(query, parameters):
        captured["query"] = query
        return None

    monkeypatch.setattr(repository, "_query_one", query_one)
    monkeypatch.setattr(repository, "person_member_ids", lambda player_id: [player_id])
    assert repository.player_spatial(3) is None
    for fragment in (
        "heatmap_layers",
        "threat_cells",
        "pass_lines",
        "'passes'",
        "'carries'",
        "'defensive'",
        '{"tags":[{"id":101}]}',  # Wyscout records goals as a tag, not an outcome
    ):
        assert fragment in captured["query"]


def test_similarity_query_compares_pooled_targets_only_against_pooled_peers(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        repository, "_query_all", lambda query, parameters: captured.update(query=query) or []
    )
    monkeypatch.setattr(repository, "person_member_ids", lambda player_id: [player_id])
    repository.similar_players(1)
    query = captured["query"]
    assert "pooled_percentile" in query
    assert "target.comparison_scope = candidate.comparison_scope" in query
    assert "metric.provider_pool = (SELECT tm.provider_pool" in query


def test_person_endpoint_reports_combined_provider_records(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.person_members",
        lambda player_id: [
            {"player_id": 2, "provider": "wyscout_open", "link_basis": "FULL_NAME_AND_CLUB"},
            {"player_id": 3, "provider": "statsbomb_open", "link_basis": "FULL_NAME_AND_CLUB"},
        ],
    )
    payload = client.get("/players/2/related-identities").json()
    assert len(payload["data"]) == 2
    assert payload["meta"]["policy"] == "PRESENTATION_GROUPING_ONLY"
    monkeypatch.setattr(
        "football_intelligence.api.person_members",
        lambda player_id: [{"player_id": 2, "provider": "wyscout_open", "link_basis": None}],
    )
    assert client.get("/players/2/related-identities").json()["data"] == []


def test_season_context_is_passed_through_to_context_dependent_endpoints(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "football_intelligence.api.player_spatial",
        lambda player_id, context=None: seen.update(spatial=context) or None,
    )
    monkeypatch.setattr(
        "football_intelligence.api.similar_players",
        lambda player_id, role_id=None, context=None: seen.update(similar=context) or [],
    )
    monkeypatch.setattr(
        "football_intelligence.api.team_context_rows",
        lambda player_id, context=None: seen.update(team=context) or [],
    )
    query = {"team_id": 5, "competition_id": 6, "season_id": 7}
    client.get("/players/1/spatial", params=query)
    client.get("/players/1/similar", params=query)
    client.get("/players/1/tactical-context", params=query)
    assert seen == {"spatial": (5, 6, 7), "similar": (5, 6, 7), "team": (5, 6, 7)}


def _team_rows():
    rows = []
    for player_id in range(1, 9):
        for metric, value in (
            ("pressures_per_90", 85),
            ("recoveries_per_90", 80),
            ("progressive_passes_per_90", 35),
            ("box_entries_per_90", 45),
        ):
            rows.append(
                {
                    "player_id": player_id,
                    "minutes_played": 1800,
                    "metric_name": metric,
                    "percentile": (
                        95 if player_id == 1 and metric == "box_entries_per_90" else value
                    ),
                    "is_target": player_id == 1,
                    "team_name": "Example FC",
                    "competition_name": "League",
                    "season_label": "2025/26",
                }
            )
    return rows


def test_tactical_context_endpoint_describes_team_style_and_player_contribution(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.team_context_rows", lambda player_id: _team_rows()
    )
    payload = client.get("/players/1/tactical-context").json()
    assert payload["meta"]["status"] == "AVAILABLE"
    assert payload["meta"]["human_review_required"] is True
    data = payload["data"]
    assert data["team_name"] == "Example FC"
    assert data["style"].startswith("Press-and-win")
    assert any("Chance creation" in item for item in data["adds"])
    assert len(data["axes"]) == 4


def test_tactical_context_is_unavailable_without_enough_squad_evidence(monkeypatch):
    monkeypatch.setattr("football_intelligence.api.team_context_rows", lambda player_id: [])
    payload = client.get("/players/1/tactical-context").json()
    assert payload["data"] is None
    assert payload["meta"]["status"] == "INSUFFICIENT_SQUAD_EVIDENCE"


def test_scouting_report_exposes_secondary_profile_and_fit_breakdown(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.player_detail",
        lambda player_id: {"player_id": player_id, "canonical_name": "Example Forward"},
    )
    base = {
        "player_id": 7,
        "team_id": 2,
        "team_name": "Example FC",
        "competition_id": 3,
        "competition_name": "League",
        "season_id": 4,
        "season_label": "2025/26",
        "position_group": "FW",
        "minutes_played": 2000,
        "comparison_scope": "POOLED_PROVIDER_POSITION",
        "data_as_of": datetime(2026, 9, 1, tzinfo=UTC),
    }
    values = {
        "xg_per_90": 96,
        "average_shot_xg": 90,
        "box_entries_per_90": 75,
        "successful_dribbles_per_90": 88,
        "progressive_carries_per_90": 84,
        "xt_added_per_90": 80,
    }
    monkeypatch.setattr(
        "football_intelligence.api.player_intelligence",
        lambda player_id: [{**base, "metric_name": k, "percentile": v} for k, v in values.items()],
    )
    data = client.get("/players/7/scouting-report").json()["data"]
    assert data["archetype"] == "Penalty-area goal threat"
    assert data["secondary_archetype"] == "Dribbling ball-carrier"
    assert data["profile_fits"][0]["name"] == data["archetype"]
    assert data["comparison_scopes"] == ["POOLED_PROVIDER_POSITION"]
    assert data["archetype_clarity"] in {"CLEAR", "BLENDED", "LIMITED"}


def _database_available() -> bool:
    try:
        return bool(repository.player_detail(3807))
    except Exception:
        return False


@pytest.mark.skipif(not _database_available(), reason="real warehouse is not reachable")
def test_real_warehouse_serves_the_full_intelligence_layer_for_a_flagship_player():
    """Runs against the loaded database: Mbappé's thin league cohort must use the pooled scope."""
    intelligence = repository.player_intelligence(3807)
    assert intelligence, "advanced intelligence rows are missing"
    recent = [row for row in intelligence if row["season_label"] == "2022/23"]
    assert {row["comparison_scope"] for row in recent} == {"POOLED_PROVIDER_POSITION"}
    assert any(row["metric_name"] == "xt_added_per_90" for row in intelligence)
    peers = repository.similar_players(3807, limit=5)
    assert peers and all(row["comparison_population"].startswith("pooled") for row in peers)
    spatial = repository.player_spatial(3807)
    assert spatial and spatial["heatmap_layers"] and spatial["threat_cells"]
    assert spatial["pass_lines"]
    wyscout_shots = repository.player_spatial(2125, (None, None, None))
    assert wyscout_shots and any(
        str(shot["outcome"]).lower() == "goal" for shot in wyscout_shots["shots"]
    )
    goalkeeper = repository.player_intelligence(6155)
    assert {"goalkeeper_save_pct", "goalkeeper_distribution_pct"} <= {
        row["metric_name"] for row in goalkeeper
    }


def _pool_rows(
    player_id: int, name: str, values: dict[str, float], season: str = "2017/18", season_id: int = 1
):
    return [
        {
            "player_id": player_id,
            "team_id": 1,
            "competition_id": 1,
            "season_id": season_id,
            "position_group": "FW",
            "minutes_played": 2000,
            "metric_name": metric,
            "percentile": value,
            "name": name,
            "normalized_name": name.lower(),
            "team_name": "Club",
            "competition_name": "League",
            "season_label": season,
        }
        for metric, value in values.items()
    ]


def test_discovery_ranks_players_for_an_archetype_and_dedupes_people():
    from football_intelligence.discovery import build_index, discover

    finisher = {"xg_per_90": 95, "average_shot_xg": 90, "box_entries_per_90": 85}
    average = {"xg_per_90": 60, "average_shot_xg": 62, "box_entries_per_90": 61}
    rows = (
        _pool_rows(1, "Ace Finisher", finisher, "2015/16")
        + _pool_rows(1, "Ace Finisher", {**finisher, "xg_per_90": 80}, "2016/17", 2)
        + _pool_rows(2, "Solid Forward", average)
    )
    ranked = discover(
        build_index(rows), position="FW", archetype="Penalty-area goal threat", minimum_fit=55
    )
    assert [row["name"] for row in ranked] == ["Ace Finisher", "Solid Forward"]
    assert ranked[0]["season_label"] == "2015/16"  # the best season, one row per person
    assert ranked[0]["evidence"][0]["label"] == "Expected goals"


def test_discovery_endpoint_validates_inputs_and_returns_ranked_players(monkeypatch):
    from football_intelligence import discovery

    discovery.clear_cache()
    monkeypatch.setattr(
        "football_intelligence.api.archetype_pool",
        lambda: _pool_rows(
            1, "Ace Finisher", {"xg_per_90": 95, "average_shot_xg": 90, "box_entries_per_90": 85}
        ),
    )
    ok = client.get(
        "/discover", params={"position": "FW", "archetype": "Penalty-area goal threat"}
    ).json()
    assert ok["data"][0]["name"] == "Ace Finisher"
    assert ok["meta"]["human_review_required"] is True
    bad = client.get("/discover", params={"position": "FW", "archetype": "Nope"})
    assert bad.status_code == 422
    catalogue = client.get("/discover/archetypes").json()["data"]
    assert set(catalogue) == {"FW", "MD", "DF", "GK"}
    discovery.clear_cache()


def test_role_fit_endpoint_scores_only_roles_for_the_players_position(monkeypatch):
    base = {
        "player_id": 7,
        "team_id": 2,
        "team_name": "Example FC",
        "competition_id": 3,
        "season_id": 4,
        "season_label": "2025/26",
        "position_group": "FW",
        "minutes_played": 2000,
    }
    values = {"pressures_per_90": 88, "recoveries_per_90": 70, "xg_per_90": 40}
    monkeypatch.setattr(
        "football_intelligence.api.player_intelligence",
        lambda player_id: [{**base, "metric_name": k, "percentile": v} for k, v in values.items()],
    )
    monkeypatch.setattr(
        "football_intelligence.api.recruitment_roles",
        lambda: [
            {
                "role_id": 1,
                "name": "Pressing forward",
                "positions": ["FW"],
                "feature_weights": {"pressures_per_90": 3, "recoveries_per_90": 1},
            },
            {
                "role_id": 2,
                "name": "Sweeper goalkeeper",
                "positions": ["GK"],
                "feature_weights": {"sweeper_actions_per_90": 5},
            },
            {
                "role_id": 3,
                "name": "Finisher",
                "positions": ["FW"],
                "feature_weights": {"xg_per_90": 2, "average_shot_xg": 2},
            },
        ],
    )
    payload = client.get("/players/7/role-fit").json()
    assert [fit["name"] for fit in payload["data"]] == ["Pressing forward"]
    assert payload["data"][0]["fit_score"] == 83.5
    assert payload["meta"]["human_review_required"] is True


def test_overlapping_provider_records_keep_only_the_larger_sample():
    rows = [
        {"player_id": 10, "team_id": 1, "competition_id": 1, "season_id": 1, "minutes_played": 30},
        {"player_id": 20, "team_id": 1, "competition_id": 1, "season_id": 1, "minutes_played": 34},
        {"player_id": 10, "team_id": 2, "competition_id": 1, "season_id": 2, "minutes_played": 9},
    ]
    kept = repository._best_member_rows(rows)
    assert [(row["player_id"], row["season_id"]) for row in kept] == [(20, 1), (10, 2)]


def test_ties_between_provider_records_resolve_to_the_lowest_identity():
    rows = [
        {"player_id": 30, "team_id": 1, "competition_id": 1, "season_id": 1, "minutes_played": 5},
        {"player_id": 20, "team_id": 1, "competition_id": 1, "season_id": 1, "minutes_played": 5},
    ]
    assert [row["player_id"] for row in repository._best_member_rows(rows)] == [20]


def test_context_filter_expands_to_the_query_parameter_shape():
    assert repository._context_filter(None) == (None,) * 6
    assert repository._context_filter((1, 2, 3)) == (1, 1, 2, 2, 3, 3)


def test_person_member_ids_falls_back_to_the_player_when_unlinked(monkeypatch):
    monkeypatch.setattr(repository, "_query_all", lambda query, parameters: [])
    assert repository.person_member_ids(5) == [5]
    monkeypatch.setattr(
        repository,
        "_query_all",
        lambda query, parameters: [{"player_id": 2}, {"player_id": 9}],
    )
    assert repository.person_member_ids(9) == [2, 9]


def test_person_grouping_only_links_one_statsbomb_and_one_wyscout_identity():
    from football_intelligence.person_groups import BUILD_SQL

    assert "= 1" in BUILD_SQL and "count(*) = 2" in BUILD_SQL
    assert "array_length(string_to_array(p.normalized_name, ' '), 1) >= 2" in BUILD_SQL
