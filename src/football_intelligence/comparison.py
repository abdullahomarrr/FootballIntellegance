from __future__ import annotations

from dataclasses import dataclass

from football_intelligence.analytics import SimilarityResult, weighted_cosine_similarity


@dataclass(frozen=True)
class MetricDifference:
    metric: str
    left: float
    right: float
    difference: float


@dataclass(frozen=True)
class PlayerComparison:
    similarity: SimilarityResult
    differences: tuple[MetricDifference, ...]


def compare_profiles(
    left: dict[str, float | None],
    right: dict[str, float | None],
    weights: dict[str, float],
) -> PlayerComparison:
    similarity = weighted_cosine_similarity(left, right, weights)
    differences = tuple(
        MetricDifference(
            metric,
            float(left[metric]),  # type: ignore[arg-type]
            float(right[metric]),  # type: ignore[arg-type]
            round(float(left[metric]) - float(right[metric]), 6),  # type: ignore[arg-type]
        )
        for metric in similarity.compared_features
    )
    return PlayerComparison(similarity, differences)
