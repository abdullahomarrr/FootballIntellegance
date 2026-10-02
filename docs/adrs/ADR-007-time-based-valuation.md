# ADR-007: Time-based valuation evaluation

## Context
Random splits leak future football and market information into historical valuation tests.

## Decision
Features must be available as of the prediction date. Train/evaluate with chronological cutoffs and later holdouts; report time/cohort error slices and uncertainty.

## Alternatives
Random train/test split or current features joined to past targets.

## Consequences
Scores will be less flattering but operationally credible. The implementation rejects feature timestamps after their target date.
