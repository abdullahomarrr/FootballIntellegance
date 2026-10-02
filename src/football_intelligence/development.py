from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DatedMetric:
    observed_on: date
    value: float
    minutes: int


@dataclass(frozen=True)
class DevelopmentTrend:
    slope_per_year: float | None
    direction: str
    observations: int
    total_minutes: int
    confidence: str


@dataclass(frozen=True)
class MetricDevelopmentObservation:
    metric_name: str
    observed_on: date
    percentile: float
    metric_value: float
    minutes: int
    season_label: str
    competition_name: str
    team_name: str
    position_group: str


@dataclass(frozen=True)
class MetricDevelopmentTrend:
    metric_name: str
    position_group: str
    percentile_slope_per_year: float | None
    direction: str
    observations: int
    total_minutes: int
    confidence: str
    samples: tuple[MetricDevelopmentObservation, ...]


def development_trend(observations: list[DatedMetric]) -> DevelopmentTrend:
    ordered = sorted(observations, key=lambda item: item.observed_on)
    total_minutes = sum(max(item.minutes, 0) for item in ordered)
    confidence = "LOW" if total_minutes < 900 else "LIMITED" if total_minutes < 1800 else "STANDARD"
    if len(ordered) < 2 or len({item.observed_on for item in ordered}) < 2:
        return DevelopmentTrend(None, "INSUFFICIENT_DATA", len(ordered), total_minutes, confidence)
    origin = ordered[0].observed_on
    x = [(item.observed_on - origin).days / 365.25 for item in ordered]
    y = [item.value for item in ordered]
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    denominator = sum((item - x_mean) ** 2 for item in x)
    slope = sum((xv - x_mean) * (yv - y_mean) for xv, yv in zip(x, y, strict=True)) / denominator
    rounded = round(slope, 6)
    direction = "IMPROVING" if rounded > 0 else "DECLINING" if rounded < 0 else "STABLE"
    return DevelopmentTrend(rounded, direction, len(ordered), total_minutes, confidence)


def metric_development_trends(
    observations: list[MetricDevelopmentObservation],
) -> list[MetricDevelopmentTrend]:
    """Describe observed percentile movement without presenting it as a forecast.

    Metric and position families stay separate. Percentiles are used because their
    direction has already been normalised by the intelligence mart: a higher
    percentile is always more favourable, including lower-is-better measures.
    """

    grouped: dict[tuple[str, str], list[MetricDevelopmentObservation]] = defaultdict(list)
    for item in observations:
        grouped[(item.metric_name, item.position_group)].append(item)

    results: list[MetricDevelopmentTrend] = []
    for (metric_name, position_group), samples in grouped.items():
        ordered = sorted(samples, key=lambda item: item.observed_on)
        trend = development_trend(
            [DatedMetric(item.observed_on, item.percentile, item.minutes) for item in ordered]
        )
        results.append(
            MetricDevelopmentTrend(
                metric_name=metric_name,
                position_group=position_group,
                percentile_slope_per_year=trend.slope_per_year,
                direction=trend.direction,
                observations=trend.observations,
                total_minutes=trend.total_minutes,
                confidence=trend.confidence,
                samples=tuple(ordered),
            )
        )

    return sorted(
        results,
        key=lambda item: (
            item.observations < 2,
            -(abs(item.percentile_slope_per_year or 0)),
            item.metric_name,
        ),
    )
