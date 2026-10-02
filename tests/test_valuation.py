from datetime import date

from football_intelligence.valuation import (
    ValuationObservation,
    temporal_evaluation,
    valuation_availability,
)


def test_valuation_evaluation_uses_future_only_test_rows():
    result = temporal_evaluation(
        [
            ValuationObservation(1, date(2024, 1, 1), 10, 9),
            ValuationObservation(1, date(2025, 1, 1), 20, 18),
            ValuationObservation(2, date(2025, 2, 1), 10, 14),
        ],
        cutoff=date(2024, 6, 1),
    )
    assert result.training_rows == 1
    assert result.test_rows == 2
    assert result.mae == 3
    assert result.mape == 25


def test_valuation_gates_license_and_temporal_leakage():
    assert (
        valuation_availability(False, date(2024, 1, 1), date(2025, 1, 1))
        == "LICENSED_TARGET_REQUIRED"
    )
    assert (
        valuation_availability(True, date(2026, 1, 1), date(2025, 1, 1))
        == "TEMPORAL_LEAKAGE_REJECTED"
    )
    assert temporal_evaluation([], cutoff=date(2025, 1, 1)).status == "INSUFFICIENT_DATA"
