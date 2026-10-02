"""Head-to-head comparison of two current top-five-league players.

Both players' cached FotMob pages give per-90 values. Each stat is ranked inside the player's own
role family across the whole pool of cached players (the same ranking the alternatives finder
uses), so a percentile means the same thing for a Premier League and a Serie A winger. A stat goes
to whoever ranks clearly higher; small gaps, or gaps that only exist because both numbers are near
zero, are called even. Nothing here predicts how either player would do in another team.
"""

from __future__ import annotations

from typing import Any

from football_intelligence import alternatives
from football_intelligence.alternatives import Entry, Pool

EDGE_MARGIN = 5.0
GROUP_ORDER = ["Shooting", "Passing", "Possession", "Defending", "Goalkeeping", "Physical"]

# A short, role-specific set of axes for the radar, so the shape reads at a glance.
RADAR_AXES: dict[str, list[str]] = {
    "forwards": [
        "goals",
        "expected_goals",
        "shots",
        "touches_opp_box",
        "chances_created",
        "expected_assists",
        "dribbles_succeeded",
        "recoveries",
    ],
    "att_mid_wingers": [
        "goals",
        "expected_goals",
        "chances_created",
        "expected_assists",
        "dribbles_succeeded",
        "touches_opp_box",
        "crosses_succeeeded",
        "recoveries",
    ],
    "midfielders": [
        "successful_passes",
        "chances_created",
        "expected_assists",
        "long_balls_accurate",
        "dribbles_succeeded",
        "recoveries",
        "matchstats.headers.tackles",
        "interceptions",
    ],
    "fullbacks": [
        "crosses_succeeeded",
        "chances_created",
        "dribbles_succeeded",
        "successful_passes",
        "matchstats.headers.tackles",
        "interceptions",
        "recoveries",
        "duel_won",
    ],
    "center_backs": [
        "successful_passes",
        "long_balls_accurate",
        "clearances",
        "interceptions",
        "matchstats.headers.tackles",
        "aerials_won",
        "blocked_shots",
        "recoveries",
    ],
    "keepers": [
        "saves",
        "goals_prevented",
        "save_percentage",
        "keeper_high_claim",
        "keeper_sweeper",
        "long_balls_accurate",
        "successful_passes",
    ],
}
FAMILY_LABELS = {
    "forwards": "strikers",
    "att_mid_wingers": "attacking midfielders and wingers",
    "midfielders": "midfielders",
    "fullbacks": "full-backs",
    "center_backs": "centre-backs",
    "keepers": "goalkeepers",
}


def _groups(profile: dict[str, Any]) -> dict[str, str]:
    return {str(s["key"]): str(s.get("group") or "Other") for s in profile.get("stats", [])}


def _heat_cells(
    points: list[list[float]], columns: int = 12, rows: int = 8
) -> list[dict[str, int]]:
    counts: dict[tuple[int, int], int] = {}
    for x, y in points:
        cell = (
            min(columns - 1, max(0, int(x / 105 * columns))),
            min(rows - 1, max(0, int(y / 68 * rows))),
        )
        counts[cell] = counts.get(cell, 0) + 1
    return [{"x_bin": c, "y_bin": r, "events": n} for (c, r), n in counts.items()]


def _card(profile: dict[str, Any], entry: Entry | None) -> dict[str, Any]:
    league = profile.get("league") or {}
    stats = league.get("stats") or {}
    positions = profile.get("positions") or []
    main = next((p for p in positions if p.get("main")), positions[0] if positions else {})
    history = profile.get("market_values") or []
    family = entry.family if entry else alternatives.family_of(profile)
    return {
        "player_id": int(profile["player_id"]),
        "name": profile.get("name"),
        "team": profile.get("team"),
        "team_id": profile.get("team_id"),
        "league": league.get("name"),
        "season": league.get("season"),
        "position": (main or {}).get("label"),
        "family": family,
        "family_label": FAMILY_LABELS.get(family, family),
        "birth_date": profile.get("birth_date"),
        "height": profile.get("height"),
        "foot": profile.get("foot"),
        "contract_end": profile.get("contract_end"),
        "market_value_eur": float(history[-1]["value"]) if history else None,
        "minutes": int(entry.minutes) if entry else int(stats.get("Minutes played") or 0),
        "matches": stats.get("Matches"),
        "goals": stats.get("Goals"),
        "assists": stats.get("Assists"),
        "rating": stats.get("Rating"),
        "heatmap": _heat_cells(profile.get("heatmap") or []),
        "heatmap_points": len(profile.get("heatmap") or []),
    }


