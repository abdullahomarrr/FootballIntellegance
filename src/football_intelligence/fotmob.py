"""Current squads and player pages read from FotMob's public web pages (personal use).

FotMob has no public API and its terms do not allow scraping, so this is for local, personal use
only. It reads the same server-rendered HTML a browser receives and never calls the signed data
API. Requests identify the project honestly, are spaced one second apart, and everything is cached
on disk: squads for a day, player pages for a day, so a normal session touches the site rarely.
Remove this module before any public deployment.
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from football_intelligence.market_snapshot import fold, name_variants

BASE_URL = "https://www.fotmob.com"
USER_AGENT = "FootballIntelligencePortfolio/1.0 (personal portfolio project; light cached use)"
CACHE_DIRECTORY = Path("data/external/fotmob")
CACHE_SECONDS = 24 * 3600
REQUEST_SPACING_SECONDS = 1.0
MAX_CONSECUTIVE_FAILURES = 5
LEAGUES = {
    47: ("Premier League", "premier-league"),
    87: ("La Liga", "laliga"),
    55: ("Serie A", "serie"),
    54: ("Bundesliga", "bundesliga"),
    53: ("Ligue 1", "ligue-1"),
}
GROUPS = {"keepers": "GK", "defenders": "DF", "midfielders": "MD", "attackers": "FW"}

_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_last_request = 0.0


class FotmobError(RuntimeError):
    """The page could not be read or did not contain the expected data."""


def _client(client: httpx.Client | None) -> httpx.Client:
    return client or httpx.Client(
        base_url=BASE_URL,
        timeout=40,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )


def _page_props(html: str) -> dict[str, Any]:
    match = _NEXT_DATA.search(html)
    if not match:
        raise FotmobError("page has no embedded data")
    props: dict[str, Any] = json.loads(match.group(1))["props"]["pageProps"]
    return props


def _fetch_html(http: httpx.Client, path: str) -> str:
    global _last_request
    wait = REQUEST_SPACING_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    response = http.get(path)
    _last_request = time.monotonic()
    response.raise_for_status()
    return response.text


def _read_cache(path: Path, max_age: float = CACHE_SECONDS) -> Any | None:
    if path.is_file() and time.time() - path.stat().st_mtime < max_age:
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _write_cache(path: Path, payload: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # the disk cache is a courtesy


# ------------------------------------------------------------------ leagues and squads


def parse_league_teams(html: str) -> dict[str, Any]:
    props = _page_props(html)
    table = props["table"][0]["data"]["table"]["all"]
    return {
        "league_id": int(props["details"]["id"]),
        "season": str(props["details"]["selectedSeason"]),
        "teams": [{"team_id": int(row["id"]), "name": str(row["name"])} for row in table],
    }


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _birth(value: Any) -> str | None:
    if not value:
        return None
    return str(value)[:10]


def parse_squad(html: str, team_id: int) -> dict[str, Any]:
    props = _page_props(html)
    team = props["fallback"].get(f"team-{team_id}")
    if not isinstance(team, dict) or not team.get("squad"):
        raise FotmobError(f"team {team_id} page has no squad")
    members: list[dict[str, Any]] = []
    for group in team["squad"]["squad"]:
        position_group = GROUPS.get(str(group.get("title")))
        if position_group is None:
            continue  # coaches
        for raw in group["members"]:
            injury = raw.get("injury") or {}
            members.append(
                {
                    "player_id": int(raw["id"]),
                    "name": str(raw["name"]),
                    "position_group": position_group,
                    "role": (raw.get("role") or {}).get("fallback"),
                    "position_codes": raw.get("positionIdsDesc"),
                    "shirt_number": raw.get("shirtNumber"),
                    "nationality": raw.get("cname"),
                    "nationality_code": raw.get("ccode"),
                    "birth_date": _birth(raw.get("dateOfBirth")),
                    "height_cm": raw.get("height"),
                    "age": raw.get("age"),
                    "market_value_eur": raw.get("transferValue"),
                    "injured": bool(raw.get("injured")),
                    "injury_return": injury.get("expectedReturn"),
                    "rating": _num(raw.get("rating")),
                    "goals": raw.get("goals"),
                    "assists": raw.get("assists"),
                }
            )
    return {"team_id": team_id, "name": team["details"]["name"], "members": members}


def fetch_league_teams(league_id: int, client: httpx.Client | None = None) -> dict[str, Any]:
    cache = CACHE_DIRECTORY / "leagues" / f"{league_id}.json"
    cached = _read_cache(cache)
    if cached is not None:
        result: dict[str, Any] = cached
        return result
    name, slug = LEAGUES[league_id]
    http = _client(client)
    try:
        parsed = parse_league_teams(_fetch_html(http, f"/leagues/{league_id}/overview/{slug}"))
    finally:
        if client is None:
            http.close()
    parsed["league_name"] = name
    _write_cache(cache, parsed)
    return parsed


def fetch_squad(team_id: int, client: httpx.Client | None = None) -> dict[str, Any]:
    cache = CACHE_DIRECTORY / "squads" / f"{team_id}.json"
    cached = _read_cache(cache)
    if cached is not None:
        result: dict[str, Any] = cached
        return result
    http = _client(client)
    try:
        parsed = parse_squad(_fetch_html(http, f"/teams/{team_id}/squad/team"), team_id)
    finally:
        if client is None:
            http.close()
    _write_cache(cache, parsed)
    return parsed


def load_squads(
    connection: Any, client: httpx.Client | None = None, leagues: dict[int, Any] | None = None
) -> dict[str, Any]:
    """Fetch every club squad for the leagues and store them. Cached pages are reused."""
    teams = 0
    members = 0
    failures: list[str] = []
    for league_id in leagues or LEAGUES:
        league = fetch_league_teams(league_id, client)
        for team in league["teams"]:
            try:
                squad = fetch_squad(int(team["team_id"]), client)
            except (httpx.HTTPError, FotmobError) as error:
                failures.append(f"{team['name']}: {error}")
                continue
            _store_squad(connection, league, squad)
            teams += 1
            members += len(squad["members"])
    connection.commit()
    return {"teams": teams, "players": members, "failures": failures}


def _store_squad(connection: Any, league: dict[str, Any], squad: dict[str, Any]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO fotmob_team (team_id, name, league_id, league_name, season)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (team_id) DO UPDATE SET name = EXCLUDED.name,
                 league_id = EXCLUDED.league_id, league_name = EXCLUDED.league_name,
                 season = EXCLUDED.season, updated_at = now()""",
            (
                squad["team_id"],
                squad["name"],
                league["league_id"],
                league["league_name"],
                league["season"],
            ),
        )
        cursor.execute("DELETE FROM fotmob_squad_member WHERE team_id = %s", (squad["team_id"],))
        cursor.executemany(
            """INSERT INTO fotmob_squad_member
               (player_id, team_id, name, position_group, role, position_codes, shirt_number,
                nationality, nationality_code, birth_date, height_cm, age, market_value_eur,
                injured, injury_return, rating, goals, assists)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (player_id) DO UPDATE SET team_id = EXCLUDED.team_id,
                 name = EXCLUDED.name, position_group = EXCLUDED.position_group,
                 role = EXCLUDED.role, position_codes = EXCLUDED.position_codes,
                 shirt_number = EXCLUDED.shirt_number, nationality = EXCLUDED.nationality,
                 nationality_code = EXCLUDED.nationality_code, birth_date = EXCLUDED.birth_date,
                 height_cm = EXCLUDED.height_cm, age = EXCLUDED.age,
                 market_value_eur = EXCLUDED.market_value_eur, injured = EXCLUDED.injured,
                 injury_return = EXCLUDED.injury_return, rating = EXCLUDED.rating,
                 goals = EXCLUDED.goals, assists = EXCLUDED.assists, updated_at = now()""",
            [
                (
                    m["player_id"], squad["team_id"], m["name"], m["position_group"], m["role"],
                    m["position_codes"], m["shirt_number"], m["nationality"],
                    m["nationality_code"], m["birth_date"], m["height_cm"], m["age"],
                    m["market_value_eur"], m["injured"], m["injury_return"], m["rating"],
                    m["goals"], m["assists"],
                )
                for m in squad["members"]
            ],
        )


