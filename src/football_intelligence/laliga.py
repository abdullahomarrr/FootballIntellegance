"""Current La Liga player stats from the free Big Ball Sports API tier.

The free tier covers the current season only, with a small daily request budget, so this module
pulls each finished match's player lines once, keeps them on disk forever (a finished match never
changes) and sums them into season totals and per-90 rates. The feed has no event locations and no
expected stats; it is a stats tier, not an event profile.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from football_intelligence.market_snapshot import fold, name_variants

BASE_URL = "https://api.bigballsdata.com"
USER_AGENT = "FootballIntelligencePortfolio/1.0 (personal portfolio project; light cached use)"
CACHE_DIRECTORY = Path("data/external/laliga")
MATCH_LIST_SECONDS = 3600
REQUEST_SPACING_SECONDS = 0.7
POSITIONS = {"Goalkeeper": "GK", "Defender": "DF", "Midfielder": "MD", "Attacker": "FW"}

# metric -> (label, higher_is_better)
OUTFIELD_METRICS = {
    "goals_per_90": ("Goals", True),
    "assists_per_90": ("Assists", True),
    "shots_per_90": ("Shots", True),
    "shots_on_target_per_90": ("Shots on target", True),
    "key_passes_per_90": ("Key passes", True),
    "dribbles_won_per_90": ("Dribbles won", True),
    "tackles_per_90": ("Tackles", True),
    "interceptions_per_90": ("Interceptions", True),
    "duels_won_per_90": ("Duels won", True),
    "pass_completion": ("Pass completion %", True),
    "rating": ("Average match rating", True),
}
GOALKEEPER_METRICS = {
    "saves_per_90": ("Saves", True),
    "pass_completion": ("Pass completion %", True),
    "rating": ("Average match rating", True),
}

_last_request = 0.0
_memory: dict[str, tuple[float, Any]] = {}


class MissingApiKey(RuntimeError):
    """BIGBALLS_API_KEY is not configured."""


def current_season_start(today: date | None = None) -> int:
    day = today or datetime.now(UTC).date()
    return day.year if day.month >= 8 else day.year - 1


def _client(client: httpx.Client | None) -> httpx.Client:
    if client is not None:
        return client
    key = os.environ.get("BIGBALLS_API_KEY", "").strip()
    if not key:
        raise MissingApiKey("BIGBALLS_API_KEY is not set")
    return httpx.Client(
        base_url=BASE_URL,
        timeout=30,
        headers={"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT},
    )


def _get(http: httpx.Client, path: str, params: dict[str, Any] | None = None) -> Any:
    global _last_request
    wait = REQUEST_SPACING_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    response = http.get(path, params=params)
    _last_request = time.monotonic()
    response.raise_for_status()
    return response.json()


def _write_cache(path: Path, payload: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # the disk cache is a courtesy; the in-memory copy still serves this process


def finished_matches(
    season_start: int, client: httpx.Client | None = None
) -> list[dict[str, Any]]:
    """Finished La Liga matches for a season (cached for an hour)."""
    name = f"matches-{season_start}"
    cached = _memory.get(name)
    if cached and time.monotonic() - cached[0] < MATCH_LIST_SECONDS:
        rows: list[dict[str, Any]] = cached[1]
        return rows
    path = CACHE_DIRECTORY / f"{name}.json"
    if path.is_file() and time.time() - path.stat().st_mtime < MATCH_LIST_SECONDS:
        rows = json.loads(path.read_text(encoding="utf-8"))
        _memory[name] = (time.monotonic(), rows)
        return rows
    http = _client(client)
    try:
        rows = []
        offset = 0
        while True:
            page = _get(
                http,
                "/v1/matches",
                {
                    "sport": "football",
                    "league": "laliga",
                    "season": season_start,
                    "status": "finished",
                    "limit": 100,
                    "offset": offset,
                },
            )
            batch = page.get("data", [])
            rows.extend(batch)
            if len(batch) < 100:
                break
            offset += 100
    finally:
        if client is None:
            http.close()
    _write_cache(path, rows)
    _memory[name] = (time.monotonic(), rows)
    return rows


def match_player_lines(match_id: str, client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Per-player lines for one finished match. Finished matches are cached permanently."""
    path = CACHE_DIRECTORY / "matches" / f"{match_id}.json"
    if path.is_file():
        lines: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        return lines
    http = _client(client)
    try:
        payload = _get(http, f"/v1/stored/matches/{match_id}/stats")
    finally:
        if client is None:
            http.close()
    lines = payload.get("data", {}).get("players", [])
    _write_cache(path, lines)
    return lines


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _stat(line: dict[str, Any], key: str) -> float:
    entry = line.get("stats", {}).get(key)
    return _num(entry.get("value") if isinstance(entry, dict) else entry)


