# Similarity methodology

## Production population

`GET /players/{player_id}/similar` uses only canonical rows backed by real
`fact_player_match` observations. The target is its latest player-team-season profile with
at least 900 minutes. Candidates must share the same competition, season, and broad Wyscout
position group (`GK`, `DF`, `MD`, or `FW`) and must also have at least 900 minutes.

The broad position is a provider field, not an inferred detailed role. The system does not
pretend it can distinguish centre-backs from full-backs, or central midfielders from wide
midfielders, from the available metadata.

## Features and scaling

The feature set `player_style_v2` contains eight per-90 metrics: goals, assists, shots,
shots on target, passes, key passes, tackles, and interceptions. Each value is ranked inside
the declared comparison population. Missing values remain missing; no imputation to zero is
performed.

Percentiles are centered at 50 before cosine similarity. This avoids the inflated scores
caused by applying cosine directly to an all-positive 0–100 vector. Cosine is mapped from
`[-1, 1]` to a displayed `[0, 100]` score. A result is returned only when all target metrics
are also available for the candidate.

## Explainability and versioning

Every row includes the comparison population, minutes, position group, model version,
compared features, and the target/candidate percentile and difference for every feature.
The deterministic implementation is versioned as `role_weighted_similarity_v2`.

## Validation boundary

The live database query has been exercised against the full Wyscout Open 2017/18 Big Five
load and returns named canonical peers with eight real compared features. This is an
engineering sanity check, not football-expert validation. Analyst review of role cohorts,
ranking stability across minute thresholds, and comparison to standardized Euclidean
distance remain necessary before treating the ranking as a decision model.

Similarity supports investigation; it does not establish interchangeability, transfer
availability, affordability, tactical fit, medical suitability, or future performance.
