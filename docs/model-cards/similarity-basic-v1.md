# Similarity Basic v1

## Purpose

Rank compatible player profiles using common, available numerical features. It supports human recruitment investigation; it does not declare two players interchangeable.

## Method

Cosine similarity over the intersection of non-null features. The response lists compared and missing features and assigns coverage confidence. Missing event features are never replaced with zero.

## Evaluation required before production

Backtest known role cohorts, inspect nearest neighbours with football analysts, measure ranking stability across minutes thresholds, and compare against standardized Euclidean and role-weighted baselines.

## Limitations

Sensitive to feature scaling and feature choice. Current implementation is a deterministic baseline, not a validated production model.
