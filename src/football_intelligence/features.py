from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MetricDirection(StrEnum):
    HIGHER_BETTER = "HIGHER_BETTER"
    LOWER_BETTER = "LOWER_BETTER"
    CONTEXT_ONLY = "CONTEXT_ONLY"


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    label: str
    unit: str
    coverage_tier: int
    direction: MetricDirection
    positions: tuple[str, ...]
    source_requirement: str


FEATURE_SET_VERSION = "player_style_v1"
FEATURES: dict[str, FeatureDefinition] = {
    "goals_per_90": FeatureDefinition(
        "goals_per_90",
        "Goals per 90",
        "per_90",
        1,
        MetricDirection.HIGHER_BETTER,
        ("FW", "AM", "WM"),
        "player_match_stats",
    ),
    "progressive_passes_per_90": FeatureDefinition(
        "progressive_passes_per_90",
        "Progressive passes per 90",
        "per_90",
        3,
        MetricDirection.HIGHER_BETTER,
        ("CB", "FB", "DM", "CM", "AM"),
        "event_data",
    ),
    "pressures_per_90": FeatureDefinition(
        "pressures_per_90",
        "Pressures per 90",
        "per_90",
        3,
        MetricDirection.HIGHER_BETTER,
        ("FB", "DM", "CM", "AM", "WM", "FW"),
        "event_data",
    ),
    "turnovers_per_90": FeatureDefinition(
        "turnovers_per_90",
        "Turnovers per 90",
        "per_90",
        2,
        MetricDirection.LOWER_BETTER,
        ("GK", "CB", "FB", "DM", "CM", "AM", "WM", "FW"),
        "player_match_stats",
    ),
    "market_value": FeatureDefinition(
        "market_value",
        "Market value",
        "currency",
        1,
        MetricDirection.CONTEXT_ONLY,
        ("GK", "CB", "FB", "DM", "CM", "AM", "WM", "FW"),
        "licensed_market_value",
    ),
}


def compatible_features(position_group: str, available_tier: int) -> tuple[FeatureDefinition, ...]:
    return tuple(
        feature
        for feature in FEATURES.values()
        if position_group in feature.positions and feature.coverage_tier <= available_tier
    )


def normalize_direction(name: str, value: float) -> float:
    feature = FEATURES[name]
    if feature.direction == MetricDirection.CONTEXT_ONLY:
        raise ValueError(f"{name} is context-only and cannot enter a quality score")
    return -value if feature.direction == MetricDirection.LOWER_BETTER else value


def context_adjust(value: float, *, league_strength: float, age_reliability: float = 1.0) -> float:
    if league_strength <= 0:
        raise ValueError("League strength must be positive")
    if not 0 <= age_reliability <= 1:
        raise ValueError("Age reliability must be between zero and one")
    return round(value * league_strength * age_reliability, 6)