def _is_true(line: dict[str, Any], key: str) -> bool:
    entry = line.get("stats", {}).get(key)
    raw = entry.get("value") if isinstance(entry, dict) else entry
    return str(raw).strip().lower() == "true"


def _per_90(total: float, minutes: float) -> float | None:
    return total * 90.0 / minutes if minutes > 0 else None


def _percentile(value: float, cohort: list[float], higher_is_better: bool) -> float:
    if len(cohort) < 2:
        return 50.0
    below = sum(1 for other in cohort if other < value)
    ties = sum(1 for other in cohort if other == value)
    raw = (below + 0.5 * (ties - 1)) / (len(cohort) - 1) * 100
    return raw if higher_is_better else 100 - raw


SUMMED = {
    "goals": "goals",
    "assists": "assists",
    "shots": "shots_total",
    "shots_on_target": "shots_on",
    "key_passes": "passes_key",
    "passes": "passes_total",
    "passes_completed": "pass_accuracy",  # the feed reports completed passes, not a percentage
    "dribbles_won": "dribbles_success",
    "tackles": "tackles_total",
    "interceptions": "interceptions",
    "duels_won": "duels_won",
    "yellow_cards": "yellow_cards",
    "red_cards": "red_cards",
    "saves": "saves",
}


@dataclass(frozen=True)
class Snapshot:
    players: list[dict[str, Any]]
    matches: int
    minimum_minutes: int
    season_label: str


def build_snapshot(
    matches: list[list[dict[str, Any]]],
    rounds: int,
    season_start: int,
    league_teams: set[str] | None = None,
) -> Snapshot:
    """Sum per-match lines into season totals, then rank within position.

    The feed's team on a line is the player's current club record, not the side they played for in
    that match. When it names a club outside the league (a loan, a transfer, a national team), the
    club is marked unclear rather than shown wrongly.
    """
    totals: dict[str, dict[str, Any]] = {}
    for lines in matches:
        for line in lines:
            minutes = _stat(line, "minutes")
            if minutes <= 0:
                continue
            entry = totals.setdefault(
                str(line["id"]),
                {
                    "id": str(line["id"]),
                    "name": line.get("name") or "",
                    "team": _resolved_team(line.get("team_name"), league_teams),
                    "feed_club": line.get("team_name") or None,
                    "position_group": POSITIONS.get(str(line.get("position")), ""),
                    "appearances": 0,
                    "starts": 0,
                    "minutes": 0.0,
                    "rating_minutes": 0.0,
                    "rating_weighted": 0.0,
                    **dict.fromkeys(SUMMED, 0.0),
                },
            )
            entry["appearances"] += 1
            entry["starts"] += 0 if _is_true(line, "substitute") else 1
            entry["minutes"] += minutes
            rating = _stat(line, "rating")
            if rating > 0:
                entry["rating_minutes"] += minutes
                entry["rating_weighted"] += rating * minutes
            for key, source in SUMMED.items():
                entry[key] += _stat(line, source)
    minimum = max(90, int(0.4 * 90 * rounds))
    players: list[dict[str, Any]] = []
    for entry in totals.values():
        minutes = entry["minutes"]
        completion = entry["passes_completed"] / entry["passes"] * 100 if entry["passes"] else None
        average_rating = (
            entry["rating_weighted"] / entry["rating_minutes"] if entry["rating_minutes"] else None
        )
        metrics: dict[str, float | None] = {
            "goals_per_90": _per_90(entry["goals"], minutes),
            "assists_per_90": _per_90(entry["assists"], minutes),
            "shots_per_90": _per_90(entry["shots"], minutes),
            "shots_on_target_per_90": _per_90(entry["shots_on_target"], minutes),
            "key_passes_per_90": _per_90(entry["key_passes"], minutes),
            "dribbles_won_per_90": _per_90(entry["dribbles_won"], minutes),
            "tackles_per_90": _per_90(entry["tackles"], minutes),
            "interceptions_per_90": _per_90(entry["interceptions"], minutes),
            "duels_won_per_90": _per_90(entry["duels_won"], minutes),
            "saves_per_90": _per_90(entry["saves"], minutes),
            "pass_completion": completion if entry["passes"] >= 100 else None,
            "rating": average_rating,
        }
        players.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "team": entry["team"],
                "club_unclear": entry["team"] == UNCLEAR_CLUB,
                "feed_club": entry["feed_club"],
                "position_group": entry["position_group"],
                "appearances": entry["appearances"],
                "starts": entry["starts"],
                "minutes": int(minutes),
                "goals": int(entry["goals"]),
                "assists": int(entry["assists"]),
                "shots": int(entry["shots"]),
                "shots_on_target": int(entry["shots_on_target"]),
                "key_passes": int(entry["key_passes"]),
                "passes": int(entry["passes"]),
                "pass_completion": None if completion is None else round(completion, 1),
                "tackles": int(entry["tackles"]),
                "interceptions": int(entry["interceptions"]),
                "saves": int(entry["saves"]),
                "yellow_cards": int(entry["yellow_cards"]),
                "red_cards": int(entry["red_cards"]),
                "average_rating": None if average_rating is None else round(average_rating, 2),
                "metrics": metrics,
                "rankings": {},
            }
        )
    for position in {p["position_group"] for p in players if p["position_group"]}:
        metric_set = GOALKEEPER_METRICS if position == "GK" else OUTFIELD_METRICS
        cohort = [p for p in players if p["position_group"] == position and p["minutes"] >= minimum]
        for player in (p for p in players if p["position_group"] == position):
            if player["minutes"] < minimum:
                continue
            for metric, (label, higher) in metric_set.items():
                value = player["metrics"].get(metric)
                if value is None:
                    continue
                values = [
                    c["metrics"][metric] for c in cohort if c["metrics"].get(metric) is not None
                ]
                player["rankings"][metric] = {
                    "label": label,
                    "value": round(value, 3),
                    "percentile": round(_percentile(value, values, higher), 1),
                    "cohort_size": len(values),
                }
    return Snapshot(
        players, len(matches), minimum, f"{season_start}-{str(season_start + 1)[2:]}"
    )


