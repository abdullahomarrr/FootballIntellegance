"""Current Premier League stats from the public Fantasy Premier League feed.

This is an unofficial, undocumented, unlicensed public endpoint. It is used read-only and
lightly: responses are cached on disk and in memory, requests are spaced out, and nothing is
republished in bulk. It supplies current-season totals, expected stats, availability news and
past-season totals, but no event locations. FPL prices are game prices, not market values.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from football_intelligence.market_snapshot import name_variants

BASE_URL = "https://fantasy.premierleague.com/api"
USER_AGENT = "FootballIntelligencePortfolio/1.0 (personal portfolio project; light cached use)"
CACHE_SECONDS = 3600
CACHE_DIRECTORY = Path("data/external/fpl")
POSITIONS = {1: "GK", 2: "DF", 3: "MD", 4: "FW"}
STATUS_LABELS = {
    "a": "Available",
    "d": "Doubtful",
    "i": "Injured",
    "s": "Suspended",
    "u": "Unavailable",
    "n": "Not in squad",
}

# metric -> (label, higher_is_better); GK and outfield sets differ.
OUTFIELD_METRICS = {
    "goals_per_90": ("Goals", True),
    "assists_per_90": ("Assists", True),
    "xg_per_90": ("Expected goals", True),
    "xa_per_90": ("Expected assists", True),
    "xgi_per_90": ("Expected goal involvements", True),
    "tackles_per_90": ("Tackles", True),
    "recoveries_per_90": ("Ball recoveries", True),
    "cbi_per_90": ("Clearances, blocks and interceptions", True),
    "defensive_contribution_per_90": ("Defensive contributions", True),
}
GOALKEEPER_METRICS = {
    "saves_per_90": ("Saves", True),
    "goals_conceded_per_90": ("Goals conceded", False),
    "xgc_per_90": ("Expected goals conceded", False),
    "clean_sheets_per_90": ("Clean sheets", True),
}

_memory: dict[str, tuple[float, Any]] = {}
_last_request = 0.0


def _cached_get(client: httpx.Client, url: str, cache_name: str) -> Any:
    now = time.monotonic()
    cached = _memory.get(cache_name)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]
    path = CACHE_DIRECTORY / f"{cache_name}.json"
    if path.is_file() and time.time() - path.stat().st_mtime < CACHE_SECONDS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        _memory[cache_name] = (now, payload)
        return payload
    global _last_request
    wait = 1.0 - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    response = client.get(url)
    _last_request = time.monotonic()
    response.raise_for_status()
    payload = response.json()
    try:
        CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # the disk cache is a courtesy; the in-memory copy still serves this process
    _memory[cache_name] = (now, payload)
    return payload


def _client(client: httpx.Client | None) -> httpx.Client:
    return client or httpx.Client(
        timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    )


def fetch_bootstrap(client: httpx.Client | None = None) -> dict[str, Any]:
    http = _client(client)
    try:
        data: dict[str, Any] = _cached_get(http, f"{BASE_URL}/bootstrap-static/", "bootstrap")
        return data
    finally:
        if client is None:
            http.close()


def fetch_summary(element_id: int, client: httpx.Client | None = None) -> dict[str, Any]:
    http = _client(client)
    try:
        data: dict[str, Any] = _cached_get(
            http, f"{BASE_URL}/element-summary/{element_id}/", f"element-{element_id}"
        )
        return data
    finally:
        if client is None:
            http.close()


def clear_cache() -> None:
    _memory.clear()


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _per_90(total: Any, minutes: float) -> float | None:
    return _num(total) * 90.0 / minutes if minutes > 0 else None


@dataclass(frozen=True)
class Snapshot:
    players: list[dict[str, Any]]
    gameweek: int
    minimum_minutes: int
    fetched_note: str


def _display_name(element: dict[str, Any]) -> str:
    known = (element.get("known_name") or "").strip()
    return known or f"{element['first_name']} {element['second_name']}".strip()


def _metrics(element: dict[str, Any], minutes: float) -> dict[str, float | None]:
    if POSITIONS.get(element["element_type"]) == "GK":
        return {
            "saves_per_90": _per_90(element["saves"], minutes),
            "goals_conceded_per_90": _per_90(element["goals_conceded"], minutes),
            "xgc_per_90": _per_90(element["expected_goals_conceded"], minutes),
            "clean_sheets_per_90": _per_90(element["clean_sheets"], minutes),
        }
    return {
        "goals_per_90": _per_90(element["goals_scored"], minutes),
        "assists_per_90": _per_90(element["assists"], minutes),
        "xg_per_90": _per_90(element["expected_goals"], minutes),
        "xa_per_90": _per_90(element["expected_assists"], minutes),
        "xgi_per_90": _per_90(element["expected_goal_involvements"], minutes),
        "tackles_per_90": _per_90(element["tackles"], minutes),
        "recoveries_per_90": _per_90(element["recoveries"], minutes),
        "cbi_per_90": _per_90(element["clearances_blocks_interceptions"], minutes),
        "defensive_contribution_per_90": _per_90(element["defensive_contribution"], minutes),
    }


def _percentile(value: float, cohort: list[float], higher_is_better: bool) -> float:
    if len(cohort) < 2:
        return 50.0
    below = sum(1 for other in cohort if other < value)
    ties = sum(1 for other in cohort if other == value)
    raw = (below + 0.5 * (ties - 1)) / (len(cohort) - 1) * 100
    return raw if higher_is_better else 100 - raw


def age_on(birth: str | None, today: date | None = None) -> int | None:
    if not birth:
        return None
    try:
        born = date.fromisoformat(birth[:10])
    except ValueError:
        return None
    day = today or date.today()
    return day.year - born.year - ((day.month, day.day) < (born.month, born.day))


def build_snapshot(bootstrap: dict[str, Any]) -> Snapshot:
    teams = {team["id"]: team["name"] for team in bootstrap["teams"]}
    finished = [event for event in bootstrap["events"] if event.get("finished")]
    gameweek = max((int(event["id"]) for event in finished), default=0)
    minimum = max(90, int(0.4 * 90 * gameweek))
    players: list[dict[str, Any]] = []
    for element in bootstrap["elements"]:
        minutes = _num(element["minutes"])
        position = POSITIONS.get(element["element_type"], "")
        status = str(element.get("status") or "a")
        players.append(
            {
                "code": int(element["code"]),
                "element_id": int(element["id"]),
                "name": _display_name(element),
                "web_name": element["web_name"],
                "team": teams.get(element["team"], "Unknown"),
                "position_group": position,
                "birth_date": element.get("birth_date"),
                "age": age_on(element.get("birth_date")),
                "minutes": int(minutes),
                "starts": int(_num(element.get("starts"))),
                "goals": int(_num(element["goals_scored"])),
                "assists": int(_num(element["assists"])),
                "expected_goals": round(_num(element["expected_goals"]), 2),
                "expected_assists": round(_num(element["expected_assists"]), 2),
                "yellow_cards": int(_num(element["yellow_cards"])),
                "red_cards": int(_num(element["red_cards"])),
                "clean_sheets": int(_num(element["clean_sheets"])),
                "saves": int(_num(element["saves"])),
                "game_price": _num(element["now_cost"]) / 10,
                "selected_by_percent": _num(element["selected_by_percent"]),
                "form": _num(element["form"]),
                "status": status,
                "status_label": STATUS_LABELS.get(status, status),
                "news": element.get("news") or None,
                "news_added": element.get("news_added"),
                "chance_of_playing": element.get("chance_of_playing_next_round"),
                "metrics": _metrics(element, minutes),
            }
        )
    for position in {p["position_group"] for p in players}:
        metric_set = GOALKEEPER_METRICS if position == "GK" else OUTFIELD_METRICS
        cohort = [p for p in players if p["position_group"] == position and p["minutes"] >= minimum]
        for player in players:
            if player["position_group"] != position:
                continue
            ranked: dict[str, Any] = {}
            for metric, (label, higher) in metric_set.items():
                value = player["metrics"].get(metric)
                if value is None or player["minutes"] < minimum:
                    continue
                values = [
                    c["metrics"][metric] for c in cohort if c["metrics"].get(metric) is not None
                ]
                ranked[metric] = {
                    "label": label,
                    "value": round(value, 3),
                    "percentile": round(_percentile(value, values, higher), 1),
                    "cohort_size": len(values),
                }
            player["rankings"] = ranked
    return Snapshot(
        players,
        gameweek,
        minimum,
        datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )


def season_table(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in summary.get("history_past", []):
        rows.append(
            {
                "season": row["season_name"],
                "minutes": int(_num(row["minutes"])),
                "goals": int(_num(row["goals_scored"])),
                "assists": int(_num(row["assists"])),
                "expected_goals": round(_num(row.get("expected_goals")), 1) or None,
                "expected_assists": round(_num(row.get("expected_assists")), 1) or None,
                "clean_sheets": int(_num(row["clean_sheets"])),
                "points": int(_num(row["total_points"])),
            }
        )
    return rows


def gameweek_table(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "round": int(row["round"]),
            "minutes": int(_num(row["minutes"])),
            "goals": int(_num(row["goals_scored"])),
            "assists": int(_num(row["assists"])),
            "expected_goals": round(_num(row["expected_goals"]), 2),
            "expected_assists": round(_num(row["expected_assists"]), 2),
            "was_home": bool(row.get("was_home")),
            "opponent_team": row.get("opponent_team"),
        }
        for row in summary.get("history", [])
    ]


# ------------------------------------------------------------------ linking to our players


def link_players(connection: Any, players: list[dict[str, Any]]) -> dict[int, tuple[int, str]]:
    """{fpl_code: (our player_id, basis)} using Reep IDs first, then birth date and name."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT opta_numeric, tm_player_id, wyscout_id FROM reep_crosswalk")
        crosswalk = {
            str(opta): (tm, wy) for opta, tm, wy in cursor.fetchall() if opta is not None
        }
        cursor.execute("SELECT tm_player_id, player_id FROM bridge_player_transfermarkt")
        by_tm = {int(tm): int(pid) for tm, pid in cursor.fetchall()}
        cursor.execute(
            """SELECT provider_player_id, player_id FROM bridge_player_provider
               WHERE provider = 'wyscout_open' AND valid_to IS NULL"""
        )
        by_wy = {str(ppid): int(pid) for ppid, pid in cursor.fetchall()}
        cursor.execute(
            """SELECT p.player_id, p.birth_date, p.canonical_name, p.display_name
               FROM dim_player p WHERE p.birth_date IS NOT NULL"""
        )
        by_birth: dict[date, list[tuple[int, set[str]]]] = {}
        for pid, born, canonical, display in cursor.fetchall():
            by_birth.setdefault(born, []).append((int(pid), name_variants(canonical, display)))
    links: dict[int, tuple[int, str]] = {}
    for player in players:
        code = int(player["code"])
        tm, wy = crosswalk.get(str(code), (None, None))
        if wy is not None and str(wy) in by_wy:
            links[code] = (by_wy[str(wy)], "ID_CROSSWALK_WYSCOUT")
            continue
        if tm is not None and int(tm) in by_tm:
            links[code] = (by_tm[int(tm)], "ID_CROSSWALK_TRANSFERMARKT")
            continue
        born = _birth(player.get("birth_date"))
        if born is None:
            continue
        theirs = name_variants(player["name"], player["web_name"])
        candidates = [pid for pid, names in by_birth.get(born, []) if names & theirs]
        if len(candidates) == 1:
            links[code] = (candidates[0], "NAME_AND_BIRTH_DATE")
    return links


def _birth(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def persist_links(connection: Any, links: dict[int, tuple[int, str]]) -> int:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM bridge_player_fpl")
        cursor.executemany(
            "INSERT INTO bridge_player_fpl (fpl_code, player_id, link_basis) VALUES (%s, %s, %s)",
            [(code, pid, basis) for code, (pid, basis) in links.items()],
        )
    connection.commit()
    return len(links)
