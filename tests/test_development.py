from datetime import date

from football_intelligence.development import (
    DatedMetric,
    MetricDevelopmentObservation,
    development_trend,
    metric_development_trends,
)


def test_development_trend_reports_slope_direction_and_minutes_confidence():
    trend = development_trend(
        [
            DatedMetric(date(2024, 1, 1), 1.0, 1000),
            DatedMetric(date(2025, 1, 1), 2.0, 1000),
        ]
    )
    assert trend.direction == "IMPROVING"
    assert trend.slope_per_year is not None
    assert round(trend.slope_per_year, 2) == 1.0
    assert trend.confidence == "STANDARD"


def test_development_trend_requires_distinct_dates():
    trend = development_trend([DatedMetric(date(2025, 1, 1), 1.0, 100)])
    assert trend.direction == "INSUFFICIENT_DATA"
    assert trend.slope_per_year is None


def test_metric_development_keeps_position_families_separate_and_orders_change():
    observations = [
        MetricDevelopmentObservation(
            metric_name="turnovers_per_90",
            observed_on=date(2024, 7, 1),
            percentile=40,
            metric_value=3.0,
            minutes=1000,
            season_label="2024/25",
            competition_name="League",
            team_name="Club",
            position_group="MID",
        ),
        MetricDevelopmentObservation(
            metric_name="turnovers_per_90",
            observed_on=date(2025, 7, 1),
            percentile=70,
            metric_value=2.0,
            minutes=1100,
            season_label="2025/26",
            competition_name="League",
            team_name="Club",
            position_group="MID",
        ),
        MetricDevelopmentObservation(
            metric_name="turnovers_per_90",
            observed_on=date(2025, 7, 1),
            percentile=55,
            metric_value=1.5,
            minutes=900,
            season_label="2025/26",
            competition_name="League",
            team_name="Club",
            position_group="FWD",
        ),
    ]

    trends = metric_development_trends(observations)

    assert len(trends) == 2
    assert trends[0].position_group == "MID"
    assert trends[0].direction == "IMPROVING"
    assert round(trends[0].percentile_slope_per_year or 0, 1) == 30.0
    assert trends[0].confidence == "STANDARD"
    assert trends[1].direction == "INSUFFICIENT_DATA"
