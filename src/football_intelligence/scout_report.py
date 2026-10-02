from __future__ import annotations

from dataclasses import dataclass

from football_intelligence.archetypes import CATALOGUE, METRIC_LABELS, assess_archetype

OUTFIELD_METRICS = (
    "pass_completion_pct",
    "pressured_pass_completion_pct",
    "progressive_passes_per_90",
    "passes_into_final_third_per_90",
    "box_entries_per_90",
    "progressive_carries_per_90",
    "successful_dribbles_per_90",
    "pressures_per_90",
    "recoveries_per_90",
    "defensive_actions_per_90",
    "defensive_duels_per_90",
    "turnovers_per_90",
    "xt_added_per_90",
    "xg_per_90",
    "average_shot_xg",
)
GOALKEEPER_METRICS = (
    "goalkeeper_saves_per_90",
    "goalkeeper_save_pct",
    "goalkeeper_distribution_pct",
    "goalkeeper_long_pass_pct",
    "goals_conceded_per_90",
    "claims_and_punches_per_90",
    "sweeper_actions_per_90",
)


def complete_metric_family(
    percentiles: dict[str, float | None], position_group: str
) -> dict[str, float | None]:
    """Add expected-but-unavailable metrics as null so reports can disclose coverage gaps."""
    expected = GOALKEEPER_METRICS if position_group == "GK" else OUTFIELD_METRICS
    return {metric: percentiles.get(metric) for metric in expected}


@dataclass(frozen=True)
class ReportClaim:
    text: str
    evidence_metrics: tuple[str, ...]
    claim_type: str = "CALCULATED"


@dataclass(frozen=True)
class ScoutReport:
    archetype: str
    archetype_evidence: tuple[str, ...]
    summary: str
    strengths: tuple[ReportClaim, ...]
    risks: tuple[ReportClaim, ...]
    caveats: tuple[str, ...]
    archetype_description: str = ""
    archetype_clarity: str = "UNAVAILABLE"
    secondary_archetype: str | None = None
    profile_fits: tuple[tuple[str, float], ...] = ()


def build_scout_report(
    *,
    player_name: str,
    percentiles: dict[str, float | None],
    minutes: int,
    coverage_level: str,
    position_group: str = "OUTFIELD",
) -> ScoutReport:
    def ordinal(value: float) -> str:
        rounded = round(value)
        mod100 = rounded % 100
        suffix = (
            "th"
            if 11 <= mod100 <= 13
            else "st"
            if rounded % 10 == 1
            else "nd"
            if rounded % 10 == 2
            else "rd"
            if rounded % 10 == 3
            else "th"
        )
        return f"{rounded}{suffix}"

    labels = METRIC_LABELS
    available = {name: value for name, value in percentiles.items() if value is not None}
    high = sorted(available.items(), key=lambda item: item[1], reverse=True)
    low = sorted(available.items(), key=lambda item: item[1])
    strengths = tuple(
        ReportClaim(
            f"{labels.get(name, name.replace('_', ' ').title())} ranks at the "
            f"{ordinal(value)} percentile.",
            (name,),
        )
        for name, value in high[:3]
        if value >= 70
    )
    risks = tuple(
        ReportClaim(
            f"{labels.get(name, name.replace('_', ' ').title())} ranks at the "
            f"{ordinal(value)} percentile.",
            (name,),
        )
        for name, value in low[:3]
        if value <= 30
    )
    caveats: list[str] = []
    if minutes < 900:
        caveats.append(f"Limited sample: {minutes} minutes.")
    missing = sorted(set(percentiles) - set(available))
    if missing:
        caveats.append(
            "Unavailable provider metrics: "
            + ", ".join(labels.get(name, name.replace("_", " ").title()) for name in missing)
            + "."
        )
    if not coverage_level.startswith("EVENT"):
        caveats.append("Spatial conclusions are unavailable at this coverage level.")
    archetype_description = ""
    archetype_clarity = "UNAVAILABLE"
    secondary_archetype: str | None = None
    profile_fits: tuple[tuple[str, float], ...] = ()
    if position_group in CATALOGUE:
        assessment = assess_archetype(percentiles, position_group)
        profile_fits = tuple((fit.name, round(fit.score, 1)) for fit in assessment.ranked)
        archetype_clarity = assessment.clarity
        caveats.extend(assessment.notes)
        if assessment.primary is not None:
            archetype = assessment.primary.name
            archetype_description = assessment.primary.description
            archetype_evidence = tuple(name for name, _ in assessment.primary.evidence)
        else:
            archetype, archetype_evidence = "Insufficient evidence", ()
        if assessment.secondary is not None:
            secondary_archetype = assessment.secondary.name
    else:
        dimensions = {
            "Progressive creator": (
                "progressive_passes_per_90",
                "passes_into_final_third_per_90",
                "box_entries_per_90",
            ),
            "Ball-carrying threat": ("progressive_carries_per_90", "successful_dribbles_per_90"),
            "Defensive disruptor": (
                "pressures_per_90",
                "recoveries_per_90",
                "defensive_actions_per_90",
                "defensive_duels_per_90",
            ),
            "Secure distributor": ("pass_completion_pct", "pressured_pass_completion_pct"),
            "Goal threat": ("xg_per_90", "average_shot_xg", "box_entries_per_90"),
        }
        scored = [
            (
                sum(float(available[key]) for key in keys if key in available) / len(present),
                label,
                present,
            )
            for label, keys in dimensions.items()
            if (present := tuple(key for key in keys if key in available))
        ]
        if scored:
            _, archetype, archetype_evidence = max(
                scored, key=lambda item: (item[0], len(item[2]))
            )
        else:
            archetype, archetype_evidence = "Insufficient evidence", ()
    lead = ", ".join(
        f"{labels.get(name, name)} {ordinal(float(available[name]))}"
        for name in archetype_evidence[:3]
        if name in available
    )
    opening = (
        f"{player_name} has no assignable archetype"
        if archetype == "Insufficient evidence"
        else f"{player_name} profiles as {archetype[:1].lower()}{archetype[1:]}"
    )
    summary = (
        opening
        + (f" ({archetype_description.rstrip('.').lower()})" if archetype_description else "")
        + (f", led by {lead}" if lead else "")
        + f". The interpretation uses {len(available)} comparable event metrics "
        f"across {minutes} minutes; "
        "it is evidence for scout review, not a scouting verdict."
    )
    return ScoutReport(
        archetype,
        archetype_evidence,
        summary,
        strengths,
        risks,
        tuple(caveats),
        archetype_description,
        archetype_clarity,
        secondary_archetype,
        profile_fits,
    )