# ------------------------------------------------------------------ player pages


def _stat_items(player: dict[str, Any]) -> list[dict[str, Any]]:
    section = (player.get("firstSeasonStats") or {}).get("statsSection") or {}
    items: list[dict[str, Any]] = []
    for group in section.get("items", []):
        for stat in group.get("items", []):
            items.append(
                {
                    "key": stat.get("localizedTitleId"),
                    "title": stat.get("title"),
                    "group": group.get("title"),
                    "value": stat.get("statValue"),
                    "per90": _num(stat.get("per90")),
                    "percentile": _num(stat.get("percentileRank")),
                    "percentile_per90": _num(stat.get("percentileRankPer90")),
                }
            )
    return items


def parse_player(html: str, player_id: int) -> dict[str, Any]:
    props = _page_props(html)
    raw = props["fallback"].get(f"player:{player_id}")
    if not isinstance(raw, dict) or not raw.get("name"):
        raise FotmobError(f"player {player_id} page has no data")
    first = raw.get("firstSeasonStats") or {}
    main = raw.get("mainLeague") or {}
    info = {
        str(item.get("translationKey")): (item.get("value") or {}).get("fallback")
        for item in raw.get("playerInformation") or []
    }
    positions = [
        {
            "label": (p.get("strPos") or {}).get("label"),
            "short": (p.get("strPosShort") or {}).get("label"),
            "main": bool(p.get("isMainPosition")),
            "appearances": p.get("occurences"),
        }
        for p in (raw.get("positionDescription") or {}).get("positions", [])
    ]
    team = raw.get("primaryTeam") or {}
    values = (raw.get("marketValues") or {}).get("values", [])
    heat = (first.get("heatmap") or {}).get("coordinates") or []
    shots = first.get("shotmap") or first.get("keeperShotmap") or []
    return {
        "player_id": player_id,
        "name": raw["name"],
        "birth_date": _birth((raw.get("birthDate") or {}).get("utcTime")),
        "contract_end": _birth((raw.get("contractEnd") or {}).get("utcTime")),
        "team_id": team.get("teamId"),
        "team": team.get("teamName"),
        "on_loan": bool(team.get("onLoan")),
        "positions": positions,
        "height": info.get("height_sentencecase"),
        "foot": info.get("preferred_foot"),
        "injury": raw.get("injuryInformation"),
        "league": {
            "id": main.get("leagueId"),
            "name": main.get("leagueName"),
            "season": main.get("season"),
            "stats": {s["title"]: s.get("value") for s in main.get("stats", [])},
        },
        "traits": raw.get("traits"),
        "stats": _stat_items(raw),
        "market_values": [
            {"date": str(v["date"])[:10], "value": v["value"]} for v in values
        ],
        "heatmap": [[round(c["x"], 1), round(c["y"], 1)] for c in heat],
        "shots": [
            {
                "x": s.get("x"),
                "y": s.get("y"),
                "minute": s.get("min"),
                "xg": _num(s.get("expectedGoals")),
                "type": s.get("eventType"),
                "situation": s.get("situation"),
                "on_target": s.get("isOnTarget"),
            }
            for s in shots
            if "x" in s
        ],
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def player_cache_path(player_id: int) -> Path:
    return CACHE_DIRECTORY / "players" / f"{player_id}.json"


def fetch_player(player_id: int, client: httpx.Client | None = None) -> dict[str, Any]:
    cached = _read_cache(player_cache_path(player_id))
    if cached is not None:
        result: dict[str, Any] = cached
        return result
    http = _client(client)
    try:
        parsed = parse_player(_fetch_html(http, f"/players/{player_id}/x"), player_id)
    finally:
        if client is None:
            http.close()
    _write_cache(player_cache_path(player_id), parsed)
    return parsed


# ------------------------------------------------------------------ linking to our players


def _birth_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def link_players(connection: Any) -> dict[int, tuple[int, str]]:
    """{fotmob id: (our player_id, basis)} on the same birth date and exactly one name fit."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT player_id, name, birth_date FROM fotmob_squad_member "
            "WHERE birth_date IS NOT NULL"
        )
        theirs = cursor.fetchall()
        cursor.execute(
            """SELECT player_id, canonical_name, display_name, birth_date
               FROM dim_player WHERE birth_date IS NOT NULL"""
        )
        ours: dict[date, list[tuple[int, set[str], set[str]]]] = {}
        for player_id, canonical, display, born in cursor.fetchall():
            ours.setdefault(born, []).append(
                (
                    int(player_id),
                    name_variants(canonical, display),
                    set(fold(canonical).split()),
                )
            )
    links: dict[int, tuple[int, str]] = {}
    for fotmob_id, name, born in theirs:
        candidates = ours.get(born, [])
        variants = name_variants(name)
        exact = [pid for pid, names, _tokens in candidates if names & variants]
        if len(exact) == 1:
            links[int(fotmob_id)] = (exact[0], "BIRTH_DATE_AND_NAME")
            continue
        words = set(fold(name).split())
        loose = [pid for pid, _names, tokens in candidates if len(words) >= 2 and words <= tokens]
        if len(loose) == 1:
            links[int(fotmob_id)] = (loose[0], "BIRTH_DATE_AND_NAME_WORDS")
    for fotmob_id, found in _link_by_name_and_club(connection, set(links)).items():
        links[fotmob_id] = found
    return links


def _link_by_name_and_club(
    connection: Any, already_linked: set[int]
) -> dict[int, tuple[int, str]]:
    """For players we hold no birth date for: one exact name fit whose latest Transfermarkt
    contract club is this squad's club."""
    from football_intelligence.laliga import _same_club

    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT m.player_id, m.name, t.name FROM fotmob_squad_member m
               JOIN fotmob_team t ON t.team_id = m.team_id"""
        )
        members = [row for row in cursor.fetchall() if int(row[0]) not in already_linked]
        cursor.execute(
            """SELECT p.player_id, p.canonical_name, p.display_name,
                      (SELECT c.club_name FROM player_contract_observation c
                        WHERE c.player_id = p.player_id AND c.club_name IS NOT NULL
                        ORDER BY c.observed_as_of DESC LIMIT 1)
               FROM dim_player p WHERE p.birth_date IS NULL"""
        )
        rows = cursor.fetchall()
    by_name: dict[str, set[tuple[int, str]]] = {}
    tokens_by_player: dict[int, tuple[set[str], str]] = {}
    for player_id, canonical, display, club in rows:
        if not club:
            continue
        tokens_by_player[int(player_id)] = (set(fold(canonical).split()), str(club))
        for variant in name_variants(canonical, display):
            by_name.setdefault(variant, set()).add((int(player_id), str(club)))
    links: dict[int, tuple[int, str]] = {}
    for fotmob_id, name, team in members:
        fits = {
            pid
            for variant in name_variants(name)
            for pid, club in by_name.get(variant, set())
            if _same_club(club, str(team))
        }
        if len(fits) == 1:
            links[int(fotmob_id)] = (next(iter(fits)), "NAME_AND_CLUB")
            continue
        words = set(fold(name).split())
        loose = [
            pid
            for pid, (tokens, club) in tokens_by_player.items()
            if len(words) >= 2 and words <= tokens and _same_club(club, str(team))
        ]
        if len(loose) == 1:
            links[int(fotmob_id)] = (loose[0], "NAME_WORDS_AND_CLUB")
    return links


def persist_links(connection: Any, links: dict[int, tuple[int, str]]) -> int:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM bridge_player_fotmob")
        cursor.executemany(
            "INSERT INTO bridge_player_fotmob (fotmob_id, player_id, link_basis) "
            "VALUES (%s, %s, %s)",
            [(fid, pid, basis) for fid, (pid, basis) in links.items()],
        )
    connection.commit()
    return len(links)


def warm_profiles(
    connection: Any, client: httpx.Client | None = None, limit: int | None = None
) -> dict[str, Any]:
    """Fetch the page of every squad player who has played this season, skipping cached ones.

    Resumable: a stopped run picks up where it left off because finished pages stay on disk.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT player_id FROM fotmob_squad_member WHERE rating IS NOT NULL
               ORDER BY market_value_eur DESC NULLS LAST, player_id"""
        )
        wanted = [int(row[0]) for row in cursor.fetchall()]
    fetched = skipped = streak = 0
    failures: list[int] = []
    stopped_early = False
    for player_id in wanted:
        if streak >= MAX_CONSECUTIVE_FAILURES:
            stopped_early = True  # the site is refusing us; stop rather than keep asking
            break
        if _read_cache(player_cache_path(player_id)) is not None:
            skipped += 1
            continue
        if limit is not None and fetched >= limit:
            break
        try:
            fetch_player(player_id, client)
            fetched += 1
            streak = 0
        except (httpx.HTTPError, FotmobError):
            failures.append(player_id)
            streak += 1
    return {
        "wanted": len(wanted),
        "fetched": fetched,
        "already_cached": skipped,
        "failures": failures,
        "stopped_early": stopped_early,
    }


def sync_profiles_to_database(connection: Any) -> dict[str, int]:
    """Copy every cached player page on disk into fotmob_player_profile (upsert)."""
    from datetime import UTC, datetime

    directory = CACHE_DIRECTORY / "players"
    rows = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            player_id = int(payload["player_id"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        fetched_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        rows.append((player_id, json.dumps(payload, ensure_ascii=False), fetched_at))
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO fotmob_player_profile (player_id, payload, fetched_at)
            VALUES (%s, %s::jsonb, %s)
            ON CONFLICT (player_id) DO UPDATE
            SET payload = EXCLUDED.payload, fetched_at = EXCLUDED.fetched_at
            """,
            rows,
        )
    connection.commit()
    return {"profiles": len(rows)}
