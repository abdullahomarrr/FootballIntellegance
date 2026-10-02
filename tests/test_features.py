import pytest

from football_intelligence.features import compatible_features, context_adjust, normalize_direction


def test_feature_dictionary_is_position_and_coverage_aware():
    basic_forward = compatible_features("FW", 1)
    assert [item.name for item in basic_forward] == ["goals_per_90", "market_value"]
    assert {item.source_requirement for item in basic_forward} == {
        "player_match_stats",
        "licensed_market_value",
    }


def test_direction_normalization_keeps_context_out_of_quality():
    assert normalize_direction("turnovers_per_90", 3) == -3
    with pytest.raises(ValueError, match="context-only"):
        normalize_direction("market_value", 10)


def test_context_adjustment_is_explicit_and_validated():
    assert context_adjust(10, league_strength=0.8, age_reliability=0.5) == 4
    with pytest.raises(ValueError, match="positive"):
        context_adjust(10, league_strength=0)
    with pytest.raises(ValueError, match="between"):
        context_adjust(10, league_strength=1, age_reliability=2)
