# Linear development v1

## Purpose

Summarize the direction and annual rate of change of a player metric across dated observations.

## Method

Ordinary least squares against elapsed years. At least two distinct dates are required. Confidence is based on total observed minutes and all source observations remain visible.

The player-profile implementation applies this calculation to direction-normalized advanced-event percentiles within a single position family. It reports the first and latest context, annual percentile movement, observation count, evidence-minutes and confidence under model version `observed_percentile_trajectory_v1`. Metrics with only one qualified sample remain unavailable rather than being presented as a trend.

## Limitations

The slope is descriptive, not a forecast. It does not separate ageing, league strength, role, team or injury effects and is sensitive to small samples and metric-definition changes. No future value is emitted.

Percentile populations can also change between seasons. Movement therefore means the player's standing changed relative to the observed peers in each context; it does not prove that an underlying skill changed by the same amount.
