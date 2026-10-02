# Player intelligence methodology

## Observation grains

The platform keeps provider events, canonical player-match facts, and player-team-
competition-season profiles separate. Mid-season teams are not merged by default. Counts,
minutes, starts, position, and event-derived measures retain their source provider and
`data_as_of` timestamp.

Wyscout minutes come from lineups and substitutions. StatsBomb minutes come from lineup
position intervals and observed match duration. A player without a participation interval is
not assigned inferred minutes. StatsBomb baseline actions use native event attributes; Wyscout
uses the published event and tag dictionaries.

The advanced layer adds 22 candidate metrics. Fifteen belong to outfield profiles: pass
completion, pressured-pass completion, forward-coordinate progressive passes, final-third
passes, box entries, progressive carries, successful dribbles, pressures, recoveries,
defensive actions, defensive duels (tackles for StatsBomb, ground defending duels for Wyscout),
direction-adjusted turnovers, net expected threat added, expected goals, and average shot
quality. Goalkeepers use a separate seven-metric family: saves, save percentage, goals conceded,
claims and punches, sweeper actions, distribution accuracy and long-pass accuracy (35 m+). Goalkeeper metrics never enter an outfield population, or vice
versa.

Provider support remains explicit. StatsBomb supplies pressure, carry, recovery, turnover, and
xG detail that is not inferred for providers that did not record it. Wyscout completion and duel
outcomes use its published tags. Unsupported observations remain null; they are not zero.

## Rates and comparison populations

Per-90 values divide observed counts by observed minutes only when minutes are positive.
Profiles are labelled `LOW` below 450 minutes, `LIMITED` from 450 through 899, and `STANDARD`
from 900 minutes. Percentiles include only profiles with at least 900 minutes and are calculated
within competition, season, and broad provider position (`GK`, `DF`, `MD`, or `FW`).

Metrics with fewer than five qualified peers or no population variation are removed. For
turnovers and goals conceded, percentile direction is reversed so a higher percentile still
means the more favourable observed value. Low-minute rows remain visible in the base profile
and are not converted to zero.

## Spatial intelligence

Raw provider coordinates are retained. Wyscout 0–100 and StatsBomb 120×80 coordinates are
mapped to 105×68 metres. Values outside a provider's declared coordinate plane are quarantined,
never clipped. The player spatial API reports located-event count, mean location, a 12×8 event-
density surface, event mix, and shot locations sized by recorded xG. The versioned xT baseline
is deterministic location evidence, not a trained claim about player value.

Coordinate-increase features such as progressive passes and carries are provider-relative;
attacking-direction normalization is not claimed where the source lacks sufficient orientation
context.

## Reports, similarity, and roles

Development trends require at least two chronological season observations and expose total
minutes and confidence. Player archetypes are deterministic summaries of the strongest
available position-relative percentiles. Scouting reports cite contributing metrics, surface
strengths, low-percentile review questions, sample caveats, and require human review.

Similarity is balanced mean absolute distance between advanced percentiles in the target's
strongest qualified competition-season-position context. A candidate needs at least three
shared metrics and 60% target-feature coverage. A saved role supplies transparent feature
weights—including zero for irrelevant dimensions—and hard constraints. Role fit is the weighted mean of the candidate's favourable
percentiles; a role-backed recommendation combines 60% similarity with 40% role fit. The two
scores remain visible separately.

The broad position field cannot defensibly distinguish centre-back from full-back or central
from wide midfield roles. Detailed tactical labels therefore remain user-defined recruitment
briefs rather than inferred truth. All analytical outputs support scouting investigation and
require human review.

## Comparison populations (update 2026-10-01)

A percentile is computed in a like-for-like cohort when at least 15 qualified players of the same
position and data provider exist in that competition and season. Otherwise it is computed in a
pooled population: all qualified player-seasons of that position from the same provider. The
scope is stored with every row (`COMPETITION_SEASON` or `POOLED_PROVIDER_POSITION`) and shown in
the interface. Similarity compares a pooled target only with candidates ranked in the pooled
population, and a like-for-like target only with its own cohort.

## Expected threat

`xt_added_per_90` sums the change in a versioned location value (rising toward goal and through
central lanes) over completed passes and carries. It is a transparent baseline, not a fitted xT
grid. StatsBomb includes carries; Wyscout does not record them, so Wyscout values are lower and
are only ever ranked against Wyscout peers.

## Archetypes

Each position (GK, DF, MD, FW) has its own catalogue of weighted metric profiles
(`archetypes.py`). A profile's fit is the weighted mean percentile over its measurable metrics.
It needs at least two metrics covering half of its weight. The report names a primary profile, a
secondary when another profile reaches 65, and a clarity rating: clear, blended (within five
points), weak (best below 55), or limited when provider gaps prevent other profiles from being
assessed. Archetypes are descriptive summaries, not verdicts.

## Team context and role fit

Team style averages squad players' pooled position-relative percentiles, weighted by minutes,
over four axes (possession security, progression, pressing and winning the ball, chance
creation). The player's own axis scores show what he adds and where the squad carries the load.
Role fit is the weighted mean percentile over a saved brief's positive weights, shown only when
at least 60% of that weight is measurable, with the strongest drivers and weakest gaps.

## Discovery

`/discover` ranks one player-season per person by fit to a chosen archetype (minimum fit 60 and
60% metric coverage). Results show the three strongest metrics and whether the style is the
player's main profile.
