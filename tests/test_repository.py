from football_intelligence import repository


def test_database_url_has_safe_local_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert repository.database_url().startswith("postgresql://football:")


def test_database_url_uses_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    assert repository.database_url() == "postgresql://example"


def test_coverage_query_casts_nullable_parameters(monkeypatch):
    captured = {}

    def query_all(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return []

    monkeypatch.setattr(repository, "_query_all", query_all)
    assert repository.coverage_observations() == []
    assert "%s::text IS NULL" in captured["query"]
    assert captured["parameters"] == (None, None, None, None)


def test_similarity_query_uses_qualified_position_population(monkeypatch):
    captured = {}

    def query_all(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return []

    monkeypatch.setattr(repository, "_query_all", query_all)
    monkeypatch.setattr(repository, "person_member_ids", lambda player_id: [player_id])
    assert repository.similar_players(7, limit=4, role_id=12) == []
    assert "minimum_minutes" in captured["query"]
    assert "900" in captured["query"]
    assert "metric.position_group = target.position_group" in captured["query"]
    assert "mart_player_intelligence_metric_percentile" in captured["query"]
    assert "abs(target.percentile - candidate.percentile)" in captured["query"]
    assert "feature_coverage" in captured["query"]
    assert "role_fit_score" in captured["query"]
    assert "recommendation_score" in captured["query"]
    assert "avg(" in captured["query"]
    assert "advanced_event_similarity_v5" in captured["query"]
    assert "POOLED_PROVIDER_POSITION" in captured["query"]
    assert "feature_weight" in captured["query"]
    assert captured["parameters"][0] == 12
    assert captured["parameters"][-1] == 4


def test_search_matches_names_without_accents_and_popular_sort_ranks_by_value(monkeypatch):
    captured = {}

    def query_all(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return []

    monkeypatch.setattr(repository, "_query_all", query_all)
    repository.players("Modrić", 10, None, None, None, 0, "popular")
    assert captured["parameters"].count("%modric%") == 1  # accent-free pattern is passed
    assert "p.normalized_name ILIKE" in captured["query"]
    assert "peak.peak_value" in captured["query"]
    assert "history.best_minutes" in captured["query"]  # thin-evidence players rank lower
    assert "profile.player_id IS NOT NULL" in captured["query"]
    assert repository.FEATURED_PLAYERS in captured["parameters"]
    assert captured["parameters"][-1] == 10
    repository.players("x", 10, None, None, None, 0, "minutes")
    assert "WHERE false" in captured["query"]  # other sorts skip the market-value work
    assert repository.FEATURED_PLAYERS not in captured["parameters"]


def test_player_browser_query_applies_football_filters_and_safe_sort(monkeypatch):
    captured = {}

    def query_all(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return []

    monkeypatch.setattr(repository, "_query_all", query_all)
    assert repository.players("Alex", 25, "FW", "French", "2017/18", 900, "minutes") == []
    assert "ranked_profile" in captured["query"]
    assert "canonical_choice" in captured["query"]
    assert "coalesce(person.person_id::text, lower(trim(p.canonical_name)))" in captured["query"]
    assert "coalesce(profile.event_count, 0) DESC" in captured["query"]
    assert "profile.minutes_played DESC" in captured["query"]
    assert captured["parameters"] == (
        "FW",
        "FW",
        "%French%",
        "%French%",
        "%2017/18%",
        "%2017/18%",
        900,
        "%Alex%",
        "%Alex%",
        "%alex%",
        "FW",
        "%French%",
        "%2017/18%",
        900,
        25,
    )


def test_player_spatial_is_contextual_density_not_career_average(monkeypatch):
    captured = {}

    def query_one(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return None

    monkeypatch.setattr(repository, "_query_one", query_one)
    monkeypatch.setattr(repository, "person_member_ids", lambda player_id: [player_id])
    assert repository.player_spatial(42) is None
    assert "mart_player_season_profile" in captured["query"]
    assert "match.competition_id = context.competition_id" in captured["query"]
    assert "jsonb_agg" in captured["query"]
    assert "event_type_counts" in captured["query"]
    assert "event_type = 'Shot'" in captured["query"]
    assert captured["parameters"][0] == [42]


def test_player_intelligence_reads_position_specific_advanced_mart(monkeypatch):
    captured = {}

    def query_all(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return []

    monkeypatch.setattr(repository, "_query_all", query_all)
    monkeypatch.setattr(repository, "person_member_ids", lambda player_id: [player_id])
    assert repository.player_intelligence(9) == []
    assert "mart_player_intelligence_metric_percentile" in captured["query"]
    assert "higher_is_better" in captured["query"]
    assert captured["parameters"] == ([9],)


def test_shortlist_detail_carries_role_evidence_into_squad_planning(monkeypatch):
    captured = {}

    def query_one(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return None

    monkeypatch.setattr(repository, "_query_one", query_one)
    assert repository.shortlist_detail(12) is None
    assert "role_positions" in captured["query"]
    assert "role_feature_weights" in captured["query"]
    assert "role_feature_set_version" in captured["query"]
    assert "decision_evidence" in captured["query"]
    assert captured["parameters"] == (12,)


def test_shortlist_stage_update_preserves_captured_decision_evidence(monkeypatch):
    captured = {}

    def execute_one(query, parameters):
        captured["query"] = query
        captured["parameters"] = parameters
        return None

    monkeypatch.setattr(repository, "_execute_one", execute_one)
    assert repository.upsert_shortlist_player(2, 7, 1, "REVIEWING", "Evidence", None) is None
    assert "decision_evidence=coalesce" in captured["query"]
    assert "shortlist_player.decision_evidence" in captured["query"]
    assert captured["parameters"][-1] is None