def _edge(pool: Pool, a: Entry, b: Entry, key: str) -> dict[str, Any] | None:
    a_value, b_value = a.values.get(key), b.values.get(key)
    if a_value is None and b_value is None:
        return None
    a_pct = alternatives.percentile(pool, a.family, key, a_value) if a_value is not None else None
    b_pct = alternatives.percentile(pool, b.family, key, b_value) if b_value is not None else None
    if a_pct is None or b_pct is None or a_value is None or b_value is None:
        winner = None
    elif abs(a_pct - b_pct) < EDGE_MARGIN or not alternatives._meaningful(a, b, key):
        winner = "even"
    else:
        winner = "a" if a_pct > b_pct else "b"
    return {
        "key": key,
        "title": a.titles.get(key) or b.titles.get(key) or key,
        "a_per90": round(a_value, 2) if a_value is not None else None,
        "b_per90": round(b_value, 2) if b_value is not None else None,
        "a_percentile": round(a_pct, 1) if a_pct is not None else None,
        "b_percentile": round(b_pct, 1) if b_pct is not None else None,
        "lower_is_better": key in alternatives.LOWER_IS_BETTER,
        "winner": winner,
    }


def head_to_head(
    pool: Pool, profile_a: dict[str, Any], profile_b: dict[str, Any]
) -> dict[str, Any]:
    a = alternatives.entry_from_profile(profile_a)
    b = alternatives.entry_from_profile(profile_b)
    card_a, card_b = _card(profile_a, a), _card(profile_b, b)
    if a is None or b is None:
        return {"a": card_a, "b": card_b, "comparable": False, "groups": [], "radar": []}

    group_of = {**_groups(profile_b), **_groups(profile_a)}
    rows = [
        row
        for key in sorted(set(a.values) | set(b.values))
        if (row := _edge(pool, a, b, key)) is not None
    ]
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(group_of.get(row["key"], "Other"), []).append(row)
    ordered = sorted(
        groups.items(),
        key=lambda item: GROUP_ORDER.index(item[0]) if item[0] in GROUP_ORDER else 99,
    )

    def tally(items: list[dict[str, Any]]) -> dict[str, int]:
        return {side: sum(1 for r in items if r["winner"] == side) for side in ("a", "b", "even")}

    decided = [r for r in rows if r["winner"] in ("a", "b")]
    gap = {r["key"]: (r["a_percentile"] - r["b_percentile"]) for r in decided}
    biggest_a = sorted((r for r in decided if r["winner"] == "a"), key=lambda r: -gap[r["key"]])
    biggest_b = sorted((r for r in decided if r["winner"] == "b"), key=lambda r: gap[r["key"]])

    axes = RADAR_AXES.get(a.family, [])
    by_key = {r["key"]: r for r in rows}
    radar = [
        {
            "key": key,
            "title": by_key[key]["title"],
            "a": by_key[key]["a_percentile"],
            "b": by_key[key]["b_percentile"],
        }
        for key in axes
        if key in by_key
    ]
    similarity = alternatives.compare(pool, a, b) if a.family == b.family else None
    return {
        "a": card_a,
        "b": card_b,
        "comparable": True,
        "same_role": a.family == b.family,
        "similarity": similarity["similarity"] if similarity else None,
        "summary": {**tally(rows), "compared": len([r for r in rows if r["winner"]])},
        "biggest_edges": {"a": biggest_a[:3], "b": biggest_b[:3]},
        "radar": radar,
        "groups": [
            {"group": name, "tally": tally(items), "stats": items}
            for name, items in ordered
            if any(r["winner"] is not None for r in items)  # skip groups only one player has
        ],
        "low_minutes": [card["name"] for card in (card_a, card_b) if card["minutes"] < 450],
    }
