from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from football_intelligence.analytics import cosine_similarity
from football_intelligence.events import CanonicalEvent


@dataclass(frozen=True)
class TeamStyleProfile:
    team_id: str
    event_count: int
    pass_share: float
    pressure_share: float
    carry_share: float
    vertical_progression_m: float | None
    confidence: str


@dataclass(frozen=True)
class TacticalFit:
    score: float | None
    confidence: str
    compared_dimensions: tuple[str, ...]
    missing_dimensions: tuple[str, ...]


def team_style_profile(events: list[CanonicalEvent], team_id: str) -> TeamStyleProfile:
    selected = [event for event in events if event.provider_team_id == team_id]
    counts = Counter(event.event_type.casefold() for event in selected)
    progressions = [
        event.normalized_end_x_m - event.normalized_x_m
        for event in selected
        if event.event_type.casefold() in {"pass", "carry"}
        and event.normalized_x_m is not None
        and event.normalized_end_x_m is not None
    ]
    total = len(selected)

    def share(name: str) -> float:
        return round(counts[name] / total, 6) if total else 0.0

    confidence = "LOW" if total < 100 else "LIMITED" if total < 500 else "STANDARD"
    return TeamStyleProfile(
        team_id=team_id,
        event_count=total,
        pass_share=share("pass"),
        pressure_share=share("pressure"),
        carry_share=share("carry"),
        vertical_progression_m=(
            round(sum(progressions) / len(progressions), 6) if progressions else None
        ),
        confidence=confidence,
    )


def tactical_fit(
    player_traits: dict[str, float | None],
    required_traits: dict[str, float | None],
    *,
    player_minutes: int,
) -> TacticalFit:
    similarity = cosine_similarity(player_traits, required_traits)
    sample = "LOW" if player_minutes < 450 else "LIMITED" if player_minutes < 900 else "STANDARD"
    if similarity.confidence == "UNAVAILABLE":
        confidence = "UNAVAILABLE"
    elif sample == "LOW" or similarity.confidence == "LOW":
        confidence = "LOW"
    elif sample == "LIMITED" or similarity.confidence == "MEDIUM":
        confidence = "LIMITED"
    else:
        confidence = "STANDARD"
    return TacticalFit(
        score=similarity.score,
        confidence=confidence,
        compared_dimensions=similarity.compared_features,
        missing_dimensions=similarity.missing_features,
    )


def classify_archetype(features: dict[str, float | None]) -> tuple[str, tuple[str, ...]]:
    available = {key: value for key, value in features.items() if value is not None}
    if len(available) < 2:
        return "INSUFFICIENT_DATA", tuple(sorted(set(features) - set(available)))
    ranked = sorted(available, key=lambda key: available[key] or 0, reverse=True)
    labels = {
        "progressive_passes": "PROGRESSIVE_PLAYMAKER",
        "pressures": "PRESSING_SPECIALIST",
        "carries": "BALL_CARRIER",
        "aerial_duels": "AERIAL_PRESENCE",
        "shots": "SHOT_VOLUME_ATTACKER",
    }
    return labels.get(ranked[0], "BALANCED"), tuple(sorted(set(features) - set(available)))


# --- Evidence-based team style and player-in-system context -------------------------------

STYLE_AXES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "SECURITY": (
        "Possession security",
        "Keeps the ball and rarely gives it away.",
        ("pass_completion_pct", "pressured_pass_completion_pct", "turnovers_per_90"),
    ),
    "PROGRESSION": (
        "Progression",
        "Moves the ball forward through passing and carrying.",
        (
            "progressive_passes_per_90",
            "passes_into_final_third_per_90",
            "progressive_carries_per_90",
            "xt_added_per_90",
        ),
    ),
    "PRESSING": (
        "Pressing and winning the ball",
        "Presses and recovers possession.",
        ("pressures_per_90", "recoveries_per_90", "defensive_duels_per_90"),
    ),
    "CHANCES": (
        "Chance creation",
        "Gets into the box and generates quality shots.",
        ("box_entries_per_90", "xg_per_90", "successful_dribbles_per_90"),
    ),
}
STYLE_LABELS = {
    "SECURITY": "Possession-secure",
    "PROGRESSION": "Progressive",
    "PRESSING": "Press-and-win",
    "CHANCES": "Chance-creating",
}
MIN_TEAM_PLAYERS = 5


@dataclass(frozen=True)
class AxisContext:
    axis: str
    label: str
    description: str
    team_score: float | None
    player_score: float | None
    delta: float | None


