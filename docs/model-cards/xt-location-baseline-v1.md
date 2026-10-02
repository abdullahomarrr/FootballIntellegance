# xT location baseline v1

## Purpose

Provide a transparent, provider-independent progression signal for successful passes and carries on the canonical 105 × 68 metre pitch.

## Method

The location value rises cubically with distance toward the attacking goal and is modestly weighted toward central lanes. Event xT added is end value minus start value. Failed passes, missing coordinates, shots and non-movement events are excluded. Results are grouped only by explicit provider player IDs.

## Intended use

Exploration, pipeline verification and feature prototyping. Values are stored in the derived-metric namespace with model version `xt_location_baseline_v1`.

## Limitations

This is not an empirically fitted possession model, does not estimate scoring probabilities, does not account for game state, pressure or action outcome beyond obvious failed passes, and must not be represented as provider xG or production-grade xT. A learned replacement requires licensed representative event data, train/test separation, calibration and league/season drift evaluation.
