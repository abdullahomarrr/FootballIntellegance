from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from football_intelligence.api import app
from football_intelligence.providers.google_news_rss import CurrentContextArticle

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_meta_is_honest_about_live_provider():
    payload = client.get("/meta").json()
    assert payload["live_provider_status"] == "CREDENTIAL_REQUIRED"
    assert "statsbomb_open" in payload["providers"]


def test_database_coverage_endpoint_preserves_empty_ledger(monkeypatch):
    monkeypatch.setattr("football_intelligence.api.coverage_observations", lambda *args: [])
    response = client.get("/coverage/Premier%20League/2026%2F27")
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["count"] == 0


def test_open_coverage_endpoint_reads_persisted_source_evidence(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.openfootball_coverage",
        lambda: [{"competition_code": "en.1", "fixture_count": 380}],
    )
    response = client.get("/coverage/open")
    assert response.status_code == 200
    payload = response.json()
    assert payload["statsbomb"]
    assert payload["wyscout"]
    assert payload["openfootball"][0]["fixture_count"] == 380
    assert payload["meta"]["live_provider_status"] == "CREDENTIAL_REQUIRED"


def test_global_coverage_endpoint_returns_metadata(monkeypatch):
    observation = {"provider": "statsbomb_open", "competition_name": "Premier League"}
    monkeypatch.setattr(
        "football_intelligence.api.coverage_observations", lambda *args: [observation]
    )
    response = client.get("/coverage")
    assert response.status_code == 200
    assert response.json()["data"] == [observation]
    assert response.json()["meta"]["count"] == 1