@dataclass(frozen=True)
class TacticalContext:
    style: str
    style_strength: str
    team_player_count: int
    axes: tuple[AxisContext, ...]
    adds: tuple[str, ...]
    relies: tuple[str, ...]
    notes: tuple[str, ...]


def _weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    total = sum(weight for _, weight in pairs)
    return sum(value * weight for value, weight in pairs) / total if total else None


def build_tactical_context(rows: list[dict[str, object]]) -> TacticalContext | None:
    """Summarise a team's style from its players' percentiles and place one player in it.

    Rows hold ``player_id``, ``minutes_played``, ``metric_name``, ``percentile`` (a
    position-relative, direction-adjusted percentile) and ``is_target``.
    """
    squad_players = {int(row["player_id"]) for row in rows}  # type: ignore[call-overload]
    if len(squad_players) < MIN_TEAM_PLAYERS:
        return None
    axes: list[AxisContext] = []
    for axis, (label, description, metrics) in STYLE_AXES.items():
        team_pairs: list[tuple[float, float]] = []
        player_values: list[float] = []
        for row in rows:
            if row["metric_name"] not in metrics:
                continue
            value = float(row["percentile"])  # type: ignore[arg-type]
            minutes = float(row["minutes_played"] or 0)  # type: ignore[arg-type]
            team_pairs.append((value, minutes))
            if row.get("is_target"):
                player_values.append(value)
        team_score = _weighted_mean(team_pairs)
        player_score = sum(player_values) / len(player_values) if player_values else None
        delta = None
        if player_score is not None and team_score is not None:
            delta = player_score - team_score
        axes.append(AxisContext(axis, label, description, team_score, player_score, delta))
    scored = sorted(
        (a for a in axes if a.team_score is not None),
        key=lambda a: a.team_score or 0,
        reverse=True,
    )
    if not scored:
        return None
    lead = scored[0]
    gap = (lead.team_score or 0) - ((scored[1].team_score or 0) if len(scored) > 1 else 0)
    strength = "DISTINCT" if gap >= 5 else "BLENDED"
    style = STYLE_LABELS[lead.axis]
    if strength == "BLENDED" and len(scored) > 1:
        style = f"{style} / {STYLE_LABELS[scored[1].axis].lower()}"
    with_delta = [a for a in axes if a.delta is not None]
    adds = tuple(
        f"{a.label} ({a.delta:+.0f} vs team)"
        for a in sorted(with_delta, key=lambda a: a.delta or 0, reverse=True)
        if (a.delta or 0) >= 10
    )[:2]
    relies = tuple(
        f"{a.label} ({a.delta:+.0f} vs team)"
        for a in sorted(with_delta, key=lambda a: a.delta or 0)
        if (a.delta or 0) <= -10
    )[:2]
    notes = [
        "Team style is the minutes-weighted average of squad players' position-relative "
        "percentiles; it describes the recorded sample, not a coach's stated system."
    ]
    if len(squad_players) < 11:
        notes.append("Fewer than 11 qualified squad players are in this sample.")
    return TacticalContext(
        style, strength, len(squad_players), tuple(axes), adds, relies, tuple(notes)
    )


@dataclass(frozen=True)
class RoleFit:
    score: float
    coverage: float
    drivers: tuple[tuple[str, float], ...]
    gaps: tuple[tuple[str, float], ...]


def role_fit(
    percentiles: dict[str, float],
    feature_weights: dict[str, float],
    *,
    minimum_coverage: float = 0.6,
) -> RoleFit | None:
    """Weighted mean percentile over a role's priorities, with what drives and limits it."""
    weights = {name: float(w) for name, w in feature_weights.items() if float(w) > 0}
    present = {name: w for name, w in weights.items() if name in percentiles}
    if not weights or not present:
        return None
    coverage = sum(present.values()) / sum(weights.values())
    if coverage < minimum_coverage:
        return None
    score = sum(percentiles[name] * w for name, w in present.items()) / sum(present.values())
    ranked = sorted(present, key=lambda name: percentiles[name] * present[name], reverse=True)
    drivers = tuple((name, percentiles[name]) for name in ranked[:2])
    gaps = tuple(
        (name, percentiles[name])
        for name in sorted(present, key=lambda name: percentiles[name])[:2]
        if percentiles[name] < 50
    )
    return RoleFit(score, coverage, drivers, gaps)
