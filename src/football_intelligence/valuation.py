from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ValuationObservation:
    player_id: int
    observed_on: date
    actual_value: float
    predicted_value: float


@dataclass(frozen=True)
class ValuationEvaluation:
    cutoff: date
    training_rows: int
    test_rows: int
    mae: float | None
    median_absolute_error: float | None
    mape: float | None
    status: str


def temporal_evaluation(
    observations: list[ValuationObservation], *, cutoff: date
) -> ValuationEvaluation:
    """Evaluate only observations after a fixed temporal cutoff; never random-split history."""
    training = [item for item in observations if item.observed_on <= cutoff]
    test = [item for item in observations if item.observed_on > cutoff]
    if not training or not test:
        return ValuationEvaluation(
            cutoff, len(training), len(test), None, None, None, "INSUFFICIENT_DATA"
        )
    errors = sorted(abs(item.predicted_value - item.actual_value) for item in test)
    middle = len(errors) // 2
    median = errors[middle] if len(errors) % 2 else (errors[middle - 1] + errors[middle]) / 2
    percentage_errors = [
        abs(item.predicted_value - item.actual_value) / item.actual_value
        for item in test
        if item.actual_value > 0
    ]
    return ValuationEvaluation(
        cutoff=cutoff,
        training_rows=len(training),
        test_rows=len(test),
        mae=round(sum(errors) / len(errors), 2),
        median_absolute_error=round(median, 2),
        mape=(
            round(sum(percentage_errors) / len(percentage_errors) * 100, 2)
            if percentage_errors
            else None
        ),
        status="EVALUATED",
    )


def valuation_availability(
    has_licensed_targets: bool, feature_as_of: date, target_date: date
) -> str:
    if not has_licensed_targets:
        return "LICENSED_TARGET_REQUIRED"
    if feature_as_of > target_date:
        return "TEMPORAL_LEAKAGE_REJECTED"
    return "AVAILABLE_FOR_TRAINING"
