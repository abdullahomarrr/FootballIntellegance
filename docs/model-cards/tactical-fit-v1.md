# Tactical fit v1

## Purpose

Rank how closely a player's supplied trait vector matches a role or team requirement vector while exposing which dimensions were actually compared.

## Method

Cosine similarity over non-null common features, reported on a 0–100 scale. Confidence is the more conservative of feature coverage and player-minute sample bands. A rule-based archetype labels the largest available trait and reports missing inputs.

## Limitations

This is an explainable matching baseline, not a causal estimate of performance after transfer. Inputs must be population-compatible and correctly direction-normalized. It does not account for league translation, coaching effects, injuries or adaptation. Users must not compare profiles from incompatible coverage tiers.
