# Squad Exact Optimizer v1

## Purpose

Select one unique player for each requested position while respecting a total budget and maximizing supplied fit scores.

## Method

Exact exhaustive search with budget and positional constraints. It is suitable for small shortlists; a mixed-integer solver should replace it for large candidate universes.

## Limitations

The optimizer does not create fit scores and cannot correct biased or poorly calibrated inputs. It ignores wages, registration rules, negotiation uncertainty and medical/personality assessment unless explicitly represented as constraints.
