from football_intelligence.analytics import (
    cosine_similarity,
    per_90,
    percentile_rank,
    sample_confidence,
    z_scores,
)


def test_per_90_preserves_missing_and_rejects_zero_minutes():
    assert per_90(2, 180) == 1
    assert per_90(None, 180) is None
    assert per_90(2, 0) is None


def test_percentile_uses_midrank_for_ties():
    assert percentile_rank(2, [1, 2, 2, 3]) == 50
    assert percentile_rank(2, []) is None


def test_sample_confidence_thresholds():
    assert sample_confidence(449) == "LOW"
    assert sample_confidence(450) == "LIMITED"
    assert sample_confidence(900) == "STANDARD"


def test_similarity_uses_common_features_and_reports_missing():
    result = cosine_similarity({"a": 1, "b": 2, "spatial": None}, {"a": 1, "b": 2})
    assert result.score == 100
    assert result.compared_features == ("a", "b")
    assert result.missing_features == ("spatial",)
    assert result.confidence == "MEDIUM"


def test_similarity_without_common_features_is_unavailable():
    result = cosine_similarity({"a": None}, {"b": 1})
    assert result.confidence == "UNAVAILABLE"


def test_z_scores_handle_empty_and_constant_populations():
    assert z_scores([]) == []
    assert z_scores([2, 2]) == [0, 0]
    assert z_scores([1, 2, 3]) == [-1.224744871391589, 0.0, 1.224744871391589]
