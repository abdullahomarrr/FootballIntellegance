import pytest

from football_intelligence.analytics import weighted_cosine_similarity
from football_intelligence.comparison import compare_profiles


def test_weighted_similarity_reports_coverage_and_differences():
    result = compare_profiles(
        {"passing": 8, "pressing": 4, "aerial": None},
        {"passing": 7, "pressing": 5, "aerial": 2},
        {"passing": 2, "pressing": 1, "aerial": 1},
    )
    assert result.similarity.compared_features == ("passing", "pressing")
    assert result.similarity.missing_features == ("aerial",)
    assert result.differences[0].difference == 1


def test_weighted_similarity_rejects_negative_weights_and_empty_features():
    with pytest.raises(ValueError, match="negative"):
        weighted_cosine_similarity({"a": 1}, {"a": 1}, {"a": -1})
    assert weighted_cosine_similarity({"a": None}, {"a": 1}, {"a": 1}).confidence == "UNAVAILABLE"
