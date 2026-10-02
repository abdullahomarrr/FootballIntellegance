"""Similar players and possible upgrades among current top-five-league players.

Every player's cached FotMob page gives per-90 values for dozens of stats. Players are compared
only within one role family (keepers, fullbacks, centre-backs, midfielders, wingers, strikers, as
FotMob groups them), and each stat is re-ranked across the whole pool of cached players so the
numbers are comparable across leagues. Similarity measures how alike the profiles are; an upgrade is
a similar player who ranks higher overall, with stats counting more where the clicked player is
strong. Both are descriptions of measured per-90 numbers this
season, not predictions of how a player would perform in another team.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from football_intelligence import fotmob

MIN_MINUTES = 180
MIN_SHARED_STATS = 10
SIMILAR_FLOOR = 60.0
UPGRADE_MARGIN = 3.0
MIN_LISTED_GAP = 5.0

# Team context and discipline say little about an individual's role, so they are not compared.
EXCLUDED_KEYS = {
    "yellow_cards",
    "red_cards",
    "clean_sheet_team_title",
    "goals_conceded_while_on_pitch",
    "expected_goals_against_while_on_pitch",
    "physical_metrics_topspeed",
    "goals_conceded",  # mostly the team's defence; goals prevented is the keeper measure
}
LOWER_IS_BETTER = {"dispossessed", "dribbled_past", "fouls", "error_led_to_goal"}
# Rate stats swing wildly on a handful of attempts (100% long-ball accuracy off one ball), and
# penalty counts are mostly luck. Only rates with real volume behind them are kept.
KEPT_RATES = {"successful_passes_accuracy", "save_percentage"}
STRENGTH_FLOOR = 0.25


def is_noisy(key: str) -> bool:
    if key in KEPT_RATES:
        return False
    rate_suffixes = ("_accuracy", "_percent", "_rate", "_subtitle")
    return key.endswith(rate_suffixes) or key.startswith("penalty")


@dataclass
class Entry:
    player_id: int
    name: str
    team: str | None
    family: str
    position: str | None
    minutes: float
    values: dict[str, float]
    titles: dict[str, str] = field(default_factory=dict)
    market_value: float | None = None


@dataclass
class Pool:
    entries: dict[int, Entry]
    sorted_values: dict[tuple[str, str], list[float]]
    built_at: float


_pool: Pool | None = None
_pool_signature: tuple[object, ...] = (0, 0.0)


def family_of(profile: dict[str, Any]) -> str:
    traits = profile.get("traits") or {}
    key = str(traits.get("key") or "")
    if key:
        return key.removeprefix("stats_comparison_")
    return "unknown"


def entry_from_profile(profile: dict[str, Any]) -> Entry | None:
    league = profile.get("league") or {}
    minutes = fotmob._num((league.get("stats") or {}).get("Minutes played")) or 0.0
    values: dict[str, float] = {}
    titles: dict[str, str] = {}
    for stat in profile.get("stats", []):
        key = stat.get("key")
        value = stat.get("per90")
        if not key or key in EXCLUDED_KEYS or is_noisy(str(key)) or value is None:
            continue
        values[str(key)] = float(value)
        titles[str(key)] = str(stat.get("title") or key)
    family = family_of(profile)
    if family == "unknown" or not values:
        return None
    positions = profile.get("positions") or []
    main = next((p for p in positions if p.get("main")), positions[0] if positions else {})
    history = profile.get("market_values") or []
    return Entry(
        player_id=int(profile["player_id"]),
        name=str(profile["name"]),
        team=profile.get("team"),
        family=family,
        position=(main or {}).get("label"),
        minutes=minutes,
        values=values,
        titles=titles,
        market_value=float(history[-1]["value"]) if history else None,
    )


def build_pool(profiles: list[dict[str, Any]]) -> Pool:
    entries: dict[int, Entry] = {}
    for profile in profiles:
        entry = entry_from_profile(profile)
        if entry is not None:
            entries[entry.player_id] = entry
    sorted_values: dict[tuple[str, str], list[float]] = {}
    for entry in entries.values():
        if entry.minutes < MIN_MINUTES:
            continue
        for key, value in entry.values.items():
            sorted_values.setdefault((entry.family, key), []).append(value)
    for values in sorted_values.values():
        values.sort()
    return Pool(entries, sorted_values, time.time())


DATABASE_POOL_SECONDS = 3600


def load_pool() -> Pool:
    """Build (or reuse) the pool from the stored profiles plus any fresher pages on disk.

    The fotmob_player_profile table is the base, so a host whose disk cache only holds the few
    pages viewed since it started still compares against every player. Disk pages override the
    stored copy of the same player. Rebuilt when the disk cache changes or after an hour.
    """
    global _pool, _pool_signature
    directory = fotmob.CACHE_DIRECTORY / "players"
    files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    signature = (len(files), max((f.stat().st_mtime for f in files), default=0.0))
    stale = _pool is None or time.time() - _pool.built_at > DATABASE_POOL_SECONDS
    if stale or signature != _pool_signature:
        profiles: dict[Any, dict[str, Any]] = {}
        for profile in _profiles_from_database():
            profiles[profile.get("player_id")] = profile
        for path in files:
            try:
                profile = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            profiles[profile.get("player_id", path.stem)] = profile
        _pool = build_pool(list(profiles.values()))
        _pool_signature = signature
    assert _pool is not None
    return _pool


def _profiles_from_database() -> list[dict[str, Any]]:
    from football_intelligence.repository import _query_all

    try:
        rows = _query_all("SELECT payload FROM fotmob_player_profile", ())
    except Exception:  # table missing or database unreachable: an empty pool, not a crash
        return []
    return [row["payload"] for row in rows]


def percentile(pool: Pool, family: str, key: str, value: float) -> float | None:
    values = pool.sorted_values.get((family, key))
    if not values or len(values) < 5:
        return None
    below = sum(1 for other in values if other < value)
    ties = sum(1 for other in values if other == value)
    raw = (below + 0.5 * ties) / len(values) * 100
    return 100 - raw if key in LOWER_IS_BETTER else raw


def percentile_vector(pool: Pool, entry: Entry) -> dict[str, float]:
    vector: dict[str, float] = {}
    for key, value in entry.values.items():
        score = percentile(pool, entry.family, key, value)
        if score is not None:
            vector[key] = score
    return vector


def compare(pool: Pool, target: Entry, other: Entry) -> dict[str, Any] | None:
    """Similarity (0-100) and overall difference between two players of the same role family."""
    mine = percentile_vector(pool, target)
    theirs = percentile_vector(pool, other)
    shared = sorted(set(mine) & set(theirs))
    if len(shared) < MIN_SHARED_STATS:
        return None
    gaps = {key: theirs[key] - mine[key] for key in shared}
    similarity = 100 - sum(abs(gap) for gap in gaps.values()) / len(gaps)
    # Count a stat more where the clicked player is strong, so a winger's goals and chances
    # created outweigh his clearances. Stats where he is weak still count at the floor.
    weights = {
        key: STRENGTH_FLOOR + (1 - STRENGTH_FLOOR) * max(0.0, (mine[key] - 50) / 50) for key in gaps
    }
    overall = sum(weights[key] * gaps[key] for key in gaps) / sum(weights.values())
    impact = sorted(gaps, key=lambda key: weights[key] * gaps[key])
    return {
        "similarity": round(similarity, 1),
        "overall_difference": round(overall, 1),
        "stats_compared": len(shared),
        "better_at": [
            _stat_gap(target, other, key, gaps[key])
            for key in reversed(impact[-3:])
            if gaps[key] >= MIN_LISTED_GAP and _meaningful(target, other, key)
        ],
        "weaker_at": [
            _stat_gap(target, other, key, gaps[key])
            for key in impact[:3]
            if gaps[key] <= -MIN_LISTED_GAP and _meaningful(target, other, key)
        ],
    }


def _meaningful(target: Entry, other: Entry, key: str) -> bool:
    """Skip gaps that exist only because both numbers are almost zero."""
    a, b = target.values[key], other.values[key]
    return abs(a - b) >= max(0.03, 0.05 * max(abs(a), abs(b)))


def _stat_gap(target: Entry, other: Entry, key: str, gap: float) -> dict[str, Any]:
    return {
        "stat": target.titles.get(key) or other.titles.get(key) or key,
        "target_per90": round(target.values[key], 2),
        "candidate_per90": round(other.values[key], 2),
        "percentile_gap": round(gap, 1),
    }


def _summary(entry: Entry, comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "player_id": entry.player_id,
        "name": entry.name,
        "team": entry.team,
        "position": entry.position,
        "minutes": int(entry.minutes),
        "market_value_eur": entry.market_value,
        **comparison,
    }


def alternatives(
    pool: Pool, player_id: int, limit: int = 8, max_value_eur: float | None = None
) -> dict[str, Any]:
    target = pool.entries.get(player_id)
    if target is None:
        return {"status": "TARGET_NOT_IN_POOL", "similar": [], "upgrades": [], "pool_size": 0}
    if target.minutes < MIN_MINUTES:
        return {
            "status": "TARGET_TOO_FEW_MINUTES",
            "similar": [],
            "upgrades": [],
            "pool_size": 0,
            "minimum_minutes": MIN_MINUTES,
        }
    candidates = [
        e
        for e in pool.entries.values()
        if e.family == target.family and e.player_id != player_id and e.minutes >= MIN_MINUTES
    ]
    scored = []
    for candidate in candidates:
        result = compare(pool, target, candidate)
        if result is not None:
            scored.append(_summary(candidate, result))
    similar = sorted(scored, key=lambda row: -row["similarity"])[:limit]
    upgrades = [
        row
        for row in scored
        if row["similarity"] >= SIMILAR_FLOOR
        and row["overall_difference"] >= UPGRADE_MARGIN
        and (
            max_value_eur is None
            or (row["market_value_eur"] is not None and row["market_value_eur"] <= max_value_eur)
        )
    ]
    upgrades.sort(key=lambda row: -row["overall_difference"])
    return {
        "status": "OK",
        "family": target.family,
        "target_minutes": int(target.minutes),
        "pool_size": len(scored),
        "minimum_minutes": MIN_MINUTES,
        "similar": similar,
        "upgrades": upgrades[:limit],
    }
