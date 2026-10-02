"""Discover players by playing style: rank qualified player-seasons against one archetype."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from football_intelligence.archetypes import CATALOGUE, assess_archetype, metric_label

CACHE_SECONDS = 600
_cache: dict[str, Any] = {"built_at": 0.0, "entries": []}


def archetype_catalogue() -> dict[str, list[dict[str, str]]]:
    return {
        position: [{"name": item.name, "description": item.description} for item in definitions]
        for position, definitions in CATALOGUE.items()
    }


def build_index(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group percentile rows into player-seasons and score every archetype for each."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (row["player_id"], row["team_id"], row["competition_id"], row["season_id"])
        grouped[key].append(row)
    entries: list[dict[str, Any]] = []
    for group in grouped.values():
        head = group[0]
        position = str(head["position_group"])
        percentiles = {str(row["metric_name"]): float(row["percentile"]) for row in group}
        assessment = assess_archetype(percentiles, position)
        if assessment.primary is None:
            continue
        entries.append(
            {
                "player_id": head["player_id"],
                "name": head["name"],
                "normalized_name": head["normalized_name"],
                "team_name": head.get("team_name"),
                "competition_name": head.get("competition_name"),
                "season_label": head.get("season_label"),
                "position_group": position,
                "minutes_played": int(head.get("minutes_played") or 0),
                "primary": assessment.primary.name,
                "clarity": assessment.clarity,
                "fits": {fit.name: fit for fit in assessment.ranked},
                "percentiles": percentiles,
            }
        )
    return entries


def discover(
    entries: list[dict[str, Any]],
    *,
    position: str,
    archetype: str,
    limit: int = 12,
    minimum_fit: float = 60.0,
    season: str | None = None,
    competition: str | None = None,
) -> list[dict[str, Any]]:
    """Best-fitting players for one archetype, one row per person (their best season)."""
    best: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if entry["position_group"] != position:
            continue
        fit = entry["fits"].get(archetype)
        if fit is None or fit.score < minimum_fit or fit.coverage < 0.6:
            continue
        if season and season.casefold() not in str(entry["season_label"]).casefold():
            continue
        if competition and competition.casefold() not in str(entry["competition_name"]).casefold():
            continue
        key = entry["normalized_name"]
        if key not in best or fit.score > best[key]["fit_score"]:
            top = sorted(fit.evidence, key=lambda item: item[1], reverse=True)[:3]
            best[key] = {
                "player_id": entry["player_id"],
                "name": entry["name"],
                "team_name": entry["team_name"],
                "competition_name": entry["competition_name"],
                "season_label": entry["season_label"],
                "position_group": position,
                "minutes_played": entry["minutes_played"],
                "fit_score": round(fit.score, 1),
                "metric_coverage": round(fit.coverage * 100),
                "is_primary_profile": entry["primary"] == archetype,
                "clarity": entry["clarity"],
                "evidence": [
                    {"metric": metric, "label": metric_label(metric), "percentile": round(value)}
                    for metric, value in top
                ],
            }
    ranked = sorted(
        best.values(), key=lambda row: (row["fit_score"], row["minutes_played"]), reverse=True
    )
    return ranked[:limit]


def cached_index(
    loader: Callable[[], list[dict[str, Any]]], *, now: float | None = None
) -> list[dict[str, Any]]:
    moment = time.monotonic() if now is None else now
    if not _cache["entries"] or moment - float(_cache["built_at"]) > CACHE_SECONDS:
        _cache["entries"] = build_index(loader())
        _cache["built_at"] = moment
    entries: list[dict[str, Any]] = _cache["entries"]
    return entries


def clear_cache() -> None:
    _cache["entries"] = []
    _cache["built_at"] = 0.0
