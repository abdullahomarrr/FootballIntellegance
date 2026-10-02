from __future__ import annotations

from dataclasses import dataclass

from football_intelligence.analytics import (
    SimilarityResult,
    cosine_similarity,
    weighted_cosine_similarity,
)


@dataclass(frozen=True, slots=True)
class Candidate:
    player_id: int
    name: str
    age: int | None
    estimated_value: float | None
    minutes: int
    features: dict[str, float | None]


@dataclass(frozen=True, slots=True)
class RecruitmentConstraints:
    maximum_age: int | None = None
    maximum_value: float | None = None
    minimum_minutes: int = 900


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    candidate: Candidate
    similarity: SimilarityResult


def rank_candidates(
    target_features: dict[str, float | None],
    candidates: list[Candidate],
    constraints: RecruitmentConstraints,
    weights: dict[str, float] | None = None,
) -> list[RankedCandidate]:
    eligible: list[RankedCandidate] = []
    for candidate in candidates:
        if candidate.minutes < constraints.minimum_minutes:
            continue
        if (
            constraints.maximum_age is not None
            and candidate.age is not None
            and candidate.age > constraints.maximum_age
        ):
            continue
        if (
            constraints.maximum_value is not None
            and candidate.estimated_value is not None
            and candidate.estimated_value > constraints.maximum_value
        ):
            continue
        similarity = (
            weighted_cosine_similarity(target_features, candidate.features, weights)
            if weights is not None
            else cosine_similarity(target_features, candidate.features)
        )
        if similarity.confidence == "UNAVAILABLE":
            continue
        eligible.append(RankedCandidate(candidate, similarity))
    return sorted(eligible, key=lambda item: item.similarity.score, reverse=True)
