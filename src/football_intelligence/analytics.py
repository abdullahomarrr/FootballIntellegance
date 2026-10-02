from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev


def per_90(value: float | None, minutes: int | None) -> float | None:
    if value is None or minutes is None or minutes <= 0:
        return None
    return value * 90 / minutes


def percentile_rank(value: float, population: list[float]) -> float | None:
    if not population:
        return None
    below = sum(item < value for item in population)
    equal = sum(item == value for item in population)
    return round((below + 0.5 * equal) / len(population) * 100, 2)


def sample_confidence(minutes: int) -> str:
    if minutes < 450:
        return "LOW"
    if minutes < 900:
        return "LIMITED"
    return "STANDARD"


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    score: float
    compared_features: tuple[str, ...]
    missing_features: tuple[str, ...]
    confidence: str


def cosine_similarity(
    left: dict[str, float | None], right: dict[str, float | None]
) -> SimilarityResult:
    common = tuple(
        sorted(
            key
            for key in left.keys() & right.keys()
            if left[key] is not None and right[key] is not None
        )
    )
    missing = tuple(sorted((left.keys() | right.keys()) - set(common)))
    if not common:
        return SimilarityResult(0.0, (), missing, "UNAVAILABLE")
    left_values = [float(left[key]) for key in common]  # type: ignore[arg-type]
    right_values = [float(right[key]) for key in common]  # type: ignore[arg-type]
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0 or right_norm == 0:
        score = 0.0
    else:
        score = sum(a * b for a, b in zip(left_values, right_values, strict=True)) / (
            left_norm * right_norm
        )
    coverage = len(common) / len(left.keys() | right.keys())
    confidence = "HIGH" if coverage >= 0.9 else "MEDIUM" if coverage >= 0.6 else "LOW"
    return SimilarityResult(round(score * 100, 2), common, missing, confidence)


def z_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    spread = pstdev(values)
    if spread == 0:
        return [0.0 for _ in values]
    center = mean(values)
    return [(value - center) / spread for value in values]


def weighted_cosine_similarity(
    left: dict[str, float | None],
    right: dict[str, float | None],
    weights: dict[str, float],
) -> SimilarityResult:
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("Feature weights cannot be negative")
    keys = left.keys() | right.keys() | weights.keys()
    common = tuple(
        sorted(
            key
            for key in keys
            if left.get(key) is not None and right.get(key) is not None and weights.get(key, 1) > 0
        )
    )
    missing = tuple(sorted(keys - set(common)))
    if not common:
        return SimilarityResult(0.0, (), missing, "UNAVAILABLE")
    left_values = [float(left[key]) * weights.get(key, 1) ** 0.5 for key in common]  # type: ignore[arg-type]
    right_values = [float(right[key]) * weights.get(key, 1) ** 0.5 for key in common]  # type: ignore[arg-type]
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    score = (
        sum(a * b for a, b in zip(left_values, right_values, strict=True))
        / (left_norm * right_norm)
        if left_norm and right_norm
        else 0.0
    )
    requested = {key for key in keys if weights.get(key, 1) > 0}
    coverage = len(common) / len(requested) if requested else 0
    confidence = "HIGH" if coverage >= 0.9 else "MEDIUM" if coverage >= 0.6 else "LOW"
    return SimilarityResult(round(score * 100, 2), common, missing, confidence)
