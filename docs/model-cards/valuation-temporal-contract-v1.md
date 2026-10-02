# Valuation temporal contract v1

## Purpose

Define leakage-safe evaluation and availability behavior before a licensed market-value target is procured.

## Contract

Features must be timestamped no later than the target date. Evaluation uses a fixed chronological cutoff, never a random split, and reports MAE, median absolute error and MAPE on later observations. Missing train/test periods produce `INSUFFICIENT_DATA`. Without licensed targets the public result is `LICENSED_TARGET_REQUIRED` with no estimate or interval.

## Production requirements

A fitted model must add currency normalization, inflation/market regime controls, temporal cross-validation, position/age/cohort error slices, prediction intervals and drift monitoring. Market value and transfer fee remain distinct concepts.