def test_recruitment_endpoint_filters_and_explains_similarity():
    response = client.post(
        "/recruitment/search",
        json={
            "target_features": {"passing": 1, "carrying": 1},
            "maximum_age": 25,
            "candidates": [
                {
                    "player_id": 1,
                    "name": "Candidate",
                    "age": 21,
                    "minutes": 1200,
                    "features": {"passing": 1, "carrying": 1, "spatial": None},
                }
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["similarity_score"] == 100
    assert payload["data"][0]["missing_features"] == ["spatial"]


def test_replacement_finder_uses_same_explainable_constraints():
    response = client.post(
        "/recruitment/replacements",
        json={
            "target_features": {"passing": 1},
            "minimum_minutes": 100,
            "candidates": [
                {
                    "player_id": 2,
                    "name": "Replacement",
                    "age": 22,
                    "minutes": 900,
                    "features": {"passing": 1},
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["meta"]["workflow"] == "REPLACEMENT_FINDER"
    assert response.json()["meta"]["requires_human_review"] is True


def test_role_and_shortlist_workflows(monkeypatch):
    role = {"role_id": 4, "name": "Pressing forward"}
    shortlist = {"shortlist_id": 8, "name": "Summer targets", "status": "ACTIVE"}
    monkeypatch.setattr("football_intelligence.api.recruitment_roles", lambda: [role])
    monkeypatch.setattr("football_intelligence.api.create_recruitment_role", lambda **kwargs: role)
    monkeypatch.setattr("football_intelligence.api.shortlists", lambda: [shortlist])
    monkeypatch.setattr(
        "football_intelligence.api.create_shortlist", lambda name, role_id: shortlist
    )
    monkeypatch.setattr(
        "football_intelligence.api.shortlist_detail", lambda shortlist_id: shortlist
    )
    monkeypatch.setattr(
        "football_intelligence.api.player_detail",
        lambda player_id: {"player_id": player_id, "canonical_name": "Target"},
    )
    monkeypatch.setattr(
        "football_intelligence.api.upsert_shortlist_player",
        lambda shortlist_id, **kwargs: {"shortlist_id": shortlist_id, **kwargs},
    )
    monkeypatch.setattr(
        "football_intelligence.api.archive_shortlist",
        lambda shortlist_id: {**shortlist, "status": "ARCHIVED"},
    )

    assert client.get("/recruitment/roles").json()["meta"]["count"] == 1
    created_role = client.post(
        "/recruitment/roles",
        json={
            "name": "Pressing forward",
            "positions": ["ST"],
            "feature_weights": {"pressures": 2},
            "feature_set_version": "role_v1",
        },
    )
    assert created_role.status_code == 200
    assert client.get("/shortlists").json()["meta"]["count"] == 1
    assert (
        client.post("/shortlists", json={"name": "Summer targets", "role_id": 4}).status_code == 200
    )
    assert client.get("/shortlists/8").status_code == 200
    added = client.post(
        "/shortlists/8/players",
        json={"player_id": 7, "rank": 1, "stage": "REVIEWING", "rationale": "Strong fit"},
    )
    assert added.json()["data"]["stage"] == "REVIEWING"
    assert client.post("/shortlists/8/archive").json()["data"]["status"] == "ARCHIVED"


def test_shortlist_not_found(monkeypatch):
    monkeypatch.setattr("football_intelligence.api.shortlist_detail", lambda shortlist_id: None)
    assert client.get("/shortlists/999").status_code == 404
    assert client.post("/shortlists/999/players", json={"player_id": 7}).status_code == 404


def test_removing_a_shortlist_candidate(monkeypatch):
    lists = {
        8: {"shortlist_id": 8, "status": "ACTIVE"},
        9: {"shortlist_id": 9, "status": "ARCHIVED"},
    }
    monkeypatch.setattr("football_intelligence.api.shortlist_detail", lambda i: lists.get(i))
    removed = []

    def remove(shortlist_id, player_id):
        if player_id != 7:
            return None
        removed.append((shortlist_id, player_id))
        return {"shortlist_id": shortlist_id, "player_id": player_id, "stage": "REVIEWING"}

    monkeypatch.setattr("football_intelligence.api.remove_shortlist_player", remove)
    response = client.delete("/shortlists/8/players/7")
    assert response.status_code == 200 and response.json()["data"]["player_id"] == 7
    assert removed == [(8, 7)]
    assert client.delete("/shortlists/8/players/99").status_code == 404  # not on the list
    assert client.delete("/shortlists/9/players/7").status_code == 409  # archived is read-only
    assert client.delete("/shortlists/404/players/7").status_code == 404
    assert removed == [(8, 7)]


def test_shortlist_decision_snapshot_validates_reference_player():
    response = client.post(
        "/shortlists/8/players",
        json={
            "player_id": 7,
            "decision_evidence": {
                "reference_player_id": 0,
            },
        },
    )
    assert response.status_code == 422


def test_shortlist_decision_snapshot_is_rebuilt_from_server_model(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "football_intelligence.api.shortlist_detail",
        lambda shortlist_id: {
            "shortlist_id": shortlist_id,
            "role_id": 4,
            "players": [],
        },
    )
    monkeypatch.setattr(
        "football_intelligence.api.player_detail",
        lambda player_id: {
            "player_id": player_id,
            "canonical_name": "Reference" if player_id == 3 else "Candidate",
        },
    )
    monkeypatch.setattr(
        "football_intelligence.api.similar_players",
        lambda player_id, role_id=None: [
            {
                "player_id": 7,
                "similarity_score": 88.0,
                "role_fit_score": 76.0,
                "recommendation_score": 83.2,
                "feature_coverage_pct": 90.0,
                "compared_feature_count": 9,
                "target_feature_count": 10,
                "feature_differences": {
                    "pressures_per_90": {"difference": 2.0},
                    "xg_per_90": {"difference": -18.0},
                },
                "competition_name": "Example League",
                "season_label": "2025/26",
                "position_group": "FW",
                "model_version": "advanced_event_similarity_v5",
            }
        ],
    )

    def upsert(shortlist_id, **kwargs):
        captured.update(kwargs)
        return {"shortlist_id": shortlist_id, **kwargs}

    monkeypatch.setattr("football_intelligence.api.upsert_shortlist_player", upsert)
    response = client.post(
        "/shortlists/8/players",
        json={"player_id": 7, "decision_evidence": {"reference_player_id": 3}},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["decision_evidence"] == "CAPTURED_FROM_SERVER_MODEL"
    assert captured["decision_evidence"]["similarity_score"] == 88.0
    assert captured["decision_evidence"]["closest_metric"] == "pressures_per_90"
    assert captured["decision_evidence"]["largest_difference_metric"] == "xg_per_90"


def test_shortlist_detail_enriches_candidates_with_role_evidence(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.shortlist_detail",
        lambda shortlist_id: {
            "shortlist_id": shortlist_id,
            "name": "Pressing options",
            "role_feature_weights": {"pressures_per_90": 2, "xg_per_90": 1},
            "players": [
                {
                    "player_id": 7,
                    "name": "Target",
                    "rank": 1,
                    "stage": "REVIEWING",
                    "rationale": "Strong event fit",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "football_intelligence.api.player_intelligence",
        lambda player_id: [
            {
                "player_id": player_id,
                "team_id": 2,
                "team_name": "Example FC",
                "competition_id": 3,
                "competition_name": "Example League",
                "season_id": 4,
                "season_label": "2025/26",
                "position_group": "FW",
                "minutes_played": 1800,
                "metric_name": metric,
                "percentile": percentile,
                "data_as_of": "2026-06-01T00:00:00Z",
            }
            for metric, percentile in (
                ("pressures_per_90", 90),
                ("recoveries_per_90", 85),
                ("xg_per_90", 60),
            )
        ],
    )

    response = client.get("/shortlists/8")
    evidence = response.json()["data"]["players"][0]["intelligence"]

    assert response.status_code == 200
    assert evidence["status"] == "AVAILABLE"
    assert evidence["role_fit_score"] == 80.0
    assert evidence["role_feature_coverage"] == 2
    assert evidence["archetype"] == "Pressing forward"
    assert response.json()["meta"]["model_version"] == "shortlist_evidence_v1"


def test_shortlist_detail_keeps_missing_event_evidence_unknown(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.shortlist_detail",
        lambda shortlist_id: {
            "shortlist_id": shortlist_id,
            "name": "Coverage review",
            "role_feature_weights": {"progressive_passes_per_90": 3},
            "players": [
                {
                    "player_id": 19,
                    "name": "Uncovered player",
                    "rank": None,
                    "stage": "IDENTIFIED",
                    "rationale": None,
                }
            ],
        },
    )
    monkeypatch.setattr("football_intelligence.api.player_intelligence", lambda player_id: [])

    response = client.get("/shortlists/9")
    evidence = response.json()["data"]["players"][0]["intelligence"]

    assert response.status_code == 200
    assert evidence == {
        "status": "INSUFFICIENT_EVENT_COVERAGE",
        "role_fit_score": None,
        "role_feature_coverage": 0,
        "role_feature_total": 1,
    }


def test_match_summary_exposes_unresolved_identity(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.match_summary",
        lambda provider, match_id: {
            "provider": provider,
            "provider_match_id": match_id,
            "event_count": 10,
        },
    )
    response = client.get("/matches/statsbomb_open/123/summary")
    assert response.status_code == 200
    assert response.json()["meta"]["identity_status"] == "PROVIDER_UNRESOLVED"


def test_provider_player_profile_not_found(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.provider_player_match_profile", lambda *args: None
    )
    response = client.get("/players/provider/statsbomb_open/1/matches/123")
    assert response.status_code == 404


def test_provider_player_profile_success_retains_provider_scope(monkeypatch):
    profile = {
        "provider_player_id": "1",
        "provider_match_id": "123",
        "player_id": 7,
        "identity_status": "CANONICAL_SINGLE_PROVIDER",
        "event_count": 8,
    }
    monkeypatch.setattr(
        "football_intelligence.api.provider_player_match_profile", lambda *args: profile
    )
    response = client.get("/players/provider/statsbomb_open/1/matches/123")
    assert response.status_code == 200
    assert response.json()["data"] == profile
    assert response.json()["meta"]["provider"] == "statsbomb_open"
    assert response.json()["meta"]["identity_status"] == "CANONICAL_SINGLE_PROVIDER"


def test_canonical_player_endpoints_preserve_empty_coverage(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.players",
        lambda search, limit: [{"player_id": 7, "canonical_name": "Example"}],
    )
    monkeypatch.setattr(
        "football_intelligence.api.player_detail",
        lambda player_id: {"player_id": player_id, "canonical_name": "Example"},
    )
    monkeypatch.setattr("football_intelligence.api.player_seasons", lambda player_id: [])
    monkeypatch.setattr("football_intelligence.api.similar_players", lambda player_id: [])
    listing = client.get("/players?search=Example")
    detail = client.get("/players/7")
    seasons = client.get("/players/7/seasons")
    assert listing.json()["meta"]["count"] == 1
    assert detail.json()["data"]["player_id"] == 7
    assert seasons.json()["data"] == []
    assert seasons.json()["meta"]["count"] == 0


def test_player_browser_rejects_unknown_filter_values():
    assert client.get("/players?position=STRIKER").status_code == 422
    assert client.get("/players?min_minutes=-1").status_code == 422
    assert client.get("/players?sort=rating").status_code == 422


def test_player_season_metadata_exposes_source_freshness_status_and_sample(monkeypatch):
    older = datetime(2026, 8, 1, tzinfo=UTC)
    latest = datetime(2026, 9, 1, tzinfo=UTC)
    monkeypatch.setattr(
        "football_intelligence.api.player_seasons",
        lambda player_id: [
            {"season_status": "FINAL", "data_as_of": older},
            {"season_status": "IN_PROGRESS", "data_as_of": latest},
        ],
    )

    meta = client.get("/players/7/seasons").json()["meta"]

    assert meta["data_as_of"] == "2026-09-01T00:00:00Z"
    assert meta["sample_size"] == 2
    assert meta["season_statuses"] == ["FINAL", "IN_PROGRESS"]


def test_market_context_player_endpoints_are_gracefully_empty(monkeypatch):
    monkeypatch.setattr("football_intelligence.api.player_news", lambda player_id: [])
    monkeypatch.setattr("football_intelligence.api.player_sentiment", lambda player_id: [])
    news = client.get("/players/7/news")
    sentiment = client.get("/players/7/sentiment")
    assert news.json()["meta"]["source_status"] == "API_RIGHTS_REQUIRED"
    assert sentiment.json()["meta"]["use"] == "EXTERNAL_CONTEXT_ONLY"


def test_player_research_returns_live_source_links_without_article_bodies(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.player_detail",
        lambda player_id: {"player_id": player_id, "canonical_name": "Example Player"},
    )
    from football_intelligence.research import ResearchResult, SourceStatus

    article = CurrentContextArticle(
        "Example Player transfer update",
        "https://news.google.com/rss/articles/example",
        "Example Publisher",
        "https://publisher.example",
        datetime(2026, 9, 30, 12, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "football_intelligence.api.research_player",
        lambda name: ResearchResult(
            name,
            datetime(2026, 9, 30, 13, tzinfo=UTC),
            articles=[article],
            sources=[SourceStatus("google_news_rss", "OK", None, 1)],
        ),
    )
    payload = client.get("/players/7/research").json()
    assert payload["meta"]["status"] == "AVAILABLE"
    assert payload["meta"]["content_policy"].startswith("HEADLINE_METADATA_PLUS_SHORT_VERBATIM")
    assert payload["data"]["articles"][0]["topics"] == ["TRANSFER"]
    assert "article_body" not in payload["data"]["articles"][0]


def test_player_analytics_endpoints_expose_absence_without_zero(monkeypatch):
    monkeypatch.setattr("football_intelligence.api.player_metrics", lambda player_id: [])
    monkeypatch.setattr("football_intelligence.api.player_spatial", lambda player_id: None)
    monkeypatch.setattr("football_intelligence.api.player_seasons", lambda player_id: [])
    monkeypatch.setattr("football_intelligence.api.player_intelligence", lambda player_id: [])
    monkeypatch.setattr("football_intelligence.api.similar_players", lambda player_id: [])
    monkeypatch.setattr(
        "football_intelligence.api.player_market",
        lambda player_id: {"market_values": [], "transfers": []},
    )
    assert client.get("/players/7/metrics").json()["data"] == []
    assert client.get("/players/7/spatial").json()["meta"]["coverage_level"] == "UNAVAILABLE"
    assert (
        client.get("/players/7/development").json()["meta"]["status"]
        == "INSUFFICIENT_LONGITUDINAL_DATA"
    )
    assert client.get("/players/7/market").json()["data"]["market_values"] == []
    assert (
        client.get("/players/7/similar").json()["meta"]["status"] == "INSUFFICIENT_FEATURE_COVERAGE"
    )


def test_player_development_interprets_real_intelligence_rows_as_observed_change(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.player_intelligence",
        lambda player_id: [
            {
                "metric_name": "progressive_passes_per_90",
                "season_start_date": date(2024, 7, 1),
                "percentile": 42,
                "metric_value": 3.1,
                "minutes_played": 1200,
                "season_label": "2024/25",
                "competition_name": "League",
                "team_name": "Club A",
                "position_group": "MID",
                "data_as_of": datetime(2025, 6, 1, tzinfo=UTC),
            },
            {
                "metric_name": "progressive_passes_per_90",
                "season_start_date": date(2025, 7, 1),
                "percentile": 72,
                "metric_value": 5.4,
                "minutes_played": 1500,
                "season_label": "2025/26",
                "competition_name": "League",
                "team_name": "Club B",
                "position_group": "MID",
                "data_as_of": datetime(2026, 6, 1, tzinfo=UTC),
            },
        ],
    )

    payload = client.get("/players/7/development").json()

    assert payload["meta"]["status"] == "AVAILABLE"
    assert payload["meta"]["model_version"] == "observed_percentile_trajectory_v1"
    assert payload["data"][0]["direction"] == "IMPROVING"
    assert round(payload["data"][0]["percentile_slope_per_year"], 1) == 30.0
    assert payload["data"][0]["samples"][1]["team_name"] == "Club B"


def test_spatial_endpoint_labels_contextual_density_and_direction_limit(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.player_spatial",
        lambda player_id: {
            "player_id": player_id,
            "located_event_count": 120,
            "heatmap": [{"x_bin": 8, "y_bin": 3, "events": 25}],
            "data_as_of": datetime(2026, 9, 1, tzinfo=UTC),
        },
    )
    payload = client.get("/players/7/spatial").json()
    assert payload["data"]["heatmap"][0]["events"] == 25
    assert payload["meta"]["model_version"] == "contextual_event_density_v2"
    assert "attacks left to right" in payload["meta"]["direction_note"]
    assert payload["meta"]["sample_size"] == 120


def test_intelligence_endpoint_separates_goalkeeper_metric_family(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.player_intelligence",
        lambda player_id: [
            {
                "player_id": player_id,
                "position_group": "GK",
                "metric_name": "goalkeeper_saves_per_90",
                "metric_value": 3.2,
                "percentile": 81,
                "data_as_of": datetime(2026, 9, 1, tzinfo=UTC),
            }
        ],
    )
    payload = client.get("/players/7/intelligence").json()
    assert payload["meta"]["metric_family"] == "GOALKEEPER"
    assert payload["data"][0]["metric_name"] == "goalkeeper_saves_per_90"


def test_player_scouting_report_uses_real_context_and_evidence(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.player_detail",
        lambda player_id: {"player_id": player_id, "canonical_name": "Example Keeper"},
    )
    monkeypatch.setattr(
        "football_intelligence.api.player_intelligence",
        lambda player_id: [
            {
                "player_id": player_id,
                "team_id": 2,
                "competition_id": 3,
                "season_id": 4,
                "team_name": "Example FC",
                "competition_name": "League",
                "season_label": "2025/26",
                "position_group": "GK",
                "minutes_played": 1800,
                "metric_name": "goalkeeper_saves_per_90",
                "percentile": 88,
                "data_as_of": datetime(2026, 9, 1, tzinfo=UTC),
            },
            {
                "player_id": player_id,
                "team_id": 2,
                "competition_id": 3,
                "season_id": 4,
                "team_name": "Example FC",
                "competition_name": "League",
                "season_label": "2025/26",
                "position_group": "GK",
                "minutes_played": 1800,
                "metric_name": "goals_conceded_per_90",
                "percentile": 92,
                "data_as_of": datetime(2026, 9, 1, tzinfo=UTC),
            },
        ],
    )
    payload = client.get("/players/7/scouting-report").json()
    assert payload["data"]["archetype"] == "Shot-stopper"
    assert payload["data"]["context"]["season_label"] == "2025/26"
    assert payload["meta"]["evidence_metric_count"] == 2
    assert payload["meta"]["expected_metric_count"] == 7
    assert payload["meta"]["evidence_coverage_pct"] == 28.6
    assert payload["meta"]["human_review_required"] is True


def test_similar_players_returns_real_repository_results(monkeypatch):
    monkeypatch.setattr(
        "football_intelligence.api.similar_players",
        lambda player_id: [
            {
                "player_id": 8,
                "name": "Real peer",
                "similarity_score": 97.2,
                "compared_features": ["passes_per_90", "tackles_per_90"],
            }
        ],
    )
    payload = client.get("/players/7/similar").json()
    assert payload["data"][0]["name"] == "Real peer"
    assert payload["meta"]["status"] == "AVAILABLE"
    assert payload["meta"]["minimum_minutes"] == 900
    assert payload["meta"]["model_version"] == "advanced_event_similarity_v5"
    assert payload["meta"]["feature_set_version"] == "event_intelligence_v1"


def test_squad_optimizer_endpoint():
    response = client.post(
        "/squad/optimize",
        json={
            "needs": ["RW", "ST"],
            "budget": 80,
            "candidates": [
                {
                    "player_id": 1,
                    "name": "Winger",
                    "positions": ["RW"],
                    "cost": 30,
                    "fit_score": 80,
                },
                {
                    "player_id": 2,
                    "name": "Striker",
                    "positions": ["ST"],
                    "cost": 40,
                    "fit_score": 90,
                },
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["budget_remaining"] == 10


def test_tactical_fit_endpoint_is_explainable():
    response = client.post(
        "/analytics/tactical-fit",
        json={
            "player_traits": {"pressures": 8, "carries": 2},
            "required_traits": {"pressures": 9, "carries": 2},
            "player_minutes": 1200,
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["archetype"] == "PRESSING_SPECIALIST"
    assert response.json()["data"]["confidence"] == "STANDARD"


def test_development_endpoint_preserves_insufficient_data():
    response = client.post(
        "/analytics/development-trend",
        json={"observations": [{"observed_on": "2026-01-01", "value": 2, "minutes": 100}]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["direction"] == "INSUFFICIENT_DATA"


def test_sentiment_endpoint_labels_external_context():
    response = client.post("/market/sentiment/score", json={"text": "A brilliant performance"})
    assert response.status_code == 200
    assert response.json()["data"]["label"] == "POSITIVE"
    assert response.json()["meta"]["use"] == "EXTERNAL_CONTEXT_ONLY"


def test_valuation_endpoint_returns_honest_license_gate():
    response = client.post(
        "/market/valuation/availability",
        json={"feature_as_of": "2026-01-01", "target_date": "2026-06-01"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "LICENSED_TARGET_REQUIRED"
    assert response.json()["data"]["estimate"] is None


def test_recruitment_compare_explains_weighted_features():
    response = client.post(
        "/recruitment/compare",
        json={
            "left_features": {"passing": 8, "pressing": 4, "aerial": None},
            "right_features": {"passing": 7, "pressing": 5, "aerial": 2},
            "feature_weights": {"passing": 2, "pressing": 1, "aerial": 1},
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["missing_features"] == ["aerial"]
    assert response.json()["meta"]["model_version"] == "role_weighted_similarity_v1"


def test_natural_language_query_requires_confirmation():
    response = client.post(
        "/recruitment/parse-query",
        json={"query": "pressing striker under 23 and under £25m"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["position"] == "ST"
    assert response.json()["data"]["maximum_age"] == 23
    assert response.json()["data"]["requires_confirmation"] is True


def test_scout_report_endpoint_exposes_evidence_and_human_review():
    response = client.post(
        "/analytics/scout-report",
        json={
            "player_name": "Example",
            "percentiles": {"passing": 90, "pressing": 20},
            "minutes": 1000,
            "coverage_level": "BASIC",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["strengths"][0]["evidence_metrics"] == ["passing"]
    assert response.json()["meta"]["human_review_required"] is True
