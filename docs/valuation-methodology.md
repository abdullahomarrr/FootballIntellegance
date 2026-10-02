# Valuation methodology and availability boundary

## Current status

No legitimate as-of-dated historical market-value target series is available in the current
environment. Consequently no valuation model is fitted, no test metric is reported, and no
uncertainty interval or player valuation is fabricated. The API returns
`LICENSED_TARGET_REQUIRED` with null estimate and interval fields.

## Required target contract

A future source must provide player identity, valuation date, amount, currency, valuation
type, publication/as-of time, provenance, correction semantics, retention rights, and
redistribution terms. Market value is not a transfer fee; the two must remain distinct.
Nominal values require currency normalization with a dated, documented FX source.

## Intended evaluation

Features must exist at or before the prediction cutoff. Splits are chronological, with a
held-out future period and no random player-season leakage. Baselines should include median
by cohort and regularized linear/tree models only after the target audit passes. Report MAE,
median absolute error, RMSE, and calibration/coverage of prediction intervals by position,
age, league, and value band. A model is publishable only if it improves on the declared
baseline and its interval coverage is measured on untouched future data.

The current code implements and tests the temporal availability contract around this future
workflow. It is an integration boundary, not evidence of a trained model.