UNCLEAR_CLUB = "Club unclear"


def _resolved_team(team: Any, league_teams: set[str] | None) -> str:
    name = str(team or "")
    if not name or (league_teams is not None and name not in league_teams):
        return UNCLEAR_CLUB
    return name


def load_snapshot(client: httpx.Client | None = None) -> Snapshot:
    """Fetch (or reuse cached) matches and build the current season snapshot."""
    start = current_season_start()
    listing = finished_matches(start, client)
    lines = [match_player_lines(str(row["id"]), client) for row in listing]
    rounds = _rounds_played(listing)
    teams = {
        str((row.get(side) or {}).get("name") or "")
        for row in listing
        for side in ("home", "away")
    } - {""}
    return build_snapshot(lines, rounds, start, teams)


def _rounds_played(listing: list[dict[str, Any]]) -> int:
    """How many matches the busiest team has played, a proxy for the matchweek."""
    counts: dict[str, int] = {}
    for row in listing:
        for side in ("home", "away"):
            team = str((row.get(side) or {}).get("id") or "")
            if team:
                counts[team] = counts.get(team, 0) + 1
    return max(counts.values(), default=0)


# ------------------------------------------------------------------ linking to our players


def link_players(connection: Any, players: list[dict[str, Any]]) -> dict[str, tuple[int, str]]:
    """{feed id: (our player_id, basis)} for players whose full name matches exactly one of ours
    and whose latest contract club in the Transfermarkt snapshot matches the La Liga team."""
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT p.player_id, p.canonical_name, p.display_name,
                      (SELECT c.club_name FROM player_contract_observation c
                        WHERE c.player_id = p.player_id AND c.club_name IS NOT NULL
                        ORDER BY c.observed_as_of DESC LIMIT 1)
               FROM dim_player p"""
        )
        rows = cursor.fetchall()
    by_name: dict[str, list[tuple[int, str]]] = {}
    for player_id, canonical, display, club in rows:
        for variant in name_variants(canonical, display):
            by_name.setdefault(variant, []).append((int(player_id), club or ""))
    at_club: dict[str, list[tuple[int, set[str]]]] = {}
    for team in {p["team"] for p in players if not p.get("club_unclear")}:
        at_club[team] = [
            (int(pid), set(fold(canonical).split()))
            for pid, canonical, _display, club in rows
            if club and _same_club(club, team)
        ]
    links: dict[str, tuple[int, str]] = {}
    for player in (p for p in players if not p.get("club_unclear")):
        found = {
            pid: club
            for variant in name_variants(player["name"])
            for pid, club in by_name.get(variant, [])
        }
        if len(found) == 1:
            ((candidate, club),) = found.items()
            if _same_club(club, player["team"]):
                links[player["id"]] = (candidate, "NAME_AND_CLUB")
            continue
        # Second pass: every word of the feed name appears in one of our (longer, legal) names,
        # among players whose contract club is this team, and exactly one fits.
        words = set(fold(player["name"]).split())
        if len(words) < 2:
            continue
        fits = [pid for pid, tokens in at_club[player["team"]] if words <= tokens]
        if len(fits) == 1:
            links[player["id"]] = (fits[0], "NAME_WORDS_AND_CLUB")
    return links


def _same_club(contract_club: str, team: str) -> bool:
    club_tokens = set(fold(contract_club).split())
    team_tokens = {token for token in fold(team).split() if len(token) > 2}
    return bool(team_tokens) and team_tokens <= club_tokens
