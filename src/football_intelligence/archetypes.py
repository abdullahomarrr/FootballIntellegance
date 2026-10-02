"""Position-aware, evidence-weighted player archetypes.

Each broad position (GK, DF, MD, FW) has its own catalogue. An archetype is a weighted
profile over direction-adjusted percentiles, so a high percentile always means the more
favourable observed value. Scores are weighted mean percentiles over the metrics that exist
for the player; archetypes with too little metric coverage are not scored.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

MIN_METRICS = 2
MIN_WEIGHT_COVERAGE = 0.5
SECONDARY_THRESHOLD = 65.0
CLEAR_MARGIN = 5.0


@dataclass(frozen=True)
class ArchetypeDefinition:
    name: str
    description: str
    weights: dict[str, float]


@dataclass(frozen=True)
class ArchetypeScore:
    name: str
    description: str
    score: float
    coverage: float
    evidence: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class ArchetypeAssessment:
    primary: ArchetypeScore | None
    secondary: ArchetypeScore | None
    ranked: tuple[ArchetypeScore, ...]
    clarity: str
    notes: tuple[str, ...]


CATALOGUE: dict[str, tuple[ArchetypeDefinition, ...]] = {
    "FW": (
        ArchetypeDefinition(
            "Penalty-area goal threat",
            "Gets into dangerous areas and takes high-quality shots.",
            {"xg_per_90": 2.0, "average_shot_xg": 1.5, "box_entries_per_90": 1.0},
        ),
        ArchetypeDefinition(
            "Dribbling ball-carrier",
            "Beats opponents and moves the ball forward with the ball at their feet.",
            {
                "successful_dribbles_per_90": 2.0,
                "progressive_carries_per_90": 2.0,
                "xt_added_per_90": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Link-up forward",
            "Keeps possession and connects attacks with secure, forward passing.",
            {
                "pass_completion_pct": 1.5,
                "pressured_pass_completion_pct": 1.0,
                "progressive_passes_per_90": 1.5,
                "passes_into_final_third_per_90": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Pressing forward",
            "Leads the press and wins the ball high up the pitch.",
            {"pressures_per_90": 2.0, "recoveries_per_90": 1.5, "defensive_duels_per_90": 1.0},
        ),
        ArchetypeDefinition(
            "Creative attacker",
            "Creates threat through passing and carrying into the final third.",
            {
                "xt_added_per_90": 2.0,
                "passes_into_final_third_per_90": 1.5,
                "progressive_passes_per_90": 1.5,
            },
        ),
    ),
    "MD": (
        ArchetypeDefinition(
            "Deep-lying playmaker",
            "Dictates tempo with secure, progressive distribution.",
            {
                "progressive_passes_per_90": 2.0,
                "passes_into_final_third_per_90": 1.5,
                "pass_completion_pct": 1.5,
                "pressured_pass_completion_pct": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Ball-winning midfielder",
            "Wins the ball back through duels, recoveries and defensive work.",
            {
                "recoveries_per_90": 2.0,
                "defensive_duels_per_90": 1.5,
                "defensive_actions_per_90": 1.5,
                "pressures_per_90": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Box-to-box carrier",
            "Drives play forward by carrying and dribbling through midfield.",
            {
                "progressive_carries_per_90": 2.0,
                "successful_dribbles_per_90": 1.5,
                "xt_added_per_90": 1.5,
                "recoveries_per_90": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Attacking midfielder",
            "Arrives in the box and creates and finishes chances.",
            {
                "box_entries_per_90": 2.0,
                "xg_per_90": 1.5,
                "xt_added_per_90": 1.5,
                "successful_dribbles_per_90": 1.0,
            },
        ),
    ),
    "DF": (
        ArchetypeDefinition(
            "Ball-playing defender",
            "Starts attacks with secure, progressive passing and carrying.",
            {
                "progressive_passes_per_90": 2.0,
                "pass_completion_pct": 1.5,
                "pressured_pass_completion_pct": 1.0,
                "progressive_carries_per_90": 1.5,
            },
        ),
        ArchetypeDefinition(
            "Aggressive stopper",
            "Engages opponents high up and wins duels and defensive actions.",
            {
                "defensive_duels_per_90": 2.0,
                "defensive_actions_per_90": 1.5,
                "pressures_per_90": 1.5,
                "recoveries_per_90": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Attacking wide defender",
            "Supports attacks by entering the final third and the box.",
            {
                "box_entries_per_90": 2.0,
                "passes_into_final_third_per_90": 1.5,
                "progressive_carries_per_90": 1.5,
                "successful_dribbles_per_90": 1.0,
                "xt_added_per_90": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Secure covering defender",
            "Keeps the ball, rarely gives it away and recovers possession.",
            {
                "pass_completion_pct": 1.5,
                "turnovers_per_90": 1.5,
                "recoveries_per_90": 1.5,
                "defensive_actions_per_90": 1.0,
            },
        ),
    ),
    "GK": (
        ArchetypeDefinition(
            "Shot-stopper",
            "Saves a high share of the shots faced and concedes few goals.",
            {
                "goalkeeper_save_pct": 2.0,
                "goalkeeper_saves_per_90": 1.5,
                "goals_conceded_per_90": 1.5,
            },
        ),
        ArchetypeDefinition(
            "Commanding box keeper",
            "Claims crosses and controls the penalty area.",
            {"claims_and_punches_per_90": 2.0, "goalkeeper_save_pct": 1.0},
        ),
        ArchetypeDefinition(
            "Sweeper-keeper",
            "Plays high, sweeps behind the defence and starts attacks.",
            {
                "sweeper_actions_per_90": 2.0,
                "goalkeeper_distribution_pct": 1.5,
                "goalkeeper_long_pass_pct": 1.0,
            },
        ),
        ArchetypeDefinition(
            "Distributing keeper",
            "Builds play with accurate short and long distribution.",
            {"goalkeeper_distribution_pct": 2.0, "goalkeeper_long_pass_pct": 2.0},
        ),
    ),
}

METRIC_LABELS: dict[str, str] = {
    "pass_completion_pct": "Pass completion",
    "pressured_pass_completion_pct": "Passing under pressure",
    "progressive_passes_per_90": "Progressive passes",
    "passes_into_final_third_per_90": "Final-third entries",
    "box_entries_per_90": "Penalty-area entries",
    "progressive_carries_per_90": "Progressive carries",
    "successful_dribbles_per_90": "Successful dribbles",
    "pressures_per_90": "Pressures",
    "recoveries_per_90": "Ball recoveries",
    "defensive_actions_per_90": "Defensive actions",
    "defensive_duels_per_90": "Defensive duels",
    "turnovers_per_90": "Ball security",
    "xt_added_per_90": "Threat added (xT)",
    "xg_per_90": "Expected goals",
    "average_shot_xg": "Shot quality",
    "goalkeeper_saves_per_90": "Save volume",
    "goalkeeper_save_pct": "Save percentage",
    "goals_conceded_per_90": "Goals-conceded record",
    "claims_and_punches_per_90": "Claims and punches",
    "sweeper_actions_per_90": "Sweeper actions",
    "goalkeeper_distribution_pct": "Distribution accuracy",
    "goalkeeper_long_pass_pct": "Long-pass accuracy",
}


def metric_label(name: str) -> str:
    return METRIC_LABELS.get(name, name.replace("_", " ").capitalize())


def _score(definition: ArchetypeDefinition, percentiles: dict[str, float]) -> ArchetypeScore | None:
    present = {k: w for k, w in definition.weights.items() if k in percentiles}
    total_weight = sum(definition.weights.values())
    coverage = sum(present.values()) / total_weight
    if len(present) < MIN_METRICS or coverage < MIN_WEIGHT_COVERAGE:
        return None
    score = sum(percentiles[k] * w for k, w in present.items()) / sum(present.values())
    evidence = tuple(
        sorted(((k, percentiles[k]) for k in present), key=lambda item: item[1], reverse=True)
    )
    return ArchetypeScore(definition.name, definition.description, score, coverage, evidence)


def assess_archetype(
    percentiles: Mapping[str, float | None], position_group: str
) -> ArchetypeAssessment:
    """Rank the position's archetypes; report a primary, a credible secondary and clarity."""
    catalogue = CATALOGUE.get(position_group)
    if catalogue is None:
        return ArchetypeAssessment(None, None, (), "UNAVAILABLE", ("Position group unsupported.",))
    available = {k: float(v) for k, v in percentiles.items() if v is not None}
    scored = [s for d in catalogue if (s := _score(d, available)) is not None]
    scored_names = {s.name for s in scored}
    unassessed = [d for d in catalogue if d.name not in scored_names]
    scored.sort(key=lambda s: (s.score, s.coverage), reverse=True)
    if not scored:
        return ArchetypeAssessment(
            None, None, (), "UNAVAILABLE", ("Too few comparable metrics to assign an archetype.",)
        )
    primary = scored[0]
    secondary = (
        scored[1]
        if len(scored) > 1 and scored[1].score >= SECONDARY_THRESHOLD
        else None
    )
    notes: list[str] = []
    if primary.score < 55:
        clarity = "WEAK"
        notes.append(
            "No archetype stands out: every profile scores below the 55th percentile on average."
        )
    elif len(scored) > 1 and primary.score - scored[1].score < CLEAR_MARGIN:
        clarity = "BLENDED"
        notes.append(
            f"A close second profile ({scored[1].name}) sits within "
            f"{CLEAR_MARGIN:.0f} points; treat this player as a hybrid."
        )
    else:
        clarity = "CLEAR"
    if unassessed:
        missing = sorted({m for d in unassessed for m in d.weights if m not in available})
        names = ", ".join(d.name.lower() for d in unassessed)
        notes.append(
            f"The {names} profile{'s' if len(unassessed) > 1 else ''} could not be assessed "
            "because this data provider does not record: "
            + ", ".join(metric_label(m).lower() for m in missing[:5])
            + ". The label shown is the best fit among the profiles that could be scored."
        )
        if clarity == "CLEAR":
            clarity = "LIMITED"
    elif primary.coverage < 0.8:
        notes.append("Some metrics behind this archetype are unavailable for this provider.")
    return ArchetypeAssessment(primary, secondary, tuple(scored), clarity, tuple(notes))
