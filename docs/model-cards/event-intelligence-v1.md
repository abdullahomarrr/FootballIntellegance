# Event Intelligence v1

## Purpose

Turn legitimately available historical events into comparable football evidence for player
review, similarity, role fit, shortlist decisions, and squad planning. It narrows scouting work;
it does not predict transfer success or replace video, live observation, medical, or character
assessment.

## Inputs and population

Inputs are canonical player-match minutes and provider events linked to a player, team,
competition, and season. Percentiles require at least 900 observed minutes and are calculated
inside the same competition, season, and broad position group. Each metric population requires
at least five players and genuine value variation.

## Outputs

The outfield family contains 14 distribution, progression, threat, ball-carrying, defensive,
and ball-security metrics. The goalkeeper family contains saves, goals conceded, claims and
punches, and sweeper actions. Raw values, favourable-direction percentiles, population size,
sample context, feature version, and data timestamp are retained.

## Missing-data contract

Provider-unsupported features are null, never zero. Goalkeeper and outfield metric families
cannot mix. Similarity requires at least three shared features and 60% target coverage. Role fit
reports observed/required feature counts; no score is emitted when none of the weighted role
features exists.

## Explainability

The interface exposes raw values, percentile position, peer count, strongest evidence, largest
trade-off, role weights, role-fit score, archetype evidence, review questions, and caveats.
Similarity remains balanced style closeness. Recommendation score is 60% similarity and 40%
weighted role fit when a role is selected; both components remain visible and zero-weight role
dimensions are excluded from fit.

## Known limitations

- Open data is historical and uneven across providers, competitions, and seasons.
- Position groups are broad and do not establish detailed tactical roles.
- Coordinate-increase progression is provider-relative where full attacking orientation cannot
  be proven.
- Saves and goals conceded measure observed involvement and outcomes, not shot-stopping value
  after controlling for shot quality or defensive context.
- Event data does not provide tracking-derived speed, off-ball spacing, physical output, current
  availability, contract status, wages, or reliable transfer cost.

## Validation

Automated contracts enforce the metric vocabulary, percentile bounds, minimum comparison
population, non-zero population variation, and goalkeeper/outfield separation. Engineering
validation does not constitute independent football-analyst validation; representative analyst
review and ranking-stability studies remain required before club decision use.
